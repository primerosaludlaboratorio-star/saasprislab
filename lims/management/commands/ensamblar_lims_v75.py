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


class Command(BaseCommand):
    help = 'Ejecuta import LIMS v7.5 en orden Nivel 1 → 4.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
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

        self.stdout.write(self.style.HTTP_INFO('=== LIMS v7.5 Ensamblaje jerarquico ===\n'))

        if not options['saltar_nivel1']:
            self.stdout.write('>>> Nivel 1: Analitos + valores de referencia\n')
            args1 = {'dry_run': dry, 'stdout': out, 'stderr': err}
            if options['reset_catalogo']:
                args1['reset'] = True
            call_command('importar_catalogo_lims', **args1)
        else:
            self.stdout.write(self.style.WARNING('>>> Nivel 1 omitido (--saltar-nivel1)\n'))

        if dry:
            self.stdout.write('>>> Nivel 2: Perfiles (dry-run)\n')
            call_command(
                'importar_examenes_perfil_lims',
                dry_run=True, stdout=out, stderr=err,
                limpiar_perfiles=options['limpiar_perfiles'],
            )
            self.stdout.write('>>> Nivel 3: Paquetes (dry-run)\n')
            call_command(
                'importar_paquetes_perfil_lims',
                dry_run=True, stdout=out, stderr=err,
                limpiar_paquetes=options['limpiar_paquetes'],
            )
            self.stdout.write('>>> Nivel 4: Precios (dry-run)\n')
            call_command('sincronizar_precios_lims', dry_run=True, stdout=out, stderr=err)
            self.stdout.write(self.style.WARNING('\n[DRY-RUN] Niveles 2-4 solo simulados.'))
            return

        self.stdout.write('\n>>> Nivel 2: Perfiles (Examenes + Examenes_Perfil)\n')
        call_command(
            'importar_examenes_perfil_lims',
            stdout=out, stderr=err,
            limpiar_perfiles=options['limpiar_perfiles'],
        )

        self.stdout.write('\n>>> Nivel 3: Paquetes (Paquetes + Paquetes_Perfil)\n')
        call_command(
            'importar_paquetes_perfil_lims',
            stdout=out, stderr=err,
            limpiar_paquetes=options['limpiar_paquetes'],
        )

        self.stdout.write('\n>>> Nivel 4: Precios (PrecioItem)\n')
        call_command('sincronizar_precios_lims', stdout=out, stderr=err)

        self.stdout.write(self.style.SUCCESS('\n=== Ensamblaje v7.5 finalizado ===\n'))
