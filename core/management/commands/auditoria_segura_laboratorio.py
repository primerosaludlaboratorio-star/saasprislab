import json

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.test import Client

from core.models import DetalleOrden, OrdenDeServicio, PagoOrden, PreOrdenLaboratorio, ResultadoParametro
from lims.models import Analito, PaqueteLims, PerfilLims


class Command(BaseCommand):
    help = (
        "Auditoria segura de laboratorio en modo solo lectura. "
        "No crea, actualiza ni elimina datos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa-id",
            type=int,
            help="Filtra la auditoria a una empresa especifica.",
        )
        parser.add_argument(
            "--username",
            type=str,
            help="Usuario existente para validar rutas autenticadas sin mutar datos.",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="Password del usuario para validar rutas autenticadas.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Imprime el resultado completo en JSON.",
        )

    def handle(self, *args, **options):
        self.empresa_id = options.get("empresa_id")
        self.client = Client()
        self.resultados = {
            "scope": {
                "empresa_id": self.empresa_id,
                "read_only": True,
                "lims_v75": True,
            },
            "auth": {
                "attempted": bool(options.get("username") and options.get("password")),
                "authenticated": False,
                "username": options.get("username") or "",
            },
            "resumen": {
                "ok": 0,
                "warn": 0,
                "fail": 0,
            },
            "checks": [],
        }

        self._print_header()
        self._authenticate(options.get("username"), options.get("password"))
        self._run_route_checks()
        self._run_data_checks()
        self._run_integrity_checks()
        self._print_summary(options.get("json", False))

    def _print_header(self):
        self.stdout.write("=" * 72)
        self.stdout.write("AUDITORIA SEGURA LABORATORIO (SOLO LECTURA)")
        self.stdout.write("=" * 72)

    def _authenticate(self, username, password):
        if not username or not password:
            self._add_check(
                "auth",
                "WARN",
                "Sin credenciales: se validaran rutas en modo anonimo o por redireccion.",
            )
            return

        authenticated = self.client.login(username=username, password=password)
        self.resultados["auth"]["authenticated"] = authenticated
        if authenticated:
            self._add_check("auth", "OK", f"Login correcto para {username}.")
        else:
            self._add_check(
                "auth",
                "WARN",
                f"No se pudo autenticar a {username}; se continua con validaciones de solo lectura.",
            )

    def _empresa_filter(self, field="empresa_id"):
        if not self.empresa_id:
            return Q()
        return Q(**{field: self.empresa_id})

    def _add_check(self, nombre, status, detalle, extra=None):
        self.resultados["checks"].append(
            {
                "nombre": nombre,
                "status": status,
                "detalle": detalle,
                "extra": extra or {},
            }
        )
        if status == "OK":
            self.resultados["resumen"]["ok"] += 1
            self.stdout.write(self.style.SUCCESS(f"[OK] {nombre}: {detalle}"))
        elif status == "WARN":
            self.resultados["resumen"]["warn"] += 1
            self.stdout.write(self.style.WARNING(f"[WARN] {nombre}: {detalle}"))
        else:
            self.resultados["resumen"]["fail"] += 1
            self.stdout.write(self.style.ERROR(f"[FAIL] {nombre}: {detalle}"))

    def _run_route_checks(self):
        self.stdout.write("\n[RUTAS]")
        rutas = [
            ("lab_recepcion", "/laboratorio/recepcion/"),
            ("lab_toma_muestra", "/laboratorio/toma-muestra/"),
            ("lab_lista_trabajo", "/laboratorio/lista-trabajo/"),
            ("lab_registro_resultados", "/laboratorio/registro-resultados/"),
            ("lab_control_calidad", "/laboratorio/control-calidad/"),
            ("lab_entrega_resultados", "/laboratorio/entrega-resultados/"),
            ("lab_api_buscar_estudios", "/laboratorio/api/buscar-estudios/?q=glu"),
            ("lab_api_medicos", "/laboratorio/api/medicos/"),
            ("lab_api_preordenes", "/laboratorio/api/preordenes-pendientes/"),
            ("lab_api_ordenes_recientes", "/laboratorio/api/ordenes-recientes/"),
        ]

        for nombre, url in rutas:
            response = self.client.get(url, follow=False, secure=True)
            status = response.status_code
            if status >= 500:
                self._add_check(nombre, "FAIL", f"{url} devolvio {status}.", {"status_code": status})
            elif status == 404:
                self._add_check(nombre, "FAIL", f"{url} no existe.", {"status_code": status})
            elif status in (200, 301, 302, 403):
                level = "OK" if status in (200, 301, 302) else "WARN"
                self._add_check(nombre, level, f"{url} respondio {status}.", {"status_code": status})
            else:
                self._add_check(nombre, "WARN", f"{url} respondio {status}.", {"status_code": status})

    def _run_data_checks(self):
        self.stdout.write("\n[DATOS]")
        analitos_qs = Analito.objects.filter(self._empresa_filter())
        perfiles_qs = PerfilLims.objects.filter(self._empresa_filter())
        paquetes_qs = PaqueteLims.objects.filter(self._empresa_filter())
        ordenes_qs = OrdenDeServicio.objects.filter(self._empresa_filter())
        detalles_qs = DetalleOrden.objects.filter(orden__in=ordenes_qs)
        pagos_qs = PagoOrden.objects.filter(self._empresa_filter())
        resultados_qs = ResultadoParametro.objects.filter(orden__in=ordenes_qs)
        preordenes_qs = PreOrdenLaboratorio.objects.filter(self._empresa_filter())

        estado_counts = {
            "pendiente_pago": ordenes_qs.filter(estado="PENDIENTE_PAGO").count(),
            "pagado": ordenes_qs.filter(estado="PAGADO").count(),
            "en_proceso": ordenes_qs.filter(estado="EN_PROCESO").count(),
            "resultados_listos": ordenes_qs.filter(estado="RESULTADOS_LISTOS").count(),
            "entregado": ordenes_qs.filter(estado="ENTREGADO").count(),
            "cancelado": ordenes_qs.filter(estado="CANCELADO").count(),
        }

        self._add_check(
            "snapshot_laboratorio",
            "OK",
            (
                f"analitos={analitos_qs.count()}, perfiles={perfiles_qs.count()}, "
                f"paquetes={paquetes_qs.count()}, ordenes={ordenes_qs.count()}, "
                f"detalles={detalles_qs.count()}, resultados={resultados_qs.count()}, "
                f"pagos={pagos_qs.count()}, preordenes={preordenes_qs.count()}"
            ),
            {
                "analitos": analitos_qs.count(),
                "perfiles": perfiles_qs.count(),
                "paquetes": paquetes_qs.count(),
                "ordenes": ordenes_qs.count(),
                "detalles": detalles_qs.count(),
                "resultados": resultados_qs.count(),
                "pagos": pagos_qs.count(),
                "preordenes": preordenes_qs.count(),
                "estado_ordenes": estado_counts,
            },
        )

    def _run_integrity_checks(self):
        self.stdout.write("\n[INTEGRIDAD]")
        ordenes_qs = OrdenDeServicio.objects.filter(self._empresa_filter())
        detalles_qs = DetalleOrden.objects.filter(orden__in=ordenes_qs)
        pagos_qs = PagoOrden.objects.filter(self._empresa_filter())
        resultados_qs = ResultadoParametro.objects.filter(orden__in=ordenes_qs)
        preordenes_qs = PreOrdenLaboratorio.objects.filter(self._empresa_filter())

        detalles_sin_item_lims = detalles_qs.filter(
            analito__isnull=True,
            perfil_lims__isnull=True,
            paquete_lims__isnull=True,
        ).count()

        detalles_con_multiples_items = detalles_qs.filter(
            (
                Q(analito__isnull=False, perfil_lims__isnull=False)
                | Q(analito__isnull=False, paquete_lims__isnull=False)
                | Q(perfil_lims__isnull=False, paquete_lims__isnull=False)
            )
        ).count()

        ordenes_pagadas_sin_detalle = ordenes_qs.filter(
            estado__in=["PAGADO", "EN_PROCESO", "RESULTADOS_LISTOS", "ENTREGADO"],
            detalles__isnull=True,
        ).distinct().count()

        ordenes_listas_sin_pdf = ordenes_qs.filter(
            estado__in=["RESULTADOS_LISTOS", "ENTREGADO"],
            archivo_resultado__isnull=True,
        ).count()

        preordenes_cobradas_sin_orden = preordenes_qs.filter(
            estado="COBRADA",
            orden_vinculada__isnull=True,
        ).count()

        pagos_sin_empresa = pagos_qs.filter(empresa__isnull=True).count()
        pagos_cancelados_con_monto = pagos_qs.filter(
            cancelado=True
        ).exclude(
            monto_efectivo=0,
            monto_tarjeta=0,
            monto_transferencia=0,
            monto_credito=0,
            monto_debito=0,
        ).count()

        resultados_validados_sin_fecha = resultados_qs.filter(
            validado=True,
            fecha_validacion__isnull=True,
        ).count()

        resultados_con_fecha_sin_flag = resultados_qs.filter(
            validado=False,
            fecha_validacion__isnull=False,
        ).count()

        resultados_criticos_no_validados = resultados_qs.filter(
            es_critico=True,
            validado=False,
        ).count()

        self._integrity_check("detalles_sin_item_lims", detalles_sin_item_lims, "Detalles sin analito/perfil/paquete LIMS")
        self._integrity_check("detalles_con_multiples_items", detalles_con_multiples_items, "Detalles con multiples llaves LIMS activas")
        self._integrity_check("ordenes_pagadas_sin_detalle", ordenes_pagadas_sin_detalle, "Ordenes pagadas o en flujo sin detalles")
        self._integrity_check("ordenes_listas_sin_pdf", ordenes_listas_sin_pdf, "Ordenes listas/entregadas sin PDF adjunto")
        self._integrity_check("preordenes_cobradas_sin_orden", preordenes_cobradas_sin_orden, "Preordenes cobradas sin orden vinculada")
        self._integrity_check("pagos_sin_empresa", pagos_sin_empresa, "Pagos de orden sin empresa")
        self._integrity_check("pagos_cancelados_con_monto", pagos_cancelados_con_monto, "Pagos cancelados con monto bruto no nulo")
        self._integrity_check("resultados_validados_sin_fecha", resultados_validados_sin_fecha, "Resultados validados sin fecha_validacion")
        self._integrity_check("resultados_con_fecha_sin_flag", resultados_con_fecha_sin_flag, "Resultados con fecha_validacion pero sin flag validado")
        self._integrity_check("resultados_criticos_no_validados", resultados_criticos_no_validados, "Resultados criticos aun no validados")

    def _integrity_check(self, nombre, cantidad, descripcion):
        if cantidad == 0:
            self._add_check(nombre, "OK", f"{descripcion}: 0")
        else:
            self._add_check(nombre, "WARN", f"{descripcion}: {cantidad}", {"count": cantidad})

    def _print_summary(self, as_json):
        self.stdout.write("\n[RESUMEN]")
        resumen = self.resultados["resumen"]
        self.stdout.write(
            f"OK={resumen['ok']} WARN={resumen['warn']} FAIL={resumen['fail']}"
        )
        if as_json:
            self.stdout.write(json.dumps(self.resultados, indent=2, ensure_ascii=False))
