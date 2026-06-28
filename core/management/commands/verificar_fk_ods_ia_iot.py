"""
Comprueba FKs hacia core.OrdenDeServicio en IA, IoT y NotificacionPanico (ISO).
Útil tras migrar datos o aplicar core.0053 en PostgreSQL.

Uso: python manage.py verificar_fk_ods_ia_iot
"""

from django.core.management.base import BaseCommand

from core.models import OrdenDeServicio
from ia.models import CotizacionOCR, TranscripcionVoz
from iot.models import VerificacionKiosco
from laboratorio.models import NotificacionPanico


class Command(BaseCommand):
    help = (
        'Lista filas IA/IoT/Lab (pánico ISO) cuya FK a OrdenDeServicio no existe en core (huérfanas).'
    )

    def handle(self, *args, **options):
        ods_qs = OrdenDeServicio.objects.values_list('id', flat=True)
        total_issues = 0

        checks = (
            (CotizacionOCR, 'orden_asociada', 'ia.CotizacionOCR'),
            (TranscripcionVoz, 'orden_asociada', 'ia.TranscripcionVoz'),
            (VerificacionKiosco, 'orden', 'iot.VerificacionKiosco'),
            (NotificacionPanico, 'orden', 'laboratorio.NotificacionPanico'),
        )

        for Model, fk_name, label in checks:
            qs = Model.objects.filter(**{f'{fk_name}_id__isnull': False}).exclude(
                **{f'{fk_name}_id__in': ods_qs}
            )
            n = qs.count()
            if n:
                total_issues += n
                self.stdout.write(
                    self.style.WARNING(f'{label}: {n} fila(s) con {fk_name}_id inválido')
                )
                for row in qs[:20]:
                    oid = getattr(row, f'{fk_name}_id')
                    self.stdout.write(f'  pk={row.pk} → {fk_name}_id={oid}')
                if n > 20:
                    self.stdout.write(f'  ... y {n - 20} más')
            else:
                self.stdout.write(self.style.SUCCESS(f'{label}: OK'))

        if total_issues:
            self.stdout.write(self.style.ERROR(f'Total problemas: {total_issues}'))
        else:
            self.stdout.write(
                self.style.SUCCESS('OK: ninguna FK huerfana hacia OrdenDeServicio (IA/IoT/Lab).')
            )
