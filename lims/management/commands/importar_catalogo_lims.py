"""
Importador del catálogo LIMS desde los CSV legacy (Nivel 1).
=============================================================
Fuentes:
  datos_lims/Parametros.csv         → lims.Analito (+ costo_lista desde Costo)
  datos_lims/Valores_normalidad.csv → lims.ValorReferenciaAnalito

Pipeline v7.5 completo: python manage.py ensamblar_lims_v75

Mapeos críticos:
  Permite_venta_directa: 'Si' / 'Sí' → True, resto → False
  Unidad (rangos): '2 (dias)' → DIAS, '1 (años)' → ANOS
  Sexo (rangos): 'Indistinto' → I, 'Masculino' → M, 'Femenino' → F

Uso:
  python manage.py importar_catalogo_lims
  python manage.py importar_catalogo_lims --dry-run   (sin guardar)
  python manage.py importar_catalogo_lims --reset     (borra lims.* primero)
  python manage.py importar_catalogo_lims --con-perfiles  (Niveles 2-4: perfiles, paquetes, precios)
  python manage.py ensamblar_lims_v75   (pipeline completo 1→4)
"""
import csv
import os
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from lims.models import Analito, ValorReferenciaAnalito


BASE_DIR = getattr(settings, 'BASE_DIR', os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
))
CSV_PARAMETROS      = os.path.join(BASE_DIR, 'datos_lims', 'Parametros.csv')
CSV_VALORES_REF     = os.path.join(BASE_DIR, 'datos_lims', 'Valores_normalidad.csv')


def _bool(valor: str) -> bool:
    return (valor or '').strip().lower() in ('si', 'sí', 's', 'yes', '1', 'true')


def _int_o_none(valor: str):
    try:
        return int(str(valor).strip())
    except (ValueError, TypeError):
        return None


def _decimal_o_none(valor: str):
    try:
        return Decimal(str(valor).strip())
    except (InvalidOperation, TypeError):
        return None


def _decimal_costo(valor) -> Decimal:
    """Costo desde CSV (Parametros / Examenes / Paquetes)."""
    if valor is None or valor == '':
        return Decimal('0.00')
    try:
        s = str(valor).strip().replace(',', '.')
        return Decimal(s).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError):
        return Decimal('0.00')


def _mapear_sexo(valor: str) -> str:
    v = (valor or '').strip().lower()
    if 'masculino' in v or v == 'm':
        return 'M'
    if 'femenino' in v or v == 'f':
        return 'F'
    return 'I'  # Indistinto


def _mapear_unidad_edad(valor: str) -> str:
    """
    '2 (dias)' → 'DIAS'
    '1 (años)' / '1 (a?os)' (BOM/encoding replacement) → 'ANOS'
    """
    v = (valor or '').strip().lower()
    # '2' prefijo o la palabra 'dia' en cualquier variante
    if v.startswith('2') or 'dia' in v:
        return 'DIAS'
    return 'ANOS'


def _mapear_tipo_resultado(valor: str) -> str:
    v = (valor or '').strip().lower()
    if 'numerico' in v or 'numérico' in v or 'numeric' in v:
        return 'NUMERICO'
    if 'opcion' in v or 'opción' in v or 'selec' in v:
        return 'OPCIONES'
    if 'calculo' in v or 'cálculo' in v or 'formula' in v:
        return 'CALCULO'
    return 'TEXTO'


class Command(BaseCommand):
    help = 'Importa Parametros.csv y Valores_normalidad.csv a las tablas lims.*'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Simular importación sin guardar nada en la BD',
        )
        parser.add_argument(
            '--reset', action='store_true',
            help='Eliminar todos los analitos lims.* antes de importar',
        )
        parser.add_argument(
            '--con-perfiles', action='store_true',
            help='Al terminar analitos+rangos: perfiles, paquetes y sincronizar precios (v7.5)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        reset   = options['reset']

        if dry_run:
            self.stdout.write(self.style.WARNING('  [DRY-RUN] No se guardarán cambios.\n'))

        # ── Opcional: reset previo ────────────────────────────────────────────
        if reset and not dry_run:
            self.stdout.write('Borrando registros lims.* previos...')
            ValorReferenciaAnalito.objects.all().delete()
            Analito.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('  Registros lims.* eliminados.\n'))

        # ── Fase A: importar Parametros.csv → Analito ────────────────────────
        self.stdout.write(f'Leyendo {CSV_PARAMETROS} ...')
        if not os.path.exists(CSV_PARAMETROS):
            self.stdout.write(self.style.ERROR(f'  Archivo no encontrado: {CSV_PARAMETROS}'))
            return

        creados = actualizados = errores = omitidos = 0
        id_legacy_set = {}  # id_legacy → pk para cruzar con valores de referencia

        with open(CSV_PARAMETROS, newline='', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f)
            with transaction.atomic():
                for fila in reader:
                    id_leg = _int_o_none(fila.get('Id_parametro', ''))
                    codigo = (fila.get('Codigo') or '').strip()
                    if not codigo:
                        omitidos += 1
                        continue

                    abrev   = (fila.get('Abreviatura') or codigo).strip()
                    nombre  = (fila.get('Descripcion') or codigo).strip()

                    # Evitar duplicados por código — ajustar si código ya existe
                    codigo_final = codigo
                    if Analito.objects.filter(codigo=codigo_final).exists() and not reset:
                        # Buscar por id_legacy para actualizar
                        if id_leg and Analito.objects.filter(id_legacy=id_leg).exists():
                            # Actualizar en su lugar
                            pass
                        else:
                            # Hacer único añadiendo sufijo del id_legacy
                            codigo_final = f'{codigo}-{id_leg}' if id_leg else f'{codigo}-x'

                    fm = (fila.get('Formula') or '').strip()
                    datos = {
                        'abreviatura':      abrev,
                        'nombre':           nombre,
                        'clave_hoja':       (fila.get('Clave_hoja_trabajo') or '').strip(),
                        'departamento':     (fila.get('Departamento') or 'Sin departamento').strip(),
                        'tipo_muestra':     (fila.get('Tipo_muestra') or '').strip(),
                        'metodologia':      (fila.get('Metodo') or '').strip(),
                        'tipo_resultado':   _mapear_tipo_resultado(fila.get('Tipo_resultado', '')),
                        'unidades':         (fila.get('Unidades') or '').strip(),
                        'decimales':        _int_o_none(fila.get('Decimales', '')) or 2,
                        'formula':          fm,
                        'es_calculado':     bool(fm),
                        'opciones_texto':   (fila.get('Resultado_opciones') or '').strip(),
                        'imprime_en_negritas': _bool(fila.get('Imprime_en_negritas', '')),
                        'imprimir_metodo':  _bool(fila.get('Imprimir_metodo_resultado', '')),
                        'es_vendible_individualmente': _bool(fila.get('Permite_venta_directa', '')),
                        'indicaciones':     (fila.get('Indicaciones') or '').strip(),
                        'notas':            (fila.get('Notas') or '').strip(),
                        'activo':           True,
                        'costo_lista':      _decimal_costo(fila.get('Costo')),
                    }

                    try:
                        if dry_run:
                            nombre_safe = nombre[:60].encode('ascii', 'replace').decode()
                            self.stdout.write(
                                f'  [DRY] Analito: {codigo_final} | {nombre_safe}'
                            )
                            creados += 1
                        else:
                            obj, created = Analito.objects.update_or_create(
                                id_legacy=id_leg if id_leg else None,
                                defaults={**datos, 'codigo': codigo_final},
                            ) if id_leg else Analito.objects.get_or_create(
                                codigo=codigo_final,
                                defaults=datos,
                            )
                            if id_leg:
                                id_legacy_set[id_leg] = obj.pk
                            if created:
                                creados += 1
                            else:
                                actualizados += 1
                    except Exception as e:
                        errores += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  [ERR] {codigo}: {str(e).encode("ascii","replace").decode()}'
                            )
                        )

        self.stdout.write(
            f'\n  Analitos — creados: {creados} | actualizados: {actualizados} '
            f'| omitidos: {omitidos} | errores: {errores}'
        )

        # ── Fase B: importar Valores_normalidad.csv → ValorReferenciaAnalito ─
        self.stdout.write(f'\nLeyendo {CSV_VALORES_REF} ...')
        if not os.path.exists(CSV_VALORES_REF):
            self.stdout.write(self.style.WARNING(
                f'  Archivo no encontrado: {CSV_VALORES_REF} — se omite la fase B'
            ))
            self._resumen_final(dry_run, options.get('con_perfiles', False))
            return

        # Siempre reconstruir el mapa desde la BD (evita errores en re-runs)
        id_legacy_set = {
            a.id_legacy: a.pk
            for a in Analito.objects.exclude(id_legacy=None)
        }
        self.stdout.write(f'  Mapa id_legacy: {len(id_legacy_set)} analitos indexados')

        v_creados = v_errores = v_omitidos = 0

        with open(CSV_VALORES_REF, newline='', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f)
            with transaction.atomic():
                for fila in reader:
                    id_leg  = _int_o_none(fila.get('Id_parametro', ''))
                    if id_leg is None or id_leg not in id_legacy_set:
                        v_omitidos += 1
                        continue

                    analito_pk = id_legacy_set[id_leg]
                    sexo       = _mapear_sexo(fila.get('Sexo', ''))
                    unidad     = _mapear_unidad_edad(fila.get('Unidad', ''))
                    e_min      = _int_o_none(fila.get('Edad_min', ''))
                    e_max      = _int_o_none(fila.get('Edad_max', ''))
                    r_min      = _decimal_o_none(fila.get('Ref_min', ''))
                    r_max      = _decimal_o_none(fila.get('Ref_max', ''))

                    if e_min is None or e_max is None:
                        v_omitidos += 1
                        continue

                    try:
                        if dry_run:
                            self.stdout.write(
                                f'  [DRY] Rango: analito_id={analito_pk} | '
                                f'{sexo} | {unidad} | {e_min}–{e_max}'
                            )
                            v_creados += 1
                        else:
                            ValorReferenciaAnalito.objects.update_or_create(
                                analito_id=analito_pk,
                                sexo=sexo,
                                unidad_edad=unidad,
                                edad_minima=e_min,
                                edad_maxima=e_max,
                                defaults={
                                    'ref_minimo': r_min,
                                    'ref_maximo': r_max,
                                },
                            )
                            v_creados += 1
                    except Exception as e:
                        v_errores += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  [ERR] Rango analito_id={analito_pk}: {e}'
                            )
                        )

        self.stdout.write(
            f'  Rangos — creados/actualizados: {v_creados} '
            f'| omitidos: {v_omitidos} | errores: {v_errores}'
        )

        self._resumen_final(dry_run, options.get('con_perfiles', False))

    def _resumen_final(self, dry_run: bool, con_perfiles: bool = False):
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY-RUN] Nada fue guardado.'))
            return
        total_a = Analito.objects.count()
        total_r = ValorReferenciaAnalito.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\n=== Importación completada ===\n'
            f'  lims.Analito:                {total_a}\n'
            f'  lims.ValorReferenciaAnalito: {total_r}\n'
        ))
        self.stdout.write(
            'Proximos pasos:\n'
            '  Pipeline completo: python manage.py ensamblar_lims_v75 --saltar-nivel1\n'
            '  UI: /lims/perfiles/, /lims/paquetes/, /lims/precios/\n'
        )
        if con_perfiles and not dry_run:
            self.stdout.write('\nEjecutando Niveles 2-4 (perfiles, paquetes, precios)...\n')
            call_command('importar_examenes_perfil_lims', stdout=self.stdout, stderr=self.stderr)
            call_command('importar_paquetes_perfil_lims', stdout=self.stdout, stderr=self.stderr)
            call_command('sincronizar_precios_lims', stdout=self.stdout, stderr=self.stderr)
