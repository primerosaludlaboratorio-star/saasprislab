"""
Management command para simular ventas en el PDV de Farmacia usando la MISMA lógica
que usa la interfaz (core.views.farmacia.procesar_venta).

Objetivo:
- Pruebas de carga/estrés SIN borrar datos
- Simular comportamiento "humano": carrito con 1-6 productos, cantidades variadas, pagos, clientes mixtos
- Medir tiempo total y reportar errores sin detener todo el proceso
"""

import random
import sys
import io
import time
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import IntegrityError, OperationalError
from django.utils import timezone

from core.models import Empresa, Usuario, Producto, Lote, Venta, Paciente
from core.views.farmacia import procesar_venta


def _safe_int(val, default=1):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _pick_empresa(user: Usuario) -> Empresa:
    # En este proyecto, Usuario tiene FK empresa
    return user.empresa


class Command(BaseCommand):
    help = "Simula ventas en el PDV de Farmacia (no borra datos)."

    def add_arguments(self, parser):
        parser.add_argument("--ventas", type=int, default=120, help="Número de ventas a simular (default: 120)")
        parser.add_argument("--min-items", type=int, default=1, help="Mínimo de productos por venta (default: 1)")
        parser.add_argument("--max-items", type=int, default=6, help="Máximo de productos por venta (default: 6)")
        parser.add_argument("--dias", type=int, default=7, help="Rango de días hacia atrás para fechas (default: 7)")
        parser.add_argument(
            "--usuario",
            type=str,
            default="",
            help="Username del cajero a usar (si se omite, usa el primer usuario encontrado).",
        )
        parser.add_argument(
            "--con-paciente",
            type=int,
            default=25,
            help="Porcentaje de ventas con paciente vinculado (0-100, default: 25).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No crea ventas; solo valida que hay productos con stock y construye carritos (default: false).",
        )

    def handle(self, *args, **options):
        # Blindaje encoding Windows (evita UnicodeEncodeError por emojis)
        if sys.platform == "win32":
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

        ventas_objetivo = options["ventas"]
        min_items = max(1, options["min_items"])
        max_items = max(min_items, options["max_items"])
        dias = max(1, options["dias"])
        username = (options["usuario"] or "").strip()
        pct_con_paciente = max(0, min(100, options["con_paciente"]))
        dry_run = bool(options["dry_run"])

        t0 = time.time()
        self.stdout.write(self.style.SUCCESS("[INICIANDO] Simulacion de ventas de Farmacia"))

        # Seleccionar usuario
        if username:
            user = Usuario.objects.filter(username=username).first()
            if not user:
                self.stdout.write(self.style.ERROR(f"[ERROR] No existe el usuario '{username}'"))
                return
        else:
            user = Usuario.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR("[ERROR] No hay usuarios. Cree uno primero (createsuperuser)."))
                return

        empresa = _pick_empresa(user)
        self.stdout.write(f"[USUARIO] Cajero: {user.username} | Empresa: {getattr(empresa, 'nombre', empresa.id)}")

        # Productos con stock por lotes
        def cargar_productos_con_stock():
            # Cargar candidatos sin confiar en stock cacheado (las ventas descuentan inventario)
            candidatos = (
                Producto.objects.filter(empresa=empresa)
                .only("id", "nombre", "codigo_barras", "precio_publico", "precio_compra", "iva_porcentaje", "empresa_id")
                .all()
            )
            # Filtrar por stock real en lotes
            con_stock = []
            for p in candidatos:
                stock_total = Lote.objects.filter(producto=p, cantidad__gt=0).aggregate(s=__import__("django").db.models.Sum("cantidad"))["s"] or 0
                if stock_total > 0:
                    con_stock.append(p)
            return con_stock

        productos_con_stock = cargar_productos_con_stock()

        if not productos_con_stock:
            self.stdout.write(self.style.ERROR("[ERROR] No hay productos con stock (>0) en lotes para esta empresa."))
            self.stdout.write(self.style.WARNING("        Cargue inventario primero (entrada de mercancia / lotes)."))
            return

        # Pacientes (core.models.Paciente) para simular ventas ambulatorias
        pacientes = list(Paciente.objects.filter(empresa=empresa).order_by("-id")[:200])

        # Métricas
        creadas = 0
        omitidas_sin_stock = 0
        errores = 0
        locked_retries = 0
        ventas_para_retrofecha = []  # [(venta_id, fecha_venta)]

        # Dummy request: procesar_venta solo usa request.user
        request_dummy = SimpleNamespace(user=user)

        for idx in range(ventas_objetivo):
            # Simular "persona": pausa mínima aleatoria (no ralentiza demasiado)
            time.sleep(random.uniform(0.0, 0.02))

            # Refrescar candidatos cada cierto número de ventas para evitar seleccionar productos ya agotados
            if idx % 15 == 0:
                productos_con_stock = cargar_productos_con_stock()
                if not productos_con_stock:
                    self.stdout.write(self.style.WARNING("[AVISO] Ya no hay productos con stock. Terminando simulacion."))
                    break

            # Construir carrito: 1-6 productos, cantidades pequeñas
            num_items = random.randint(min_items, max_items)
            seleccion = random.sample(productos_con_stock, k=min(num_items, len(productos_con_stock)))

            items = []
            for p in seleccion:
                # Stock REAL (sin cache) para evitar 'Stock insuficiente' por datos stale
                stock_total = Lote.objects.filter(producto=p, cantidad__gt=0).aggregate(s=__import__("django").db.models.Sum("cantidad"))["s"] or 0
                if stock_total <= 0:
                    continue

                # Cantidad humana: 1-2 (reduce fallos por stock bajo), nunca exceder stock
                cantidad = min(stock_total, random.randint(1, 2))
                items.append(
                    {
                        "producto_id": p.id,
                        "cantidad": cantidad,
                        # opcional: precio_unitario (dejamos que el backend decida)
                    }
                )

            if not items:
                omitidas_sin_stock += 1
                continue

            # Cliente / paciente (mezcla realista)
            usar_paciente = (random.randint(1, 100) <= pct_con_paciente) and bool(pacientes)
            paciente_id = random.choice(pacientes).id if usar_paciente else None

            data = {
                "items": items,
                "cliente": "PÚBLICO GENERAL" if not usar_paciente else None,
                "paciente_id": paciente_id,
                # Sin descuento manual para dejar que el sistema pruebe políticas si existen
                "descuento_porcentaje": "0",
                "tipo_descuento": "0",
                # Pagos: efectivo por defecto (monto se ajusta luego si hace falta)
                "pagos": {"efectivo": "999999"},  # el backend solo exige >0; auditoría usa efectivo_recibido/cambio
                "efectivo_recibido": "0",
                "cambio_entregado": "0",
            }

            # Fecha aleatoria últimos N días (ajustamos Venta.fecha tras crear)
            fecha_venta = timezone.now() - timedelta(days=random.randint(0, dias), hours=random.randint(0, 23), minutes=random.randint(0, 59))

            if dry_run:
                # Solo validar que el backend no rompería por estructura
                continue

            # Reintento si hay "database is locked" (SQLite)
            for intento in range(5):
                try:
                    with transaction.atomic():
                        resp = procesar_venta(request_dummy, data, empresa)

                    # procesar_venta devuelve JsonResponse
                    payload = getattr(resp, "json", None)
                    if callable(payload):
                        payload = resp.json()
                    else:
                        # Django JsonResponse: resp.content es bytes JSON
                        import json as _json

                        payload = _json.loads(resp.content.decode("utf-8"))

                    if payload.get("status") != "success":
                        errores += 1
                        if (idx + 1) % 10 == 0:
                            self.stdout.write(self.style.WARNING(f"[AVISO] Venta fallo: {payload.get('mensaje')}"))
                        break

                    venta_id = payload.get("venta_id")
                    if venta_id:
                        # IMPORTANTE:
                        # No retro-fechamos inmediatamente porque el folio se genera con contador por fecha (hoy).
                        # Si retro-fechamos en caliente, el contador vuelve a bajar y se producen colisiones de folio.
                        ventas_para_retrofecha.append((venta_id, fecha_venta))

                    creadas += 1
                    break

                except OperationalError as e:
                    msg = str(e).lower()
                    if "database is locked" in msg or "locked" in msg:
                        locked_retries += 1
                        time.sleep(0.15 * (intento + 1))
                        continue
                    errores += 1
                    break
                except IntegrityError:
                    # Folio único, línea de captura, etc. (muy raro por la lógica del backend)
                    errores += 1
                    break
                except Exception:
                    errores += 1
                    break

            if (idx + 1) % 25 == 0:
                self.stdout.write(f"[PROGRESO] {idx + 1}/{ventas_objetivo} intentadas | creadas={creadas} | errores={errores}")

        t1 = time.time()

        # Aplicar retro-fechado DESPUÉS de crear todas las ventas (evita colisiones de folios durante la corrida)
        for venta_id, fecha_venta in ventas_para_retrofecha:
            Venta.objects.filter(id=venta_id).update(fecha=fecha_venta)

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("[RESUMEN] SIMULACION FARMACIA"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"[OK] Ventas creadas: {creadas}")
        self.stdout.write(f"[INFO] Ventas omitidas (sin stock al armar carrito): {omitidas_sin_stock}")
        self.stdout.write(f"[INFO] Errores: {errores}")
        self.stdout.write(f"[INFO] Reintentos por DB locked: {locked_retries}")
        self.stdout.write(f"[TIEMPO] {t1 - t0:.2f} segundos")

        # Métrica extra rápida
        total_ventas_empresa = Venta.objects.filter(empresa=empresa).count()
        self.stdout.write(f"[INFO] Total ventas en la empresa ahora: {total_ventas_empresa}")

