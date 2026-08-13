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
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
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
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Aplica el cambio; sin esta opción solo se muestra el alcance.',
        )
        parser.add_argument(
            '--confirm-reset',
            action='store_true',
            help='Confirma el cambio de estado de las incidencias.',
        )
        parser.add_argument(
            '--confirm-delete',
            action='store_true',
            help='Confirma la eliminación física de incidencias.',
        )
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='Limita la operación a una empresa concreta.',
        )
        parser.add_argument(
            '--all-tenants',
            action='store_true',
            help='Permite explícitamente el alcance global fuera de producción.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delete = options['delete']
        apply = options['apply']
        empresa_id = options.get('empresa_id')
        all_tenants = options['all_tenants']

        if not apply:
            dry_run = True
        if apply and not options['confirm_reset']:
            raise CommandError('Operación mutante: añade --confirm-reset para continuar.')
        if delete and not options['confirm_delete']:
            raise CommandError('Eliminación destructiva: añade --confirm-delete para continuar.')
        if apply and not empresa_id and not all_tenants:
            raise CommandError('Debes indicar --empresa-id; el alcance global requiere --all-tenants.')
        if getattr(settings, 'IS_PRODUCTION', False) and all_tenants:
            raise CommandError('El alcance global de sentinel_reset está bloqueado en producción.')

        from consultorio.models import IncidenciaSentinel

        scope = IncidenciaSentinel.objects.all()
        if empresa_id:
            scope = scope.filter(empresa_id=empresa_id)

        pendientes = scope.exclude(estado='SOLUCIONADO')
        total = pendientes.count()
        total_general = scope.count()

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
            scope.delete()
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
