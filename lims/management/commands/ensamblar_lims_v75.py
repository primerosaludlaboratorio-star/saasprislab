"""
LIMS v7.5 — Ensamblaje jerarquico en orden estricto (Niveles 1 → 4)

  1. Parametros.csv + Valores_normalidad.csv  → Analito + rangos
  2. Examenes.csv + Examenes_Perfil.csv       → PerfilLims + M2M
  3. Paquetes.csv + Paquetes_Perfil.csv       → PaqueteLims + M2M
  4. Consolidacion costo_lista                → PrecioItem

Uso:
  python manage.py ensamblar_lims_v75
  python manage.py ensamblar_lims_v75 --dry-run
  python manage.py ensamblar_lims_v75 --saltar-nivel1   # si analitos ya cargados
  python manage.py ensamblar_lims_v75 --limpiar-perfiles --limpiar-paquetes
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.models import Empresa
from core.tenant import clear_current_empresa, set_current_empresa, tenant_bypass
from core.utils.default_empresa import resolve_default_empresa_sistema


class Command(BaseCommand):
    help = 'Ejecuta import LIMS v7.5 en orden Nivel 1 → 4.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--empresa-id', type=int, default=None,
            help='Empresa destino para fijar contexto tenant durante todo el ensamblaje.',
        )
        parser.add_argument(
            '--saltar-nivel1', action='store_true',
            help='No ejecutar importar_catalogo_lims (analitos + rangos)',
        )
        parser.add_argument('--limpiar-perfiles', action='store_true')
        parser.add_argument('--limpiar-paquetes', action='store_true')
        parser.add_argument(
            '--reset-catalogo', action='store_true',
            help='Pasa --reset a importar_catalogo_lims (borra Analito+rangos lims)',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        out, err = self.stdout, self.stderr
        empresa = self._resolver_empresa(options.get('empresa_id'))

        self.stdout.write(self.style.HTTP_INFO('=== LIMS v7.5 Ensamblaje jerarquico ===\n'))
        if empresa:
            self.stdout.write(self.style.NOTICE(
                f'Empresa contexto: {empresa.pk} — {empresa.nombre}\n'
            ))

        try:
            with tenant_bypass():
                if empresa:
                    set_current_empresa(empresa)

                if not options['saltar_nivel1']:
                    self.stdout.write('>>> Nivel 1: Analitos + valores de referencia\n')
                    args1 = {'dry_run': dry, 'stdout': out, 'stderr': err}
                    if empresa:
                        args1['empresa_id'] = empresa.pk
                    if options['reset_catalogo']:
                        args1['reset'] = True
                    call_command('importar_catalogo_lims', **args1)
                else:
                    self.stdout.write(self.style.WARNING('>>> Nivel 1 omitido (--saltar-nivel1)\n'))

                if dry:
                    self.stdout.write('>>> Nivel 2: Perfiles (dry-run)\n')
                    args2 = {
                        'dry_run': True,
                        'stdout': out,
                        'stderr': err,
                        'limpiar_perfiles': options['limpiar_perfiles'],
                    }
                    if empresa:
                        args2['empresa_id'] = empresa.pk
                    call_command('importar_examenes_perfil_lims', **args2)
                    self.stdout.write('>>> Nivel 3: Paquetes (dry-run)\n')
                    args3 = {
                        'dry_run': True,
                        'stdout': out,
                        'stderr': err,
                        'limpiar_paquetes': options['limpiar_paquetes'],
                    }
                    if empresa:
                        args3['empresa_id'] = empresa.pk
                    call_command('importar_paquetes_perfil_lims', **args3)
                    self.stdout.write('>>> Nivel 4: Precios (dry-run)\n')
                    args4 = {'dry_run': True, 'stdout': out, 'stderr': err}
                    if empresa:
                        args4['empresa_id'] = empresa.pk
                    call_command('sincronizar_precios_lims', **args4)
                    self.stdout.write(self.style.WARNING('\n[DRY-RUN] Niveles 2-4 solo simulados.'))
                    return

                self.stdout.write('\n>>> Nivel 2: Perfiles (Examenes + Examenes_Perfil)\n')
                args2 = {
                    'stdout': out,
                    'stderr': err,
                    'limpiar_perfiles': options['limpiar_perfiles'],
                }
                if empresa:
                    args2['empresa_id'] = empresa.pk
                call_command('importar_examenes_perfil_lims', **args2)

                self.stdout.write('\n>>> Nivel 3: Paquetes (Paquetes + Paquetes_Perfil)\n')
                args3 = {
                    'stdout': out,
                    'stderr': err,
                    'limpiar_paquetes': options['limpiar_paquetes'],
                }
                if empresa:
                    args3['empresa_id'] = empresa.pk
                call_command('importar_paquetes_perfil_lims', **args3)

                self.stdout.write('\n>>> Nivel 4: Precios (PrecioItem)\n')
                args4 = {'stdout': out, 'stderr': err}
                if empresa:
                    args4['empresa_id'] = empresa.pk
                call_command('sincronizar_precios_lims', **args4)

                self.stdout.write(self.style.SUCCESS('\n=== Ensamblaje v7.5 finalizado ===\n'))
        finally:
            clear_current_empresa()

    def _resolver_empresa(self, empresa_id):
        if empresa_id:
            return Empresa.objects.filter(pk=empresa_id, activa=True).first()
        return resolve_default_empresa_sistema()
