"""
laboratorio/management/commands/seed_rangos_iso15189.py
════════════════════════════════════════════════════════════════════════════════
Comando para cargar rangos de referencia ISO 15189 (CLSI EP28-A3c / Harrison's).
Incluye valores críticos de pánico para los parámetros más comunes.

Uso:
    python manage.py seed_rangos_iso15189
    python manage.py seed_rangos_iso15189 --limpiar   # Borra los existentes primero
════════════════════════════════════════════════════════════════════════════════
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from laboratorio.models import Parametro, RangoReferenciaParametro


# ── Base de datos de rangos (fuente: CLSI EP28-A3c + Harrison's 21st ed.) ─────
# Formato: (nombre_parametro, sexo, edad_min, edad_max, min, max, crit_bajo, crit_alto, unidad, fuente)
# Nombres exactos como aparecen en el catalogo de la DB
RANGOS_REFERENCIA = [
    # ── QUIMICA SANGUINEA ─────────────────────────────────────────────────────
    ('GLUCOSA',                              'A', 0,  999,   70.0, 99.0,   40.0, 500.0, 'mg/dL', 'CLSI'),
    ('GLUCOSA POSTPANDRIAL',                 'A', 0,  999,   70.0, 140.0,  40.0, 500.0, 'mg/dL', 'CLSI'),
    ('Creatinina',                           'M', 18, 999,   0.7,  1.3,    None, 15.0,  'mg/dL', 'HARRISON'),
    ('Creatinina',                           'F', 18, 999,   0.6,  1.1,    None, 15.0,  'mg/dL', 'HARRISON'),
    ('UREA',                                 'A', 18, 999,   7.0,  25.0,   None, 200.0, 'mg/dL', 'CLSI'),
    ('ACIDO URICO',                          'M', 18, 999,   3.4,  7.0,    None, 15.0,  'mg/dL', 'CLSI'),
    ('ACIDO URICO',                          'F', 18, 999,   2.4,  6.0,    None, 15.0,  'mg/dL', 'CLSI'),
    ('COLESTEROL',                           'A', 18, 999,   None, 200.0,  None, 600.0, 'mg/dL', 'CLSI'),
    ('TRIGLICERIDOS',                        'A', 18, 999,   None, 150.0,  None, 1000.0,'mg/dL', 'CLSI'),
    ('Colesterol de alta densidad (HDL)',    'M', 18, 999,   40.0, None,   None, None,  'mg/dL', 'CLSI'),
    ('Colesterol de alta densidad (HDL)',    'F', 18, 999,   50.0, None,   None, None,  'mg/dL', 'CLSI'),
    ('Colesterol de baja densidad (LDL)',    'A', 18, 999,   None, 100.0,  None, None,  'mg/dL', 'CLSI'),

    # ── ELECTROLITOS ─────────────────────────────────────────────────────────
    ('SODIO',                                'A', 0,  999,   136.0, 145.0, 120.0, 160.0, 'mEq/L', 'CLSI'),
    ('POTASIO',                              'A', 0,  999,   3.5,   5.1,   2.5,   6.5,   'mEq/L', 'CLSI'),
    ('CALCIO',                               'A', 0,  999,   8.6,   10.0,  6.5,   13.0,  'mg/dL', 'CLSI'),
    ('MAGNESIO SERICO',                      'A', 0,  999,   1.7,   2.2,   1.0,   4.9,   'mg/dL', 'CLSI'),

    # ── FUNCION HEPATICA ──────────────────────────────────────────────────────
    ('BILIRRUBINA TOTAL',                    'A', 0,  999,   0.2,  1.2,   None,  20.0,  'mg/dL', 'CLSI'),
    ('BILIRRUBINA DIRECTA',                  'A', 0,  999,   0.0,  0.3,   None,  None,  'mg/dL', 'CLSI'),
    ('TGO',                                  'M', 18, 999,   None, 40.0,  None,  None,  'U/L',   'CLSI'),
    ('TGO',                                  'F', 18, 999,   None, 32.0,  None,  None,  'U/L',   'CLSI'),
    ('TGP',                                  'M', 18, 999,   None, 41.0,  None,  None,  'U/L',   'CLSI'),
    ('TGP',                                  'F', 18, 999,   None, 31.0,  None,  None,  'U/L',   'CLSI'),
    ('FOSFATASA ALCALINA',                   'A', 18, 999,   44.0, 147.0, None,  None,  'U/L',   'CLSI'),
    ('Fosfatasa alcalina (ALP)',             'A', 18, 999,   44.0, 147.0, None,  None,  'U/L',   'CLSI'),
    ('Gammaglutamil transpeptidasa (GGT)',   'M', 18, 999,   None, 61.0,  None,  None,  'U/L',   'CLSI'),
    ('Gammaglutamil transpeptidasa (GGT)',   'F', 18, 999,   None, 36.0,  None,  None,  'U/L',   'CLSI'),
    ('PROTEINAS TOTALES',                    'A', 18, 999,   6.0,  8.3,   None,  None,  'g/dL',  'CLSI'),
    ('ALBUMINA',                             'A', 18, 999,   3.5,  5.0,   2.0,   None,  'g/dL',  'CLSI'),

    # ── TIROIDES ─────────────────────────────────────────────────────────────
    ('HORMONA ESTIMULANTE DE TIROIDES (TSH)','A', 18, 999,   0.4,  4.0,   None,  None,  'mUI/L', 'CLSI'),
    ('TSH NEONATAL',                         'A', 0,  1,     None, 10.0,  None,  None,  'mUI/L', 'CLSI'),

    # ── COAGULACION ───────────────────────────────────────────────────────────
    ('TIEMPO PARCIAL DE TROMBOPLASTINA',     'A', 18, 999,   25.0, 35.0,  None,  None,  'seg',   'CLSI'),

    # ── HEMOGLOBINA GLUCOSILADA ───────────────────────────────────────────────
    ('HEMOGLOBINA GLUCOSILADA',              'A', 18, 999,   None, 5.7,   None,  None,  '%',     'CLSI'),

    # ── INFLAMACION ───────────────────────────────────────────────────────────
    ('PROTEINA C REACTIVA',                  'A', 0,  999,   None, 1.0,   None,  None,  'mg/dL', 'CLSI'),
]


class Command(BaseCommand):
    help = 'Carga rangos de referencia ISO 15189 (CLSI/Harrison\'s) en RangoReferenciaParametro'

    def add_arguments(self, parser):
        parser.add_argument('--limpiar', action='store_true', help='Borra rangos existentes antes de cargar')

    def handle(self, *args, **options):
        if options['limpiar']:
            deleted, _ = RangoReferenciaParametro.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Eliminados {deleted} rangos existentes'))

        cargados = 0
        omitidos = 0
        no_encontrados = set()

        for nombre, sexo, edad_min, edad_max, v_min, v_max, c_bajo, c_alto, unidad, fuente in RANGOS_REFERENCIA:
            param = Parametro.objects.filter(nombre__iexact=nombre).first()
            if not param:
                # Buscar con icontains
                param = Parametro.objects.filter(nombre__icontains=nombre.split()[0]).first()

            if not param:
                no_encontrados.add(nombre)
                omitidos += 1
                continue

            _, created = RangoReferenciaParametro.objects.get_or_create(
                parametro=param,
                sexo=sexo,
                edad_min_anios=Decimal(str(edad_min)),
                edad_max_anios=Decimal(str(edad_max)),
                defaults={
                    'valor_minimo': Decimal(str(v_min)) if v_min is not None else None,
                    'valor_maximo': Decimal(str(v_max)) if v_max is not None else None,
                    'valor_critico_bajo': Decimal(str(c_bajo)) if c_bajo is not None else None,
                    'valor_critico_alto': Decimal(str(c_alto)) if c_alto is not None else None,
                    'unidad': unidad,
                    'fuente': fuente,
                    'activo': True,
                }
            )
            if created:
                cargados += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nRangos ISO 15189 cargados: {cargados} nuevos | {omitidos} omitidos'
        ))

        if no_encontrados:
            self.stdout.write(self.style.WARNING(
                f'Parametros no encontrados en catalogo: {", ".join(sorted(no_encontrados))}'
            ))

        self.stdout.write(self.style.SUCCESS(
            'ISO 15189 activo - El motor de validacion usara estos rangos automaticamente.'
        ))
