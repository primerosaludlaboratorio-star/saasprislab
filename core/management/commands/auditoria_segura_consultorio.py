import json

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.test import Client

from core.models import CertificadoMedico, CitaMedica, ConsultaMedica, Paciente, Receta, SignosVitales


class Command(BaseCommand):
    help = (
        "Auditoria segura de consultorio en modo solo lectura. "
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
                "clinical_models_core": True,
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
        self.stdout.write("AUDITORIA SEGURA CONSULTORIO (SOLO LECTURA)")
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
            ("consultorio_dashboard", "/consultorio/"),
            ("consultorio_recepcion", "/consultorio/recepcion/"),
            ("consultorio_agendar", "/consultorio/recepcion/agendar/"),
            ("consultorio_lista_trabajo", "/consultorio/medico/lista-trabajo/"),
            ("consultorio_nueva_consulta", "/consultorio/medico/nueva-consulta/"),
            ("consultorio_agenda", "/consultorio/agenda/"),
            ("consultorio_cobros", "/consultorio/cobros/"),
            ("consultorio_api_buscar_pacientes", "/consultorio/api/buscar-pacientes/?q=juan"),
            ("consultorio_api_resultados_disponibles", "/consultorio/api/resultados-disponibles/"),
            ("consultorio_api_buscar_vademecum", "/consultorio/api/buscar-vademecum/?q=paracetamol"),
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
        pacientes_qs = Paciente.objects.filter(self._empresa_filter())
        citas_qs = CitaMedica.objects.filter(self._empresa_filter())
        consultas_qs = ConsultaMedica.objects.filter(self._empresa_filter())
        signos_qs = SignosVitales.objects.filter(self._empresa_filter())
        recetas_qs = Receta.objects.filter(self._empresa_filter())
        certificados_qs = CertificadoMedico.objects.filter(self._empresa_filter())

        estado_citas = {
            "pendientes": citas_qs.filter(estado="PENDIENTE").count(),
            "confirmadas": citas_qs.filter(estado="CONFIRMADA").count(),
            "en_sala": citas_qs.filter(estado="EN_SALA").count(),
            "en_curso": citas_qs.filter(estado="EN_CURSO").count(),
            "completadas": citas_qs.filter(estado="COMPLETADA").count(),
            "canceladas": citas_qs.filter(estado="CANCELADA").count(),
        }
        estado_consultas = {
            "en_curso": consultas_qs.filter(estado="EN_CURSO").count(),
            "finalizadas": consultas_qs.filter(estado="FINALIZADA").count(),
            "canceladas": consultas_qs.filter(estado="CANCELADA").count(),
        }

        self._add_check(
            "snapshot_consultorio",
            "OK",
            (
                f"pacientes={pacientes_qs.count()}, citas={citas_qs.count()}, "
                f"consultas={consultas_qs.count()}, signos={signos_qs.count()}, "
                f"recetas={recetas_qs.count()}, certificados={certificados_qs.count()}"
            ),
            {
                "pacientes": pacientes_qs.count(),
                "citas": citas_qs.count(),
                "consultas": consultas_qs.count(),
                "signos_vitales": signos_qs.count(),
                "recetas": recetas_qs.count(),
                "certificados": certificados_qs.count(),
                "estado_citas": estado_citas,
                "estado_consultas": estado_consultas,
            },
        )

    def _run_integrity_checks(self):
        self.stdout.write("\n[INTEGRIDAD]")
        citas_qs = CitaMedica.objects.filter(self._empresa_filter())
        consultas_qs = ConsultaMedica.objects.filter(self._empresa_filter())
        signos_qs = SignosVitales.objects.filter(self._empresa_filter())
        recetas_qs = Receta.objects.filter(self._empresa_filter())
        certificados_qs = CertificadoMedico.objects.filter(self._empresa_filter())

        citas_completadas_sin_consulta = citas_qs.filter(
            estado="COMPLETADA",
            consulta__isnull=True,
        ).count()

        consultas_finalizadas_sin_receta_ni_plan = consultas_qs.filter(
            estado="FINALIZADA",
            receta__isnull=True,
        ).filter(
            Q(plan_tratamiento__isnull=True) | Q(plan_tratamiento="")
        ).count()

        consultas_pagadas_sin_precio = consultas_qs.filter(
            pagada=True,
            precio_consulta__lte=0,
        ).count()

        consultas_con_cita_sin_signos = consultas_qs.filter(
            cita__isnull=False,
            signos_vitales__isnull=True,
        ).count()

        signos_sin_cita = signos_qs.filter(cita__isnull=True).count()
        recetas_inactivas_vinculadas = recetas_qs.filter(activa=False, consulta__isnull=False).count()
        certificados_activos_sin_consulta = certificados_qs.filter(
            activo=True,
            consulta__isnull=True,
        ).count()
        consultas_sin_folio = consultas_qs.filter(
            Q(folio_consulta__isnull=True) | Q(folio_consulta="")
        ).count()

        self._integrity_check("citas_completadas_sin_consulta", citas_completadas_sin_consulta, "Citas completadas sin consulta asociada")
        self._integrity_check(
            "consultas_finalizadas_sin_receta_ni_plan",
            consultas_finalizadas_sin_receta_ni_plan,
            "Consultas finalizadas sin receta y sin plan de tratamiento",
        )
        self._integrity_check("consultas_pagadas_sin_precio", consultas_pagadas_sin_precio, "Consultas marcadas pagadas con precio <= 0")
        self._integrity_check("consultas_con_cita_sin_signos", consultas_con_cita_sin_signos, "Consultas con cita previa pero sin signos vitales enlazados")
        self._integrity_check("signos_sin_cita", signos_sin_cita, "Registros de signos vitales sin cita asociada")
        self._integrity_check("recetas_inactivas_vinculadas", recetas_inactivas_vinculadas, "Recetas inactivas aun vinculadas a consulta")
        self._integrity_check("certificados_activos_sin_consulta", certificados_activos_sin_consulta, "Certificados activos sin consulta vinculada")
        self._integrity_check("consultas_sin_folio", consultas_sin_folio, "Consultas sin folio_consulta")

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
