from __future__ import annotations

from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Empresa, Venta, AuditLog
from core.utils.auditoria_helper import crear_log_auditoria


class Command(BaseCommand):
    help = "Supervisor IA (cron): revisa ventas del día anterior y genera alertas si detecta anomalías (descuentos)."

    def add_arguments(self, parser):
        parser.add_argument("--empresa-id", type=int, default=None, help="Empresa específica (opcional).")
        parser.add_argument("--umbral-pct", type=float, default=0.35, help="Umbral % ventas con descuento para alertar.")
        parser.add_argument("--umbral-count", type=int, default=10, help="Umbral mínimo de ventas con descuento para alertar.")

    def handle(self, *args, **options):
        empresa_id = options.get("empresa_id")
        umbral_pct = float(options.get("umbral_pct") or 0.35)
        umbral_count = int(options.get("umbral_count") or 10)

        hoy = timezone.localdate()
        d = hoy - timedelta(days=1)
        inicio = timezone.make_aware(datetime.combine(d, datetime.min.time()))
        fin = timezone.make_aware(datetime.combine(d, datetime.max.time()))

        empresas = Empresa.objects.filter(activa=True)
        if empresa_id:
            empresas = empresas.filter(id=empresa_id)

        total_alertas = 0
        for emp in empresas:
            qs = Venta.objects.filter(empresa=emp, fecha__range=(inicio, fin))
            total = qs.count()
            if total == 0:
                continue

            con_desc = qs.filter(descuento_aplicado__gt=0).count()
            pct = con_desc / max(total, 1)

            if con_desc >= umbral_count and pct >= umbral_pct:
                total_alertas += 1
                datos = {
                    "fecha": d.isoformat(),
                    "empresa_id": emp.id,
                    "ventas_total": total,
                    "ventas_con_descuento": con_desc,
                    "porcentaje": round(pct, 4),
                    "umbral_pct": umbral_pct,
                    "umbral_count": umbral_count,
                    "mensaje": "Supervisor IA detectó volumen alto de descuentos. Revisar autorizaciones y políticas.",
                }

                # Log forense (sin usuario específico, es proceso automático)
                crear_log_auditoria(
                    empresa=emp,
                    sucursal=None,
                    usuario=None,
                    accion="SUPERVISOR_IA_ANOMALIA_DESCUENTOS",
                    modelo="Venta",
                    objeto_id=None,
                    datos_anterior=None,
                    datos_nuevo=datos,
                    ip_address=None,
                    user_agent="cron/supervisor_ia",
                )

                self.stdout.write(self.style.WARNING(f"ALERTA: {emp.nombre} {d} descuentos {con_desc}/{total} ({pct:.0%})"))

        self.stdout.write(self.style.SUCCESS(f"Supervisor IA completado. Alertas: {total_alertas}"))

