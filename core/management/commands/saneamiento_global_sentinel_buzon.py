"""
PRIS SENTINEL + BUZÓN — Saneamiento Global (Resolver/Archivar)
================================================================
Marca como SOLUCIONADO todas las incidencias Sentinel y como RESUELTO
todas las quejas/sugerencias del personal. Alcance: GLOBAL (todas las empresas).
NO borra histórico; solo actualiza estado para que el conteo quede en cero.

Uso:
  python manage.py saneamiento_global_sentinel_buzon
  python manage.py saneamiento_global_sentinel_buzon --dry-run
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger('sentinel')


class Command(BaseCommand):
    help = 'Marca todas las incidencias Sentinel y quejas/sugerencias como resueltas (global, sin borrar)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se haría, sin cambiar nada',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        sep = '=' * 59
        self.stdout.write(self.style.WARNING(sep))
        self.stdout.write(self.style.WARNING(
            '  PRIS SENTINEL + BUZON - Saneamiento Global (Resolver/Archivar)'
        ))
        self.stdout.write(self.style.WARNING(
            f'  Modo: {"DRY RUN" if dry_run else "EJECUCION REAL"}'
        ))
        self.stdout.write(self.style.WARNING(sep))

        ahora = timezone.now()
        nota_sentinel = 'Saneamiento global: resuelto/archivado para conteo en cero (sin borrar histórico).'
        nota_buzon = 'Saneamiento global: archivado para conteo en cero (sin borrar histórico).'

        # 1) IncidenciaSentinel — marcar todas las pendientes como SOLUCIONADO
        try:
            from consultorio.models import IncidenciaSentinel
            qs_sentinel = IncidenciaSentinel.objects.exclude(estado='SOLUCIONADO')
            count_sentinel = qs_sentinel.count()
            total_sentinel = IncidenciaSentinel.objects.count()

            self.stdout.write(f'\n  [SENTINEL] Incidencias pendientes: {count_sentinel} de {total_sentinel} total')
            if count_sentinel > 0:
                if not dry_run:
                    qs_sentinel.update(
                        estado='SOLUCIONADO',
                        notas_resolucion=nota_sentinel,
                        fecha_resolucion=ahora,
                    )
                self.stdout.write(self.style.SUCCESS(
                    f'        -> {"Se marcarían" if dry_run else "Marcadas"} como SOLUCIONADO'
                ))
            else:
                self.stdout.write(self.style.SUCCESS('        -> Ya estaban todas en SOLUCIONADO'))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'  [X] No se pudo importar IncidenciaSentinel: {e}'))
            count_sentinel = 0

        # 2) BuzonQuejas — marcar quejas y sugerencias pendientes como RESUELTO
        try:
            from core.models import BuzonQuejas
            qs_buzon = BuzonQuejas.objects.exclude(estado__in=['RESUELTO', 'DESCARTADO'])
            count_buzon = qs_buzon.count()
            total_buzon = BuzonQuejas.objects.count()

            self.stdout.write(f'\n  [BUZON] Quejas/sugerencias pendientes: {count_buzon} de {total_buzon} total')
            if count_buzon > 0:
                if not dry_run:
                    qs_buzon.update(
                        estado='RESUELTO',
                        notas_resolucion=nota_buzon,
                        fecha_resolucion=ahora,
                        fecha_cierre=ahora,
                    )
                self.stdout.write(self.style.SUCCESS(
                    f'        -> {"Se marcarían" if dry_run else "Marcadas"} como RESUELTO'
                ))
            else:
                self.stdout.write(self.style.SUCCESS('        -> Ya estaban todas resueltas/descartadas'))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'  [X] No se pudo importar BuzonQuejas: {e}'))
            count_buzon = 0

        # 3) Resumen
        self.stdout.write('\n' + sep)
        self.stdout.write(self.style.SUCCESS(
            f'  SENTINEL: {count_sentinel} incidencias resueltas'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'  BUZON:   {count_buzon} quejas/sugerencias archivadas'
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING(
                '  (DRY RUN - ningun cambio aplicado)'
            ))
        self.stdout.write(sep)

        logger.info(
            f'SANEAMIENTO GLOBAL: Sentinel={count_sentinel}, Buzon={count_buzon} '
            f'(dry_run={dry_run})'
        )
