"""
PRIS SENTINEL — Reset de Incidencias
=====================================
Marca todas las incidencias actuales como SOLUCIONADO
para que el dashboard arranque limpio y el Director pueda
monitorear solo errores nuevos.

Uso:
  python manage.py sentinel_reset
  python manage.py sentinel_reset --dry-run
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Marca todas las incidencias Sentinel como SOLUCIONADO (reset del dashboard)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra cuantas incidencias se marcarian sin ejecutar',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Eliminar las incidencias en vez de marcarlas como solucionadas',
        )

    def handle(self, *args, **options):
        from consultorio.models import IncidenciaSentinel

        dry_run = options['dry_run']
        delete = options['delete']

        pendientes = IncidenciaSentinel.objects.exclude(estado='SOLUCIONADO')
        total = pendientes.count()
        total_general = IncidenciaSentinel.objects.count()

        self.stdout.write(f'\nIncidencias totales en DB: {total_general}')
        self.stdout.write(f'Incidencias pendientes/en_reparacion: {total}')

        if total == 0:
            self.stdout.write(self.style.SUCCESS('No hay incidencias pendientes. Dashboard ya esta limpio.'))
            return

        # Mostrar resumen por severidad
        for sev in ['CRITICA', 'ALTA', 'MEDIA', 'BAJA']:
            count = pendientes.filter(severidad=sev).count()
            if count > 0:
                self.stdout.write(f'  [{sev}]: {count}')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\n[DRY RUN] Se marcarian {total} incidencias como SOLUCIONADO'
            ))
            return

        if delete:
            # Eliminar todas
            IncidenciaSentinel.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(
                f'\n{total_general} incidencias ELIMINADAS. Dashboard 100% limpio.'
            ))
        else:
            # Marcar como solucionadas
            now = timezone.now()
            updated = pendientes.update(
                estado='SOLUCIONADO',
                fecha_resolucion=now,
                notas_resolucion='Resuelto en batch — Reset de dashboard por el Director.',
            )
            self.stdout.write(self.style.SUCCESS(
                f'\n{updated} incidencias marcadas como SOLUCIONADO.'
            ))

        self.stdout.write(self.style.SUCCESS('Dashboard Sentinel listo para monitorear errores nuevos.'))
