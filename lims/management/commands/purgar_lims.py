"""
Comando de Hard Reset para el módulo LIMS.
Elimina IRREVERSIBLEMENTE todos los datos de laboratorio (órdenes, resultados,
catálogos técnicos, perfiles, paquetes, precios, valores de referencia).

Uso:
    python manage.py purgar_lims
    python manage.py purgar_lims --force   (sin confirmación interactiva — solo para CI)

ADVERTENCIA: Hace backup de conteos antes de borrar, pero NO hace backup de datos.
Haz pg_dump antes de ejecutar en producción.
"""
import sys

from django.core.management.base import BaseCommand
from django.db import connection, transaction
import logging


class Command(BaseCommand):
    help = 'Hard Reset LIMS: elimina todos los registros de laboratorio, catálogos y LIMS.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Omitir confirmación interactiva (usar solo en scripts automatizados)',
        )

    def _contar(self):
        """Retorna un dict {tabla: conteo} para las tablas que se van a purgar."""
        conteos = {}
        tablas = [
            # lims (propios — se borran para reset total)
            ('lims_valorreferenciaanalito', 'lims.ValorReferenciaAnalito'),
            ('lims_precioitem',             'lims.PrecioItem'),
            ('lims_paqueteLims_analitos',   'lims.PaqueteLims_analitos (M2M)'),
            ('lims_paqueteLims_perfiles',   'lims.PaqueteLims_perfiles (M2M)'),
            ('lims_perfilLims_analitos',    'lims.PerfilLims_analitos (M2M)'),
            ('lims_paqueteLims',            'lims.PaqueteLims'),
            ('lims_perfilLims',             'lims.PerfilLims'),
            ('lims_analito',                'lims.Analito'),
            # laboratorio
            ('laboratorio_valorreferencia',    'laboratorio.ValorReferencia'),
            ('laboratorio_perfilLaboratorio_pruebas', 'lab.PerfilLaboratorio_pruebas (M2M)'),
            ('laboratorio_perfilLaboratorio',  'laboratorio.PerfilLaboratorio'),
            ('laboratorio_detalleorden',       'laboratorio.DetalleOrden'),
            ('laboratorio_estudio',            'laboratorio.Estudio'),
            # core
            ('core_rangoreferencia',           'core.RangoReferencia'),
            ('core_parametro',                 'core.Parametro'),
            ('core_convenioprecioestudio',     'core.ConvenioPrecioEstudio'),
            ('core_estudio_componentes',       'core.Estudio_componentes (M2M)'),
            ('core_estudio',                   'core.Estudio'),
        ]
        with connection.cursor() as cur:
            for table, label in tablas:
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                    conteos[label] = cur.fetchone()[0]
                except Exception:
                    logging.getLogger(__name__).exception("Error inesperado en _contar (purgar_lims.py)")
                    conteos[label] = 'n/a'
        return conteos

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            '\n' + '=' * 65
        ))
        self.stdout.write(self.style.WARNING(
            '  HARD RESET LIMS — OPERACIÓN IRREVERSIBLE'
        ))
        self.stdout.write(self.style.WARNING(
            '=' * 65
        ))
        self.stdout.write(
            '\nEsta operación BORRARÁ permanentemente:\n'
            '  • Todos los analitos, perfiles, paquetes y precios (lims.*)\n'
            '  • Todos los estudios, perfiles y rangos (laboratorio.*)\n'
            '  • Catálogo técnico: core.Estudio, Parametro, RangoReferencia\n'
            '  • Precios de convenio: core.ConvenioPrecioEstudio\n'
            '  • Órdenes de trabajo y resultados (laboratorio.DetalleOrden)\n'
        )

        # Mostrar conteos actuales
        self.stdout.write('--- Conteo actual de registros ---')
        conteos = self._contar()
        for label, n in conteos.items():
            self.stdout.write(f'  {label}: {n}')
        self.stdout.write('')

        if not options['force']:
            self.stdout.write(
                self.style.ERROR(
                    'Para confirmar, escribe exactamente:  CONFIRMO\n'
                    '(cualquier otra entrada cancela la operación)\n'
                )
            )
            try:
                respuesta = input('> ').strip()
            except (KeyboardInterrupt, EOFError):
                respuesta = ''

            if respuesta != 'CONFIRMO':
                self.stdout.write(self.style.SUCCESS('\nOperación CANCELADA. No se borró nada.'))
                sys.exit(0)

        self.stdout.write('\nEjecutando purga...')

        with transaction.atomic():
            with connection.cursor() as cur:
                # 1. Deshabilitar restricciones FK temporalmente (PostgreSQL)
                cur.execute('SET CONSTRAINTS ALL DEFERRED;')

                # ── lims ────────────────────────────────────────────────────
                self._truncar(cur, 'lims_valorreferenciaanalito')
                self._truncar(cur, 'lims_precioitem')
                self._truncar_m2m(cur, 'lims_paqueteLims_analitos')
                self._truncar_m2m(cur, 'lims_paqueteLims_perfiles')
                self._truncar_m2m(cur, 'lims_perfilLims_analitos')
                self._truncar(cur, 'lims_paqueteLims')
                self._truncar(cur, 'lims_perfilLims')
                self._truncar(cur, 'lims_analito')

                # ── laboratorio ─────────────────────────────────────────────
                self._truncar(cur, 'laboratorio_valorreferencia')
                self._truncar_m2m(cur, 'laboratorio_perfilLaboratorio_pruebas')
                self._truncar(cur, 'laboratorio_perfilLaboratorio')
                self._truncar(cur, 'laboratorio_detalleorden')
                self._truncar(cur, 'laboratorio_estudio')

                # ── core ─────────────────────────────────────────────────────
                self._truncar(cur, 'core_rangoreferencia')
                self._truncar(cur, 'core_parametro')
                self._truncar(cur, 'core_convenioprecioestudio')
                self._truncar_m2m(cur, 'core_estudio_componentes')
                self._truncar(cur, 'core_estudio')

                # Re-habilitar restricciones
                cur.execute('SET CONSTRAINTS ALL IMMEDIATE;')

        self.stdout.write(self.style.SUCCESS(
            '\n¡Purga completada exitosamente!\n'
            'La base de datos queda en blanco.\n'
            'Ejecuta: python manage.py importar_catalogo_lims\n'
        ))

    # ── helpers ──────────────────────────────────────────────────────────────

    def _truncar(self, cur, tabla):
        """TRUNCATE con RESTART IDENTITY y CASCADE para evitar FK colgadas."""
        try:
            cur.execute(f'TRUNCATE TABLE "{tabla}" RESTART IDENTITY CASCADE;')
            self.stdout.write(f'  [OK] {tabla}')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _truncar (purgar_lims.py)")
            self.stdout.write(self.style.WARNING(f'  [SKIP] {tabla}: {e}'))

    def _truncar_m2m(self, cur, tabla):
        """DELETE simple para tablas M2M que no tienen secuencia propia."""
        try:
            cur.execute(f'DELETE FROM "{tabla}";')
            self.stdout.write(f'  [OK] {tabla} (M2M)')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _truncar_m2m (purgar_lims.py)")
            self.stdout.write(self.style.WARNING(f'  [SKIP] {tabla}: {e}'))