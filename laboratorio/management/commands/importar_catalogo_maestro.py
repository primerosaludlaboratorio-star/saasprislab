"""
MOTOR DE INGESTA UNIFICADO — CATÁLOGO CLÍNICO PRISLAB
======================================================
Lee los 4 archivos de origen y realiza un upsert atómico completo:

  1. ReporteExamenes.xlsx   → laboratorio.Estudio (metadatos + etiquetas + composición)
  2. ReportePaquete.xlsx    → laboratorio.PerfilLaboratorio (paquetes + composición)
  3. ReporteParametros.xlsx → laboratorio.Parametro + RangoReferenciaParametro
  4. Tarifa_Detalle.xlsx    → precio_base en Estudio y PerfilLaboratorio

Uso:
    python manage.py importar_catalogo_maestro
    python manage.py importar_catalogo_maestro --dry-run
    python manage.py importar_catalogo_maestro --solo-precios
    python manage.py importar_catalogo_maestro --solo-parametros
"""
import os
import decimal
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger(__name__)

# ── Rutas de los archivos fuente ─────────────────────────────────────────────
# Busca primero en data/ del proyecto (incluido en Docker), luego en Music/
_PROJECT_DATA = Path(__file__).resolve().parents[3] / 'data'
_LOCAL_MUSIC  = Path(os.path.expanduser('~')) / 'Music'
_LOCAL_DL     = Path(os.path.expanduser('~')) / 'Downloads'

def _find_file(filename, fallback_dir=None):
    """Busca el archivo en data/ del proyecto o en la carpeta alternativa."""
    candidate = _PROJECT_DATA / filename
    if candidate.exists():
        return candidate
    if fallback_dir:
        alt = Path(fallback_dir) / filename
        if alt.exists():
            return alt
    return candidate  # Retorna aunque no exista para que el error sea claro

ARCHIVO_EXAMENES   = _find_file('PRISLAB_ReporteExamenes.xlsx', _LOCAL_MUSIC)
ARCHIVO_PAQUETES   = _find_file('PRISLAB_ReportePaquete.xlsx', _LOCAL_MUSIC)
ARCHIVO_PARAMETROS = _find_file('PRISLAB_ReporteParametros.xlsx', _LOCAL_MUSIC)
ARCHIVO_TARIFA     = _find_file('Tarifa_Detalle_20260330_055214.xlsx', _LOCAL_DL)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_decimal(val, default=None):
    try:
        if val is None or str(val).strip() in ('', '-', 'N/A'):
            return default
        return decimal.Decimal(str(val).replace(',', '').strip())
    except (ValueError, decimal.InvalidOperation, TypeError):
        return default


def _safe_int(val, default=0):
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def _trunc(val, max_len):
    """Trunca un string al máximo permitido por el campo del modelo."""
    if val is None:
        return None
    s = str(val).strip()
    return s[:max_len] if len(s) > max_len else (s or None)


def _bool_excel(val):
    """Convierte 'Si'/'No'/'Yes'/'No' a bool."""
    if val is None:
        return False
    return str(val).strip().lower() in ('si', 'sí', 'yes', '1', 'true')


def _sexo_rango(val):
    """Normaliza sexo a los choices de RangoReferenciaParametro."""
    mapping = {
        'masculino': 'M', 'male': 'M', 'm': 'M',
        'femenino': 'F', 'female': 'F', 'f': 'F',
        'indistinto': 'A', 'ambos': 'A', 'both': 'A', '': 'A',
    }
    return mapping.get(str(val or '').strip().lower(), 'A')


def _edad_a_anios(valor, unidad):
    """Convierte edad a años decimales normalizando días."""
    v = _safe_decimal(valor, 0)
    if v is None:
        return decimal.Decimal('0')
    u = str(unidad or '').lower()
    if 'dia' in u or 'day' in u:
        return (v / decimal.Decimal('365')).quantize(decimal.Decimal('0.01'))
    return v


def _leer_excel(ruta, hoja=0):
    """Carga una hoja de un Excel y devuelve lista de filas."""
    import openpyxl
    wb = openpyxl.load_workbook(str(ruta), data_only=True)
    if isinstance(hoja, int):
        ws = wb.worksheets[hoja]
    else:
        ws = wb[hoja]
    return [r for r in ws.iter_rows(values_only=True)]


# ── Command principal ─────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Importa el catálogo clínico completo desde los archivos Excel originales del LIMS.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Simula la importación sin guardar nada en la BD.')
        parser.add_argument('--solo-precios', action='store_true',
                            help='Solo actualiza precios desde Tarifa_Detalle.xlsx.')
        parser.add_argument('--solo-parametros', action='store_true',
                            help='Solo importa parámetros y rangos de referencia.')
        parser.add_argument('--examenes-dir', type=str,
                            help='Directorio alternativo donde buscar los archivos Excel.')

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbosity = options['verbosity']

        if options.get('examenes_dir'):
            alt = Path(options['examenes_dir'])
            global ARCHIVO_EXAMENES, ARCHIVO_PAQUETES, ARCHIVO_PARAMETROS
            ARCHIVO_EXAMENES   = alt / 'PRISLAB_ReporteExamenes.xlsx'
            ARCHIVO_PAQUETES   = alt / 'PRISLAB_ReportePaquete.xlsx'
            ARCHIVO_PARAMETROS = alt / 'PRISLAB_ReporteParametros.xlsx'

        if self.dry_run:
            self.stdout.write(self.style.WARNING('⚠️  MODO DRY-RUN: no se guardarán cambios.'))

        stats = {
            'examenes_actualizados': 0,
            'examenes_creados': 0,
            'paquetes_actualizados': 0,
            'parametros_creados': 0,
            'parametros_actualizados': 0,
            'relaciones_creadas': 0,
            'rangos_creados': 0,
            'rangos_actualizados': 0,
            'precios_actualizados': 0,
        }

        try:
            with transaction.atomic():
                from core.tenant import tenant_bypass
                with tenant_bypass():
                    if not options['solo_parametros']:
                        self._importar_tarifa(stats)
                    if not options['solo_precios']:
                        self._importar_examenes(stats)
                        self._importar_paquetes(stats)
                        self._importar_parametros(stats)
                        self._importar_rangos_referencia(stats)
                        self._vincular_examen_parametro(stats)

                if self.dry_run:
                    raise DryRunInterrupt()

        except DryRunInterrupt:
            self.stdout.write(self.style.WARNING('\n🔍 DRY-RUN completado. Revertiendo...'))
        except (FileNotFoundError, PermissionError) as exc:
            raise CommandError(f'Error de archivo: {exc}') from exc
        except DatabaseError as exc:
            raise CommandError(f'Error de base de datos: {exc}') from exc
        except ValueError as exc:
            raise CommandError(f'Error de datos: {exc}') from exc
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en handle (importar_catalogo_maestro.py)")
            raise CommandError(f'Error inesperado durante la importación: {exc}') from exc

        self._imprimir_resumen(stats)

    # ────────────────────────────────────────────────────────────────────────
    # PASO 1 — PRECIOS (Tarifa_Detalle.xlsx)
    # ────────────────────────────────────────────────────────────────────────

    def _importar_tarifa(self, stats):
        from laboratorio.models import Estudio, PerfilLaboratorio

        if not ARCHIVO_TARIFA.exists():
            self.stdout.write(self.style.WARNING(f'Tarifa no encontrada: {ARCHIVO_TARIFA}'))
            return

        self._log('📋 Procesando precios desde Tarifa_Detalle.xlsx...')
        rows = _leer_excel(ARCHIVO_TARIFA, hoja='Reporte')

        # La tarifa tiene 4 filas de cabecera
        data = [r for r in rows[4:] if any(v is not None for v in r)]

        # Construir mapa codigo -> precio
        tarifa_map = {}
        for r in data:
            cod = str(r[1] or '').strip().upper()
            precio = _safe_decimal(r[4], decimal.Decimal('0.00'))
            if cod:
                tarifa_map[cod] = precio

        # Actualizar Estudio
        for estudio in Estudio.objects.all():
            cod = str(estudio.codigo or '').strip().upper()
            abrev = str(estudio.abreviatura or '').strip().upper()
            precio = tarifa_map.get(cod) or tarifa_map.get(abrev)
            if precio is not None and precio != estudio.precio_base:
                estudio.precio_base = precio
                if not self.dry_run:
                    estudio.save(update_fields=['precio_base'])
                stats['precios_actualizados'] += 1

        # Actualizar PerfilLaboratorio (precio por nombre)
        for perfil in PerfilLaboratorio.objects.all():
            nombre_upper = str(perfil.nombre or '').strip().upper()
            precio = tarifa_map.get(nombre_upper)
            if precio is not None:
                old = getattr(perfil, 'precio', decimal.Decimal('0')) or decimal.Decimal('0')
                if precio != old:
                    perfil.precio = precio
                    if not self.dry_run:
                        perfil.save(update_fields=['precio'])
                    stats['precios_actualizados'] += 1

        self._log(f'   ✅ {stats["precios_actualizados"]} precios actualizados')

    # ────────────────────────────────────────────────────────────────────────
    # PASO 2 — EXÁMENES (ReporteExamenes.xlsx)
    # ────────────────────────────────────────────────────────────────────────

    def _importar_examenes(self, stats):
        from laboratorio.models import Estudio, CategoriaExamen

        if not ARCHIVO_EXAMENES.exists():
            self.stdout.write(self.style.WARNING(f'Archivo no encontrado: {ARCHIVO_EXAMENES}'))
            return

        self._log('🔬 Procesando exámenes...')
        rows = _leer_excel(ARCHIVO_EXAMENES, hoja='Examenes')
        headers = rows[0]
        data = [r for r in rows[1:] if any(v for v in r)]

        # Mapa codigo -> tipo_muestra desde hoja Etiquetas
        etq_rows = _leer_excel(ARCHIVO_EXAMENES, hoja='Etiquetas')
        tipo_muestra_map = {}
        for r in etq_rows[1:]:
            if r[0]:
                cod = str(r[0]).strip().upper()
                tipo_muestra_map.setdefault(cod, [])
                if r[4]:
                    tipo_muestra_map[cod].append(str(r[4]))

        cat_general, _ = CategoriaExamen.objects.get_or_create(
            nombre='GENERAL',
            defaults={'descripcion': 'Categoría general de exámenes'}
        )

        for r in data:
            if not r[1]:
                continue
            cod     = str(r[1]).strip()
            abrev   = str(r[2] or '').strip()
            desc    = str(r[3] or '').strip()
            titulo  = str(r[4] or '').strip()
            tiempo  = str(r[5] or '').strip()
            metodo  = str(r[6] or '').strip()
            venta   = _bool_excel(r[7])
            costo   = _safe_decimal(r[8], decimal.Decimal('0.00'))
            sexo_ex = str(r[10] or 'Ambos').strip()
            indic   = str(r[11] or '').strip()
            notas_i = str(r[13] or '').strip()
            alinea  = str(r[14] or '').strip()
            color   = str(r[15] or '').strip()

            muestra_list = tipo_muestra_map.get(cod.upper(), [])
            muestra = ', '.join(sorted(set(muestra_list)))

            # Normalizar sexo a choices del modelo
            sexo_norm = 'Ambos'
            if sexo_ex.lower() in ('masculino', 'male', 'm'):
                sexo_norm = 'Masculino'
            elif sexo_ex.lower() in ('femenino', 'female', 'f'):
                sexo_norm = 'Femenino'

            # Buscar por código (prioritario) o nombre
            estudio = (
                Estudio.objects.filter(codigo=cod).first()
                or Estudio.objects.filter(abreviatura=abrev).first()
                or Estudio.objects.filter(nombre__iexact=desc).first()
            )

            campos = dict(
                abreviatura=_trunc(abrev, 30),
                metodo=_trunc(metodo, 255),
                titulo_reporte=_trunc(titulo, 200),
                titulo_color=_trunc(color, 20),
                titulo_alineacion=_trunc(alinea, 30),
                sexo_aplicable=sexo_norm,
                permite_venta_directa=venta,
                activo=True,
                notas_internas=notas_i or None,
                tiempo_proceso=_trunc(tiempo, 50),
                indicaciones=indic or None,
                muestra_requerida=_trunc(muestra, 200),
            )
            if costo and costo > 0:
                campos['precio_base'] = costo

            if estudio:
                for k, v in campos.items():
                    setattr(estudio, k, v)
                if not self.dry_run:
                    estudio.save()
                stats['examenes_actualizados'] += 1
            else:
                # Crear nuevo
                nombre_final = desc or titulo or cod
                estudio = Estudio(
                    categoria=cat_general,
                    nombre=nombre_final,
                    codigo=cod,
                    **campos,
                )
                if not self.dry_run:
                    estudio.save()
                stats['examenes_creados'] += 1

        self._log(f'   ✅ {stats["examenes_actualizados"]} actualizados | {stats["examenes_creados"]} creados')

    # ────────────────────────────────────────────────────────────────────────
    # PASO 3 — PAQUETES (ReportePaquete.xlsx)
    # ────────────────────────────────────────────────────────────────────────

    def _importar_paquetes(self, stats):
        from laboratorio.models import PerfilLaboratorio, Estudio, CategoriaExamen

        if not ARCHIVO_PAQUETES.exists():
            self.stdout.write(self.style.WARNING(f'Archivo no encontrado: {ARCHIVO_PAQUETES}'))
            return

        self._log('📦 Procesando paquetes...')
        rows = _leer_excel(ARCHIVO_PAQUETES, hoja='Paquetes')
        data = [r for r in rows[1:] if any(v for v in r)]

        cat_paq, _ = CategoriaExamen.objects.get_or_create(
            nombre='PAQUETES',
            defaults={'descripcion': 'Paquetes y perfiles de laboratorio'}
        )

        # Mapa abreviatura -> perfil para vincular en el paso siguiente
        perfil_abrev_map = {}

        for r in data:
            if not r[0]:
                continue
            abrev  = str(r[0]).strip()
            desc   = str(r[1] or '').strip()
            indic  = str(r[2] or '').strip()
            notas  = str(r[3] or '').strip()
            costo  = _safe_decimal(r[5], decimal.Decimal('0.00'))

            perfil = PerfilLaboratorio.objects.filter(nombre__iexact=desc).first()
            if perfil:
                perfil.descripcion = indic or notas or perfil.descripcion
                if costo and costo > 0:
                    perfil.precio = costo
                if not self.dry_run:
                    perfil.save(update_fields=['descripcion', 'precio'])
                stats['paquetes_actualizados'] += 1
            else:
                perfil = PerfilLaboratorio(
                    nombre=desc or abrev,
                    descripcion=indic or notas,
                    area_pertenencia=cat_paq,
                    precio=costo or decimal.Decimal('0.00'),
                )
                if not self.dry_run:
                    perfil.save()
                stats['paquetes_actualizados'] += 1

            perfil_abrev_map[abrev] = perfil

        # Vincular paquetes con sus estudios
        comp_rows = _leer_excel(ARCHIVO_PAQUETES, hoja='Prueba-perfil paquete')
        comp_data = [r for r in comp_rows[2:] if any(v for v in r)]

        for r in comp_data:
            paq_abrev   = str(r[0] or '').strip()
            estudio_cod = str(r[3] or '').strip()

            perfil = perfil_abrev_map.get(paq_abrev)
            if not perfil:
                perfil = PerfilLaboratorio.objects.filter(nombre__icontains=paq_abrev).first()
            if not perfil:
                continue

            estudio = (
                Estudio.objects.filter(abreviatura__iexact=estudio_cod).first()
                or Estudio.objects.filter(codigo__iexact=estudio_cod).first()
                or Estudio.objects.filter(nombre__iexact=estudio_cod).first()
            )
            if estudio and not self.dry_run:
                perfil.pruebas.add(estudio)
                stats['relaciones_creadas'] += 1

        self._log(f'   ✅ {stats["paquetes_actualizados"]} paquetes actualizados | {stats["relaciones_creadas"]} vínculos')

    # ────────────────────────────────────────────────────────────────────────
    # PASO 4 — PARÁMETROS (ReporteParametros.xlsx)
    # ────────────────────────────────────────────────────────────────────────

    def _importar_parametros(self, stats):
        from laboratorio.models import Parametro, Estudio, CategoriaExamen

        if not ARCHIVO_PARAMETROS.exists():
            self.stdout.write(self.style.WARNING(f'Archivo no encontrado: {ARCHIVO_PARAMETROS}'))
            return

        self._log('🧪 Procesando parámetros (806 registros)...')
        rows = _leer_excel(ARCHIVO_PARAMETROS, hoja='Parametros')
        data = [r for r in rows[1:] if any(v for v in r)]

        # Mapa etiqueta interfaz
        etq_rows = _leer_excel(ARCHIVO_PARAMETROS, hoja='Etiquetas')
        etq_map = {}  # cod_param -> (etiqueta, tipo_muestra)
        for r in etq_rows[1:]:
            if r[1]:
                etq_map[str(r[1]).strip().upper()] = (str(r[4] or ''), str(r[5] or ''))

        from laboratorio.models import CategoriaExamen as CatExamen
        cat_param, _ = CatExamen.objects.get_or_create(
            nombre='PARÁMETROS',
            defaults={'descripcion': 'Parámetros individuales de laboratorio'}
        )

        orden_por_examen = {}  # {estudio_id: contador}

        for idx, r in enumerate(data):
            if not r[1]:
                continue
            cod_param  = str(r[1]).strip()
            abrev      = str(r[2] or '').strip()
            desc       = str(r[3] or '').strip()
            depto      = str(r[5] or '').strip()
            tipo_mues  = str(r[6] or '').strip()
            metodo     = str(r[7] or '').strip()
            impr_met   = str(r[8] or '').strip().lower() != 'no imprimir'
            formula    = str(r[9] or '').strip()
            negritas   = _bool_excel(r[10])
            antibiog   = _bool_excel(r[11])
            tipo_res   = 'Numerico' if str(r[17] or '').strip() == 'Numerico' else 'Texto'
            res_opciones = str(r[20] or '').strip()
            decimales  = _safe_int(r[21], 2)
            indic      = str(r[23] or '').strip()
            notas      = str(r[24] or '').strip()
            tipo_ref   = str(r[26] or 'Rango numerico').strip()
            val_norm_txt = str(r[27] or '').strip()

            # Normalizar tipo_referencia a choices
            if 'texto' in tipo_ref.lower():
                tipo_ref_norm = 'Texto libre'
            elif 'rango' in tipo_ref.lower() or 'numeric' in tipo_ref.lower():
                tipo_ref_norm = 'Rango numerico'
            else:
                tipo_ref_norm = 'Sin referencia'

            etq_info = etq_map.get(cod_param.upper(), ('', ''))
            etiqueta_int = etq_info[0]
            if not tipo_mues and etq_info[1]:
                tipo_mues = etq_info[1]

            # Buscar el estudio contenedor usando la relación de composición
            # (se vincula correctamente en _vincular_examen_parametro)
            # Por ahora asociamos al estudio con mismo codigo/abreviatura o creamos estudio auxiliar
            estudio = (
                Estudio.objects.filter(abreviatura__iexact=abrev).first()
                or Estudio.objects.filter(abreviatura__iexact=cod_param).first()
                or Estudio.objects.filter(codigo__iexact=cod_param).first()
            )
            if not estudio:
                # Crear estudio auxiliar solo si el parámetro puede venderse directamente
                permite_venta = _bool_excel(r[12])
                if permite_venta:
                    estudio, _ = Estudio.objects.get_or_create(
                        codigo=cod_param,
                        defaults={
                            'nombre': desc,
                            'categoria': cat_param,
                            'abreviatura': abrev or cod_param,
                            'metodo': metodo or None,
                            'activo': True,
                            'permite_venta_directa': True,
                        }
                    )
                else:
                    # Parametro sin estudio padre: se vinculará en paso 5
                    # Guardar en registro especial para reconciliación posterior
                    continue

            orden = orden_por_examen.get(estudio.id, 0)
            orden_por_examen[estudio.id] = orden + 1

            param_campos = dict(
                abreviatura=_trunc(abrev, 30),
                codigo_interfaz=_trunc(cod_param, 50),
                departamento=_trunc(depto, 100),
                tipo_muestra=_trunc(tipo_mues, 100),
                imprimir_metodo=impr_met,
                formula=_trunc(formula, 500),
                imprimir_en_negritas=negritas,
                es_antibiograma=antibiog,
                tipo_resultado=tipo_res,
                tipo_referencia=tipo_ref_norm,
                resultado_opciones=_trunc(res_opciones, 500),
                decimales=decimales,
                indicaciones=indic or None,
                notas=notas or None,
                valor_normalidad_texto=val_norm_txt or None,
                etiqueta_interfaz=_trunc(etiqueta_int, 30),
                orden_impresion=orden,
                unidades=_trunc(str(r[15] or ''), 50),
            )
            # Eliminar campos que no existen en el modelo
            param_campos = {k: v for k, v in param_campos.items()
                            if hasattr(Parametro, k) and k not in ('objects', 'id')}

            param = (
                Parametro.objects.filter(codigo_interfaz=cod_param, estudio=estudio).first()
                or Parametro.objects.filter(nombre__iexact=desc, estudio=estudio).first()
            )

            if param:
                for k, v in param_campos.items():
                    setattr(param, k, v)
                param.nombre = desc
                if not self.dry_run:
                    param.save()
                stats['parametros_actualizados'] += 1
            else:
                param = Parametro(estudio=estudio, nombre=desc, **param_campos)
                if not self.dry_run:
                    param.save()
                stats['parametros_creados'] += 1

        self._log(f'   ✅ {stats["parametros_creados"]} creados | {stats["parametros_actualizados"]} actualizados')

    # ────────────────────────────────────────────────────────────────────────
    # PASO 5 — RANGOS DE REFERENCIA (Valores normalidad)
    # ────────────────────────────────────────────────────────────────────────

    def _importar_rangos_referencia(self, stats):
        from laboratorio.models import Parametro, RangoReferenciaParametro

        if not ARCHIVO_PARAMETROS.exists():
            return

        self._log('📊 Procesando rangos de referencia (329 rangos)...')
        rows = _leer_excel(ARCHIVO_PARAMETROS, hoja='Valores normalidad')
        data = [r for r in rows[1:] if any(v for v in r)]

        for r in data:
            if not r[1]:
                continue
            cod_param   = str(r[1]).strip()
            sexo_raw    = str(r[4] or '').strip()
            unidad_edad = str(r[5] or '').strip()
            edad_min    = _edad_a_anios(r[6], unidad_edad)
            edad_max    = _edad_a_anios(r[7], unidad_edad)
            ref_min     = _safe_decimal(r[8])
            ref_max     = _safe_decimal(r[9])
            sexo        = _sexo_rango(sexo_raw)

            # Buscar el parámetro correspondiente
            param = Parametro.objects.filter(codigo_interfaz=cod_param).first()
            if not param:
                param = Parametro.objects.filter(abreviatura__iexact=cod_param).first()
            if not param:
                continue

            # Garantizar que edad_max > edad_min
            if edad_max <= edad_min:
                edad_max = edad_min + decimal.Decimal('0.01')

            rango_defaults = dict(
                valor_minimo=ref_min,
                valor_maximo=ref_max,
                unidad=str(r[5] or '').split('(')[-1].replace(')', '').strip(),
                fuente='PRISLAB',
            )

            if not self.dry_run:
                rango, created = RangoReferenciaParametro.objects.update_or_create(
                    parametro=param,
                    sexo=sexo,
                    edad_min_anios=edad_min,
                    edad_max_anios=edad_max,
                    defaults=rango_defaults,
                )
                if created:
                    stats['rangos_creados'] += 1
                else:
                    stats['rangos_actualizados'] += 1
            else:
                stats['rangos_creados'] += 1

        self._log(f'   ✅ {stats["rangos_creados"]} rangos creados | {stats["rangos_actualizados"]} actualizados')

    # ────────────────────────────────────────────────────────────────────────
    # PASO 6 — VINCULAR EXAMEN → PARÁMETRO (Prueba del perfil)
    # ────────────────────────────────────────────────────────────────────────

    def _vincular_examen_parametro(self, stats):
        from laboratorio.models import Estudio, Parametro

        if not ARCHIVO_EXAMENES.exists():
            return

        self._log('🔗 Vinculando exámenes con sus parámetros...')
        rows = _leer_excel(ARCHIVO_EXAMENES, hoja='Prueba del perfil')
        # Fila 1: Encabezados superiores, Fila 2: headers reales
        data = [r for r in rows[2:] if any(v for v in r)]

        vinculos = 0
        for r in data:
            ex_cod    = str(r[0] or '').strip()
            param_cod = str(r[3] or '').strip()
            if not ex_cod or not param_cod:
                continue

            estudio = (
                Estudio.objects.filter(codigo=ex_cod).first()
                or Estudio.objects.filter(abreviatura__iexact=ex_cod).first()
            )
            if not estudio:
                continue

            param = (
                Parametro.objects.filter(codigo_interfaz=param_cod).first()
                or Parametro.objects.filter(abreviatura__iexact=param_cod).first()
            )
            if not param:
                continue

            # Re-asignar el parámetro al estudio correcto si no lo está
            if param.estudio_id != estudio.id:
                if not self.dry_run:
                    Parametro.objects.filter(pk=param.pk).update(estudio=estudio)
                vinculos += 1

        stats['relaciones_creadas'] += vinculos
        self._log(f'   ✅ {vinculos} vínculos examen→parámetro reconciliados')

    # ── Utilidades ────────────────────────────────────────────────────────────

    def _log(self, msg):
        if self.verbosity >= 1:
            self.stdout.write(msg)

    def _imprimir_resumen(self, stats):
        self.stdout.write('\n' + self.style.SUCCESS('=' * 55))
        self.stdout.write(self.style.SUCCESS('  IMPORTACIÓN COMPLETADA — RESUMEN'))
        self.stdout.write(self.style.SUCCESS('=' * 55))
        self.stdout.write(f"  Exámenes actualizados : {stats['examenes_actualizados']}")
        self.stdout.write(f"  Exámenes creados      : {stats['examenes_creados']}")
        self.stdout.write(f"  Paquetes actualizados : {stats['paquetes_actualizados']}")
        self.stdout.write(f"  Parámetros creados    : {stats['parametros_creados']}")
        self.stdout.write(f"  Parámetros actualizados: {stats['parametros_actualizados']}")
        self.stdout.write(f"  Relaciones vinculadas : {stats['relaciones_creadas']}")
        self.stdout.write(f"  Rangos creados        : {stats['rangos_creados']}")
        self.stdout.write(f"  Rangos actualizados   : {stats['rangos_actualizados']}")
        self.stdout.write(f"  Precios actualizados  : {stats['precios_actualizados']}")
        self.stdout.write(self.style.SUCCESS('=' * 55))


class DryRunInterrupt(Exception):
    """Señal para revertir la transacción en modo dry-run."""
    pass