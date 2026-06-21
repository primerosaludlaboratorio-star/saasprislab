import json
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Q, Sum
from django.test import Client
from django.utils import timezone

from core.models import DetalleVenta, Empresa, Lote, Producto, Venta
from farmacia.models import AperturaCaja, CierreTurnoFarmacia, DevolucionVenta, MovimientoInventario


class Command(BaseCommand):
    help = (
        "Auditoria segura de farmacia en modo solo lectura. "
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
        self.stdout.write("AUDITORIA SEGURA FARMACIA (SOLO LECTURA)")
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
            ("farmacia_pdv", "/farmacia/pdv/"),
            ("farmacia_historial_ventas", "/farmacia/historial-ventas/"),
            ("farmacia_inventario", "/farmacia/inventario/"),
            ("farmacia_api_buscar_producto", "/farmacia/api/buscar-producto-pdv/?termino=a"),
            ("farmacia_erp_devoluciones", "/farmacia/erp/devoluciones/"),
            ("farmacia_erp_verificar_caja", "/farmacia/erp/caja/verificar/"),
            ("farmacia_erp_semaforo_caducidad", "/farmacia/erp/semaforo-caducidad/"),
            ("farmacia_erp_stock_critico", "/farmacia/erp/stock-critico/"),
        ]

        for nombre, url in rutas:
            response = self.client.get(url, follow=False, secure=True)
            status = response.status_code
            if status >= 500:
                self._add_check(nombre, "FAIL", f"{url} devolvio {status}.", {"status_code": status})
            elif status == 404:
                self._add_check(nombre, "FAIL", f"{url} no existe.", {"status_code": status})
            elif status in (200, 302, 301, 403):
                level = "OK" if status in (200, 302, 301) else "WARN"
                self._add_check(nombre, level, f"{url} respondio {status}.", {"status_code": status})
            else:
                self._add_check(nombre, "WARN", f"{url} respondio {status}.", {"status_code": status})

    def _run_data_checks(self):
        self.stdout.write("\n[DATOS]")
        today = timezone.localdate()

        productos_qs = Producto.objects.filter(self._empresa_filter())
        lotes_qs = Lote.objects.filter(self._empresa_filter())
        ventas_qs = Venta.objects.filter(self._empresa_filter())
        devoluciones_qs = DevolucionVenta.objects.filter(self._empresa_filter())
        aperturas_qs = AperturaCaja.objects.filter(self._empresa_filter())
        cierres_qs = CierreTurnoFarmacia.objects.filter(self._empresa_filter())

        productos_total = productos_qs.count()
        productos_con_stock = productos_qs.filter(stock__gt=0).count()
        lotes_total = lotes_qs.count()
        lotes_activos = lotes_qs.filter(cantidad__gt=0, fecha_caducidad__gte=today).count()
        ventas_total = ventas_qs.count()
        ventas_canceladas = ventas_qs.filter(estado="CANCELADA").count()
        devoluciones_total = devoluciones_qs.count()
        aperturas_activas = aperturas_qs.filter(activa=True).count()
        cierres_total = cierres_qs.count()

        self._add_check(
            "snapshot_farmacia",
            "OK",
            (
                f"productos={productos_total}, productos_con_stock={productos_con_stock}, "
                f"lotes={lotes_total}, lotes_activos={lotes_activos}, ventas={ventas_total}, "
                f"ventas_canceladas={ventas_canceladas}, devoluciones={devoluciones_total}, "
                f"aperturas_activas={aperturas_activas}, cierres={cierres_total}"
            ),
            {
                "productos_total": productos_total,
                "productos_con_stock": productos_con_stock,
                "lotes_total": lotes_total,
                "lotes_activos": lotes_activos,
                "ventas_total": ventas_total,
                "ventas_canceladas": ventas_canceladas,
                "devoluciones_total": devoluciones_total,
                "aperturas_activas": aperturas_activas,
                "cierres_total": cierres_total,
            },
        )

    def _run_integrity_checks(self):
        self.stdout.write("\n[INTEGRIDAD]")
        now = timezone.now()
        today = timezone.localdate()

        productos_qs = Producto.objects.filter(self._empresa_filter())
        lotes_qs = Lote.objects.filter(self._empresa_filter())
        ventas_qs = Venta.objects.filter(self._empresa_filter())
        aperturas_qs = AperturaCaja.objects.filter(self._empresa_filter())
        cierres_qs = CierreTurnoFarmacia.objects.filter(self._empresa_filter())
        movimientos_qs = MovimientoInventario.objects.filter(self._empresa_filter())

        productos_stock_negativo = productos_qs.filter(stock__lt=0).count()
        lotes_caducados_con_stock = lotes_qs.filter(
            cantidad__gt=0,
            fecha_caducidad__lt=today,
        ).count()
        aperturas_huerfanas = aperturas_qs.filter(
            activa=True,
            fecha_apertura__lt=now - timedelta(days=1),
        ).count()
        cierres_con_apertura_activa = cierres_qs.filter(
            apertura_caja__isnull=False,
            apertura_caja__activa=True,
        ).count()

        ventas_completadas = ventas_qs.filter(estado="COMPLETADA")
        venta_ids_con_salida = movimientos_qs.filter(
            tipo_movimiento="SALIDA_VENTA",
            venta_id__isnull=False,
        ).values_list("venta_id", flat=True)
        ventas_sin_movimiento = ventas_completadas.exclude(id__in=venta_ids_con_salida).count()
        ventas_con_movimiento_sin_flag = ventas_completadas.filter(
            inventario_descontado=False,
            id__in=venta_ids_con_salida,
        ).count()

        detalles_sin_lote = DetalleVenta.objects.filter(
            venta__in=ventas_qs,
            producto__es_servicio=False,
            lote_vendido__isnull=True,
        ).count()

        stock_kardex_descuadrado = 0
        for producto in productos_qs.iterator(chunk_size=100):
            sums = movimientos_qs.filter(producto=producto).aggregate(
                entradas=Sum("cantidad", filter=Q(tipo_movimiento__startswith="ENTRADA")),
                salidas=Sum("cantidad", filter=Q(tipo_movimiento__startswith="SALIDA")),
            )
            entradas = sums["entradas"] or Decimal("0")
            salidas = sums["salidas"] or Decimal("0")
            teorico = entradas - salidas
            if Decimal(producto.stock) != teorico:
                stock_kardex_descuadrado += 1

        self._integrity_check("productos_stock_negativo", productos_stock_negativo, "Productos con stock negativo")
        self._integrity_check("lotes_caducados_con_stock", lotes_caducados_con_stock, "Lotes caducados con stock disponible")
        self._integrity_check("aperturas_huerfanas", aperturas_huerfanas, "Aperturas activas con mas de 24h")
        self._integrity_check("cierres_con_apertura_activa", cierres_con_apertura_activa, "Cierres vinculados a aperturas aun activas")
        self._integrity_check("ventas_sin_movimiento", ventas_sin_movimiento, "Ventas completadas sin salida de kardex")
        self._integrity_check(
            "ventas_con_movimiento_sin_flag",
            ventas_con_movimiento_sin_flag,
            "Ventas con movimiento de salida pero sin flag inventario_descontado",
        )
        self._integrity_check("detalles_sin_lote", detalles_sin_lote, "Detalles de venta sin lote vendido")
        self._integrity_check("stock_kardex_descuadrado", stock_kardex_descuadrado, "Productos descuadrados contra kardex")

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
