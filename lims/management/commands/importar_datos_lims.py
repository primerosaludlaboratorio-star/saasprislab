"""
Importación maestra desde el directorio `datos_lims/` del proyecto.

Delega en `importar_catalogo_lims` (Parametros.csv, Valores_normalidad.csv) y,
opcionalmente, en el pipeline de perfiles/paquetes/precios.

Antes de importar fija la empresa en thread-local (tenant) para que los Analito
reciban `empresa_id` correcto en entornos sin usuario HTTP.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.models import Empresa
from core.tenant import clear_current_empresa, set_current_empresa, tenant_bypass
from core.utils.default_empresa import resolve_default_empresa_sistema


class Command(BaseCommand):
    help = (
        'Importa datos LIMS desde datos_lims/ (wrapper de importar_catalogo_lims). '
        'Usa la empresa activa por defecto o --empresa-id.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Simular sin guardar',
        )
        parser.add_argument(
            '--reset', action='store_true',
            help='Borrar analitos LIMS antes de importar (peligroso)',
        )
        parser.add_argument(
            '--con-perfiles', action='store_true', dest='con_perfiles',
            help='Tras Nivel 1: perfiles, paquetes y sincronizar precios',
        )
        parser.add_argument(
            '--empresa-id', type=int, default=None,
            help='PK de Empresa destino (default: PRISLAB_DEFAULT_EMPRESA_ID o resolución estándar)',
        )

    def handle(self, *args, **options):
        emp = None
        if options.get('empresa_id'):
            emp = Empresa.objects.filter(pk=options['empresa_id'], activa=True).first()
            if not emp:
                self.stderr.write(self.style.ERROR(f'Empresa id={options["empresa_id"]} no encontrada o inactiva.'))
                return
        if not emp:
            emp = resolve_default_empresa_sistema()
        if not emp:
            self.stderr.write(
                self.style.ERROR(
                    'No hay empresa destino. Cree una Empresa activa o defina PRISLAB_DEFAULT_EMPRESA_ID.'
                )
            )
            return

        self.stdout.write(self.style.NOTICE(f'Empresa destino: {emp.pk} — {emp.nombre}'))

        argv = []
        if options['dry_run']:
            argv.append('--dry-run')
        if options['reset']:
            argv.append('--reset')
        if options['con_perfiles']:
            argv.append('--con-perfiles')

        try:
            with tenant_bypass():
                set_current_empresa(emp)
                call_command('importar_catalogo_lims', *argv, stdout=self.stdout, stderr=self.stderr)
        finally:
            clear_current_empresa()
