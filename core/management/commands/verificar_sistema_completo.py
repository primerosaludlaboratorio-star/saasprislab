"""
Smoke test operativo de PRISLAB (sin simular “todas las rutas” legacy).

El barrido HTTP contra catálogo legacy fue retirado por diseño; este comando
ejecuta comprobaciones que sí reflejan el estado real del despliegue.

Flujo:
    django check → conexión BD → verificar_integridad

Para pruebas funcionales use el Quality Gate (.github/workflows) o:
    python scripts_cursor_e2e/run_cursor_reliability_suite.py

Uso:
    python manage.py verificar_sistema_completo
    python manage.py verificar_sistema_completo --full-integrity
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
import logging


class Command(BaseCommand):
    help = (
        'Smoke test real: check de Django, acceso a BD e integridad '
        '(no sustituye suite de tests ni inventario de URLs).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--full-integrity',
            action='store_true',
            help='Ejecuta verificar_integridad sin --quick (huérfanos FK, más lento).',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n=== PRISLAB — verificar_sistema_completo (smoke honesto) ===\n'
        ))

        call_command('check', verbosity=1)

        try:
            connection.ensure_connection()
            if connection.vendor == 'sqlite':
                self.stdout.write(self.style.WARNING(
                    '[BD] SQLite (desarrollo). En producción use PostgreSQL.'
                ))
            self.stdout.write(self.style.SUCCESS('[OK] Conexión a base de datos.'))
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en handle (verificar_sistema_completo.py)")
            raise CommandError(f'Base de datos no accesible: {exc}') from exc

        integrity_kwargs = {} if options['full_integrity'] else {'quick': True}
        call_command('verificar_integridad', **integrity_kwargs)

        self.stdout.write(self.style.SUCCESS(
            '\nSmoke finalizado. Si necesita E2E/UI, ejecute la suite Playwright omni o los tests Django.\n'
        ))