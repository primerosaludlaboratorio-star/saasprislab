"""
Importar datos Legacy de DeveLab a PRISLAB V5.

Jerarquía:  Paquete  →  Perfil (Examen)  →  Parámetro  ←  Valores de Referencia

Lee los CSVs de datos_lims/:
 1. Parametros.csv          – catálogo maestro de parámetros (unidad base)
 2. Valores_normalidad.csv  – rangos de referencia (sexo / edad)
 3. Examenes.csv            – catálogo de exámenes / perfiles
 4. Examenes_Perfil.csv     – qué parámetros componen cada examen
 5. Paquetes.csv            – paquetes comerciales
 6. Paquetes_Perfil.csv     – qué perfiles/pruebas componen cada paquete

Uso:
    python manage.py importar_legacy
    python manage.py importar_legacy --limpiar   # limpia y reimporta
"""
import csv
import os
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


# ────────────────────────────────────────────────────────
# Utilidades
# ────────────────────────────────────────────────────────

def _c(val):
    """Limpia un valor CSV: quita espacios y 'nan'/vacío → ''."""
    if val is None:
        return ''
    s = str(val).strip()
    if s.lower() in ('nan', 'none', ''):
        return ''
    return s


def _sexo(val):
    s = _c(val).upper()
    if 'FEM' in s or s == 'F':
        return 'F'
    if 'MASC' in s or s == 'M':
        return 'M'
    return 'I'


def _dec(val):
    s = _c(val)
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _int(val):
    s = _c(val)
    if not s:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _read_csv(path):
    """Lee un CSV normal (1 fila de header) con auto-encoding."""
    for enc in ('utf-8-sig', 'latin-1', 'cp1252'):
        try:
            with open(path, encoding=enc, newline='') as f:
                return list(csv.DictReader(f))
        except (UnicodeDecodeError, UnicodeError):
            continue
    return []


def _read_double_header(path):
    """Lee un CSV con DOBLE fila de encabezado.  Devuelve listas de listas (raw rows)."""
    for enc in ('utf-8-sig', 'latin-1', 'cp1252'):
        try:
            with open(path, encoding=enc, newline='') as f:
                reader = csv.reader(f)
                next(reader, None)   # skip header row 1
                next(reader, None)   # skip header row 2
                return [row for row in reader if len(row) >= 4]
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    return []


class Command(BaseCommand):
    help = 'Importa datos Legacy de DeveLab (datos_lims/) a PRISLAB V5'

    def add_arguments(self, parser):
        parser.add_argument('--limpiar', action='store_true',
                            help='Limpiar Parámetros y Rangos antes de reimportar')

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        base = os.path.join(settings.BASE_DIR, 'datos_lims')
        if not os.path.isdir(base):
            self.stderr.write(f'No existe la carpeta {base}')
            return

        self.stdout.write(self.style.WARNING(f'Leyendo CSVs de {base}'))

        # ══════════════════════════════════════════════════════
        # LECTURA DE TODOS LOS CSVs EN MEMORIA
        # ══════════════════════════════════════════════════════
        rows_param = _read_csv(os.path.join(base, 'Parametros.csv'))
        rows_val   = _read_csv(os.path.join(base, 'Valores_normalidad.csv'))
        rows_exam  = _read_csv(os.path.join(base, 'Examenes.csv'))
        raw_exam_p = _read_double_header(os.path.join(base, 'Examenes_Perfil.csv'))
        rows_paq   = _read_csv(os.path.join(base, 'Paquetes.csv'))
        raw_paq_p  = _read_double_header(os.path.join(base, 'Paquetes_Perfil.csv'))

        self.stdout.write(f'  Parametros.csv:          {len(rows_param)} filas')
        self.stdout.write(f'  Valores_normalidad.csv:  {len(rows_val)} filas')
        self.stdout.write(f'  Examenes.csv:            {len(rows_exam)} filas')
        self.stdout.write(f'  Examenes_Perfil.csv:     {len(raw_exam_p)} filas')
        self.stdout.write(f'  Paquetes.csv:            {len(rows_paq)} filas')
        self.stdout.write(f'  Paquetes_Perfil.csv:     {len(raw_paq_p)} filas')

        # ══════════════════════════════════════════════════════
        # CONSTRUIR LOOKUPS EN MEMORIA
        # ══════════════════════════════════════════════════════

        # 1) param_by_code:  Codigo → dict (puede haber >1 con mismo Codigo, e.g. NEU)
        #    Usamos Id_parametro como desempate: guardamos TODOS indexados por Id
        param_by_id = {}     # Id_parametro → row dict
        param_by_code = {}   # Codigo → row dict  (último gana si hay dups)
        for r in rows_param:
            pid = _c(r.get('Id_parametro', ''))
            cod = _c(r.get('Codigo', ''))
            if pid:
                param_by_id[pid] = r
            if cod:
                # Si ya existe con mismo Codigo pero distinto Id, guardar ambos
                if cod not in param_by_code:
                    param_by_code[cod] = r
                # Si hay duplicados de Codigo, indexar el segundo por Id_parametro
                # pero param_by_code[cod] mantiene el primero

        # 2) rangos_by_id:  Id_parametro → [lista de rangos]
        rangos_by_id = {}
        for r in rows_val:
            pid = _c(r.get('Id_parametro', ''))
            if pid:
                rangos_by_id.setdefault(pid, []).append(r)

        # 3) exam_params:  codigo_examen → [lista de {param_codigo, param_desc}]  en ORDEN
        exam_params = {}
        for row in raw_exam_p:
            ec = _c(row[0])   # Codigo del examen
            pc = _c(row[3])   # Codigo del parámetro
            if ec and pc:
                exam_params.setdefault(ec, []).append(pc)

        # 4) paquete_componentes:  abreviatura_paquete → [{tipo, codigo}]
        paq_comps = {}
        for row in raw_paq_p:
            pa = _c(row[0])   # Abreviatura paquete
            tipo = _c(row[2]) if len(row) > 2 else ''  # "Prueba" o "Perfil"
            cc = _c(row[3])   # Codigo componente
            if pa and cc:
                paq_comps.setdefault(pa, []).append({'tipo': tipo, 'codigo': cc})

        # ══════════════════════════════════════════════════════
        with transaction.atomic():
            if options.get('limpiar'):
                self.stdout.write(self.style.WARNING('Limpiando datos previos...'))
                RangoReferencia.objects.all().delete()
                Parametro.objects.all().delete()
                self.stdout.write('  Parámetros y Rangos eliminados')

            # ──────────────────────────────────────────────
            # PASO 1: Secciones (departamentos)
            # ──────────────────────────────────────────────
            self.stdout.write(self.style.WARNING('\n=== PASO 1: Secciones ==='))
            deptos = set()
            for r in rows_param:
                d = _c(r.get('Departamento', ''))
                if d:
                    deptos.add(d.upper())
            secciones = {}
            for i, d in enumerate(sorted(deptos)):
                sec, _ = SeccionLaboratorio.objects.get_or_create(
                    nombre=d, defaults={'orden': i, 'activo': True}
                )
                secciones[d] = sec
            self.stdout.write(f'  {len(secciones)} secciones')

            # ──────────────────────────────────────────────
            # PASO 2: Exámenes → Estudio
            # ──────────────────────────────────────────────
            self.stdout.write(self.style.WARNING('\n=== PASO 2: Exámenes (Perfiles) ==='))
            estudios = {}   # codigo_csv → Estudio obj
            n_exam = 0
            for r in rows_exam:
                cod   = _c(r.get('Codigo', ''))
                abr   = _c(r.get('Abreviatura', ''))
                desc  = _c(r.get('Descripcion', ''))
                titulo = _c(r.get('Titulo', ''))
                metodo = _c(r.get('Metodo', ''))
                indic  = _c(r.get('Indicaciones', ''))
                notas  = _c(r.get('Notas', ''))
                codigo_final = abr or cod
                if not codigo_final:
                    continue

                # Determinar sección del examen a partir de su primer parámetro
                seccion_obj = None
                for pc in exam_params.get(cod, []):
                    pl = param_by_code.get(pc)
                    if pl:
                        dep = _c(pl.get('Departamento', '')).upper()
                        if dep in secciones:
                            seccion_obj = secciones[dep]
                            break

                est, _ = Estudio.objects.update_or_create(
                    codigo=codigo_final,
                    defaults={
                        'nombre': titulo or desc or codigo_final,
                        'abreviatura': abr or cod,
                        'seccion': seccion_obj,
                        'metodologia': metodo,
                        'indicaciones': indic,
                        'descripcion_interna': notas,
                        'es_perfil': True,
                        'activo': True,
                    }
                )
                estudios[cod] = est          # mapear por Codigo CSV (e.g., '45')
                estudios[codigo_final] = est  # también por abreviatura (e.g., 'CH')
                n_exam += 1
            self.stdout.write(f'  {n_exam} exámenes')

            # ──────────────────────────────────────────────
            # PASO 3: Parámetros + Rangos de Referencia
            # ──────────────────────────────────────────────
            self.stdout.write(self.style.WARNING('\n=== PASO 3: Parámetros y Rangos ==='))
            n_param = 0
            n_rango = 0
            seen_per_exam = {}  # track (estudio_id, abreviatura) to skip exact dups

            for exam_cod, param_codes in exam_params.items():
                estudio = estudios.get(exam_cod)
                if not estudio:
                    continue

                for orden_idx, param_cod in enumerate(param_codes):
                    pl = param_by_code.get(param_cod)
                    if not pl:
                        continue

                    id_param    = _c(pl.get('Id_parametro', ''))
                    descripcion = _c(pl.get('Descripcion', ''))
                    abreviatura = _c(pl.get('Abreviatura', ''))
                    unidades    = _c(pl.get('Unidades', ''))
                    metodo      = _c(pl.get('Metodo', ''))
                    tipo_res    = _c(pl.get('Tipo_resultado', 'Numerico')).upper()
                    formula     = _c(pl.get('Formula', ''))
                    decimales   = _int(pl.get('Decimales', '2')) or 2
                    resultado_default = _c(pl.get('Resultado_default', ''))
                    val_norm_txt = _c(pl.get('Valor de normalidad (texto libre)', ''))
                    impr_metodo = _c(pl.get('Imprimir_metodo_resultado', ''))

                    tipo_dato = 'NUMERICO' if 'NUM' in tipo_res else 'TEXTO'
                    nombre = descripcion or param_cod
                    abr_final = abreviatura or param_cod

                    # Skip exact duplicates (e.g. NEU appearing 2x in same exam)
                    dup_key = (estudio.id, abr_final)
                    if dup_key in seen_per_exam:
                        continue
                    seen_per_exam[dup_key] = True

                    parametro, created = Parametro.objects.update_or_create(
                        estudio=estudio,
                        abreviatura=abr_final,
                        defaults={
                            'nombre': nombre,
                            'unidad': unidades,
                            'tipo_dato': tipo_dato,
                            'orden_impresion': orden_idx,
                            'metodologia': metodo,
                            'formula_calculo': formula,
                            'valor_default': resultado_default,
                            'decimales_reporte': decimales,
                            'activo': True,
                        }
                    )
                    if created:
                        n_param += 1

                    # ── Crear Rangos de Referencia por sexo y edad ──
                    if id_param and id_param in rangos_by_id:
                        for rv in rangos_by_id[id_param]:
                            sexo = _sexo(rv.get('Sexo', ''))
                            unidad_edad = _c(rv.get('Unidad', '')).lower()
                            edad_min_raw = _int(rv.get('Edad_min'))
                            edad_max_raw = _int(rv.get('Edad_max'))
                            ref_min = _dec(rv.get('Ref_min'))
                            ref_max = _dec(rv.get('Ref_max'))

                            # Convertir a AÑOS (el modelo guarda años)
                            if 'dia' in unidad_edad or 'día' in unidad_edad:
                                edad_min_a = 0
                                edad_max_a = max(1, int((edad_max_raw or 365) / 365))
                            else:
                                edad_min_a = edad_min_raw
                                edad_max_a = edad_max_raw

                            RangoReferencia.objects.update_or_create(
                                parametro=parametro,
                                sexo=sexo,
                                edad_minima=edad_min_a,
                                edad_maxima=edad_max_a,
                                defaults={
                                    'valor_minimo': ref_min,
                                    'valor_maximo': ref_max,
                                    'activo': True,
                                }
                            )
                            n_rango += 1

                    elif val_norm_txt and tipo_dato == 'TEXTO':
                        RangoReferencia.objects.update_or_create(
                            parametro=parametro,
                            sexo='I',
                            edad_minima=0,
                            edad_maxima=120,
                            defaults={
                                'texto_referencia': val_norm_txt,
                                'activo': True,
                            }
                        )
                        n_rango += 1

            self.stdout.write(f'  {n_param} parámetros creados')
            self.stdout.write(f'  {n_rango} rangos de referencia')

            # ──────────────────────────────────────────────
            # PASO 4: Pruebas unitarias (venta directa)
            # ──────────────────────────────────────────────
            self.stdout.write(self.style.WARNING('\n=== PASO 4: Pruebas unitarias ==='))
            n_unit = 0
            for r in rows_param:
                if _c(r.get('Permite_venta_directa', '')).upper() != 'SI':
                    continue

                cod    = _c(r.get('Codigo', ''))
                abr    = _c(r.get('Abreviatura', ''))
                desc   = _c(r.get('Descripcion', ''))
                dep    = _c(r.get('Departamento', '')).upper()
                metodo = _c(r.get('Metodo', ''))
                pid    = _c(r.get('Id_parametro', ''))
                codigo_final = abr or cod
                if not codigo_final:
                    continue

                # No duplicar si ya existe como examen/perfil
                if Estudio.objects.filter(codigo=codigo_final).exists():
                    continue

                seccion_obj = secciones.get(dep)
                est, created = Estudio.objects.update_or_create(
                    codigo=codigo_final,
                    defaults={
                        'nombre': desc or codigo_final,
                        'abreviatura': abr or cod,
                        'seccion': seccion_obj,
                        'metodologia': metodo,
                        'es_perfil': False,
                        'activo': True,
                    }
                )
                if created:
                    n_unit += 1
                    estudios[codigo_final] = est

                    tipo_res = _c(r.get('Tipo_resultado', 'Numerico')).upper()
                    unidades = _c(r.get('Unidades', ''))
                    resultado_default = _c(r.get('Resultado_default', ''))
                    val_norm_txt = _c(r.get('Valor de normalidad (texto libre)', ''))
                    tipo_dato = 'NUMERICO' if 'NUM' in tipo_res else 'TEXTO'

                    parametro, _ = Parametro.objects.update_or_create(
                        estudio=est,
                        abreviatura=abr or cod,
                        defaults={
                            'nombre': desc or codigo_final,
                            'unidad': unidades,
                            'tipo_dato': tipo_dato,
                            'orden_impresion': 0,
                            'metodologia': metodo,
                            'valor_default': resultado_default,
                            'activo': True,
                        }
                    )

                    # Rangos de referencia
                    if pid and pid in rangos_by_id:
                        for rv in rangos_by_id[pid]:
                            sexo = _sexo(rv.get('Sexo', ''))
                            unidad_edad = _c(rv.get('Unidad', '')).lower()
                            edad_min_raw = _int(rv.get('Edad_min'))
                            edad_max_raw = _int(rv.get('Edad_max'))
                            ref_min = _dec(rv.get('Ref_min'))
                            ref_max = _dec(rv.get('Ref_max'))
                            if 'dia' in unidad_edad or 'día' in unidad_edad:
                                edad_min_a = 0
                                edad_max_a = max(1, int((edad_max_raw or 365) / 365))
                            else:
                                edad_min_a = edad_min_raw
                                edad_max_a = edad_max_raw
                            RangoReferencia.objects.update_or_create(
                                parametro=parametro,
                                sexo=sexo,
                                edad_minima=edad_min_a,
                                edad_maxima=edad_max_a,
                                defaults={
                                    'valor_minimo': ref_min,
                                    'valor_maximo': ref_max,
                                    'activo': True,
                                }
                            )
                    elif val_norm_txt:
                        RangoReferencia.objects.update_or_create(
                            parametro=parametro,
                            sexo='I',
                            edad_minima=0,
                            edad_maxima=120,
                            defaults={
                                'texto_referencia': val_norm_txt,
                                'activo': True,
                            }
                        )

            self.stdout.write(f'  {n_unit} pruebas unitarias')

            # ──────────────────────────────────────────────
            # PASO 5: Paquetes
            # ──────────────────────────────────────────────
            self.stdout.write(self.style.WARNING('\n=== PASO 5: Paquetes ==='))
            n_paq = 0
            for r in rows_paq:
                abr  = _c(r.get('Abreviatura', ''))
                desc = _c(r.get('Descripcion', ''))
                indic = _c(r.get('Indicaciones', ''))
                if not abr:
                    continue
                est, created = Estudio.objects.update_or_create(
                    codigo=abr,
                    defaults={
                        'nombre': desc or abr,
                        'abreviatura': abr,
                        'indicaciones': indic,
                        'es_perfil': True,
                        'activo': True,
                    }
                )
                estudios[abr] = est
                if created:
                    n_paq += 1
            self.stdout.write(f'  {n_paq} paquetes')

            # ── Vincular paquetes con sus componentes ──
            n_link = 0
            for paq_abr, comps in paq_comps.items():
                paquete = estudios.get(paq_abr)
                if not paquete:
                    continue
                for comp in comps:
                    comp_est = estudios.get(comp['codigo'])
                    if comp_est and paquete.id != comp_est.id:
                        paquete.componentes.add(comp_est)
                        n_link += 1
            self.stdout.write(f'  {n_link} vínculos paquete -> componente')

        # ── Reporte final ──
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('IMPORTACIÓN LEGACY COMPLETADA'))
        self.stdout.write(self.style.SUCCESS(f'  Secciones:       {len(secciones)}'))
        self.stdout.write(self.style.SUCCESS(f'  Exámenes:        {n_exam}'))
        self.stdout.write(self.style.SUCCESS(f'  Parámetros:      {n_param}'))
        self.stdout.write(self.style.SUCCESS(f'  Rangos Ref:      {n_rango}'))
        self.stdout.write(self.style.SUCCESS(f'  Pruebas Unit.:   {n_unit}'))
        self.stdout.write(self.style.SUCCESS(f'  Paquetes:        {n_paq}'))
        self.stdout.write(self.style.SUCCESS(f'  Vínculos Paq:    {n_link}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
