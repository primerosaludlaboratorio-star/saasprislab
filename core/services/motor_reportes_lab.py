"""
PRISLAB V5 - Motor de Reportes Institucionales V1.0
====================================================
Genera PDFs de resultados de laboratorio usando portada_institucional.pdf
como capa de fondo (underlay), replicando el formato oficial de
Primero Salud Laboratorio.

Arquitectura: PDF Background (portada) + ReportLab Overlay (datos)
Seguridad: QR de validacion unico por reporte
Multipagina: Desborde automatico con mismo membrete
Persistencia: GCS Bucket (media/resultados_pdf/)
"""

import logging
import os
from datetime import date, datetime
from django.utils import timezone
from decimal import Decimal
from io import BytesIO

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.models import (
    DetalleOrden,
    OrdenDeServicio,
    ResultadoParametro,
)
from core.utils.candado_financiero import (
    ReportePdfSaldoPendienteError,
    calcular_saldo,
    tiene_saldo_pendiente,
)

logger = logging.getLogger(__name__)


def _exigir_cero_saldo_antes_de_generar_pdf(orden) -> None:
    """Candado financiero intrínseco: no se genera PDF oficial con saldo pendiente."""
    if tiene_saldo_pendiente(orden):
        raise ReportePdfSaldoPendienteError(calcular_saldo(orden))

# ======================================================================
# COORDENADAS MAPEADAS DEL PDF DE EJEMPLO (ANSAY19082004)
# Tamaño carta: 612 x 792 pts (21.59 x 27.94 cm)
# ======================================================================
PAGE_W, PAGE_H = letter  # 612, 792

# Margenes que respetan el membrete (logos, firma QFB Gisel)
MARGIN_TOP = 4.8 * cm      # Debajo del logo superior
MARGIN_BOTTOM = 3.2 * cm   # Arriba de la franja de la firma
MARGIN_LEFT = 1.5 * cm
MARGIN_RIGHT = 1.5 * cm

# Ancho util
CONTENT_W = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT

# Colores institucionales (basados en el PDF de ejemplo)
COLOR_HEADER_BG = colors.HexColor('#003366')    # Azul oscuro institucional
COLOR_HEADER_TEXT = colors.white
COLOR_SECTION_BG = colors.HexColor('#e8f0fe')   # Azul claro para secciones
COLOR_SECTION_TEXT = colors.HexColor('#003366')
COLOR_GRID = colors.HexColor('#cccccc')
COLOR_ALTO = colors.HexColor('#dc3545')
COLOR_BAJO = colors.HexColor('#0d6efd')
COLOR_NORMAL = colors.HexColor('#198754')


def _get_portada_path():
    """Obtiene la ruta al PDF de portada institucional."""
    # Buscar en staticfiles recolectados (produccion)
    collected = os.path.join(settings.BASE_DIR, 'staticfiles', 'pdf', 'portada_institucional.pdf')
    if os.path.exists(collected):
        return collected
    # Buscar en static/ (desarrollo)
    dev = os.path.join(settings.BASE_DIR, 'static', 'pdf', 'portada_institucional.pdf')
    if os.path.exists(dev):
        return dev
    return None


def _calcular_edad(fecha_nacimiento):
    """Calcula la edad legible a partir de fecha de nacimiento."""
    if not fecha_nacimiento:
        return 'N/D'
    hoy = date.today()
    dias = (hoy - fecha_nacimiento).days
    if dias < 30:
        return f"{dias} dias"
    elif dias < 365:
        return f"{int(dias / 30.44)} meses"
    else:
        anios = int(dias / 365.25)
        return f"{anios} anios"


def _calcular_edad_anios(fecha_nacimiento):
    """Retorna la edad en anios como float."""
    if not fecha_nacimiento:
        return 0
    return (date.today() - fecha_nacimiento).days / 365.25


def _safe_str(val, default='-'):
    """
    Convierte a string seguro para ReportLab (maneja latin-1).
    Limpia emojis, caracteres Unicode exoticos y normaliza texto
    para evitar errores de codificacion en la generacion de PDF.
    """
    import unicodedata
    import re

    if val is None:
        return default
    s = str(val)

    # Paso 1: Normalizar Unicode (NFC - Canonical Decomposition + Composition)
    s = unicodedata.normalize('NFC', s)

    # Paso 2: Reemplazar caracteres conocidos problematicos
    replacements = {
        '\u2264': '<=',   # ≤
        '\u2265': '>=',   # ≥
        '\u00b1': '+/-',  # ±
        '\u00b5': 'u',    # µ → u (micro)
        '\u00b0': 'o',    # ° → o (grado)
        '\u2019': "'",    # '
        '\u201c': '"',    # "
        '\u201d': '"',    # "
        '\u2018': "'",    # '
        '\u2013': '-',    # –
        '\u2014': '--',   # —
        '\u2026': '...',  # …
        '\u00a0': ' ',    # non-breaking space
        '\u200b': '',     # zero-width space
        '\u200e': '',     # left-to-right mark
        '\u200f': '',     # right-to-left mark
        '\ufeff': '',     # BOM
    }
    for old, new in replacements.items():
        s = s.replace(old, new)

    # Paso 3: Eliminar emojis y simbolos Unicode exoticos (categorias So, Sk, Cn)
    # Mantener letras, numeros, puntuacion, espacios y simbolos matematicos comunes
    cleaned = []
    for ch in s:
        cat = unicodedata.category(ch)
        # Permitir: Letras (L*), Numeros (N*), Puntuacion (P*), Separadores (Z*),
        # Simbolos matematicos (Sm), Simbolos moneda (Sc), Marcas (M*)
        if cat[0] in ('L', 'N', 'P', 'Z', 'M') or cat in ('Sm', 'Sc'):
            cleaned.append(ch)
        elif cat == 'So':
            # Symbol Other (emojis, dingbats, etc) → eliminar
            pass
        elif cat == 'Cc' and ch in ('\n', '\r', '\t'):
            # Permitir saltos de linea y tabs
            cleaned.append(ch)
        elif cat == 'Cc':
            # Otros caracteres de control → eliminar
            pass
        else:
            cleaned.append(ch)
    s = ''.join(cleaned)

    # Paso 4: Intentar codificar a latin-1 como prueba final
    try:
        s.encode('latin-1')
    except UnicodeEncodeError:
        # Si falla, forzar ASCII con reemplazo
        s = s.encode('ascii', 'replace').decode('ascii')

    return s or default


def _generar_qr(url, size=2.5 * cm):
    """
    Genera imagen QR optimizada como objeto ReportLab.
    R107: Optimizacion - box_size reducido, PNG comprimido para PDF ligero.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,  # L = menor tamaño
        box_size=6,  # Reducido de 8 a 6 (menor peso)
        border=1,    # Reducido de 2 a 1 (menor borde)
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#003366", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    return RLImage(buf, width=size, height=size)


# ======================================================================
# ESTILOS
# ======================================================================
def _get_styles():
    """Retorna estilos personalizados para el reporte."""
    base = getSampleStyleSheet()

    return {
        'label': ParagraphStyle(
            'label', parent=base['Normal'],
            fontSize=7.5, textColor=colors.HexColor('#666666'),
            leading=10,
        ),
        'value': ParagraphStyle(
            'value', parent=base['Normal'],
            fontSize=8.5, fontName='Helvetica-Bold',
            leading=11,
        ),
        'value_large': ParagraphStyle(
            'value_large', parent=base['Normal'],
            fontSize=9.5, fontName='Helvetica-Bold',
            leading=12,
        ),
        'section': ParagraphStyle(
            'section', parent=base['Normal'],
            fontSize=9, fontName='Helvetica-Bold',
            textColor=COLOR_SECTION_TEXT,
            leading=12,
        ),
        'cell': ParagraphStyle(
            'cell', parent=base['Normal'],
            fontSize=8, leading=10,
        ),
        'cell_bold': ParagraphStyle(
            'cell_bold', parent=base['Normal'],
            fontSize=8, fontName='Helvetica-Bold',
            leading=10,
        ),
        'cell_small': ParagraphStyle(
            'cell_small', parent=base['Normal'],
            fontSize=7, leading=9, textColor=colors.HexColor('#555555'),
        ),
        'footer': ParagraphStyle(
            'footer', parent=base['Normal'],
            fontSize=7, alignment=TA_CENTER,
            textColor=colors.HexColor('#888888'),
        ),
        'metodo': ParagraphStyle(
            'metodo', parent=base['Normal'],
            fontSize=7, textColor=colors.HexColor('#666666'),
            leftIndent=8, leading=9,
        ),
    }


# ======================================================================
# BUILDER DE ELEMENTOS (OVERLAY)
# ======================================================================
def _orden_paciente_display(orden):
    """Nombre, edad y sexo para reportes: snapshot al momento de la orden (integridad forense) o actual."""
    paciente = orden.paciente
    nombre = getattr(orden, 'paciente_nombre_snapshot', None) or (paciente.nombre_completo if paciente else '')
    edad = getattr(orden, 'paciente_edad_snapshot', None)
    if edad is None and paciente:
        edad = _calcular_edad_anios(paciente.fecha_nacimiento) if getattr(paciente, 'fecha_nacimiento', None) else None
    sexo = getattr(orden, 'paciente_sexo_snapshot', None) or (getattr(paciente, 'sexo', '') if paciente else '')
    return nombre, edad, sexo


def _build_patient_header(orden, styles):
    """Construye la tabla de datos del paciente (formato DeveLab)."""
    paciente = orden.paciente
    nombre_display, edad_snapshot, sexo_snapshot = _orden_paciente_display(orden)
    if edad_snapshot is not None:
        edad = f'{edad_snapshot} años'
    else:
        edad = _calcular_edad(paciente.fecha_nacimiento) if paciente and getattr(paciente, 'fecha_nacimiento', None) else 'N/D'
    sexo = 'F' if sexo_snapshot == 'F' else 'M' if sexo_snapshot == 'M' else sexo_snapshot or 'N/D'
    medico_nombre = ''
    if orden.medico_referente:
        medico_nombre = _safe_str(orden.medico_referente.nombre_completo)
    
    fecha_display = orden.fecha_creacion.strftime('%d/%m/%Y') if orden.fecha_creacion else ''
    folio = orden.folio_orden or f'ORD-{orden.id}'
    origen = orden.get_origen_orden_display() if hasattr(orden, 'get_origen_orden_display') else ''
    
    # ID del paciente (código tipo DeveLab)
    pac_id = ''
    if paciente:
        if hasattr(paciente, 'uuid') and paciente.uuid:
            pac_id = str(paciente.uuid)[:14].upper()
        else:
            pac_id = str(paciente.id)
    
    # Formato DeveLab: Paciente, Registro, Medico en izquierda | Id, Sexo, Edad, Fecha en derecha
    lbl = ParagraphStyle('lbl_dl', fontSize=7, fontName='Helvetica', textColor=colors.HexColor('#666666'))
    val = ParagraphStyle('val_dl', fontSize=8, fontName='Helvetica-Bold', textColor=colors.HexColor('#222222'))
    val_lg = ParagraphStyle('val_lg_dl', fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor('#111111'))
    
    data = [
        [
            Paragraph('Paciente:', lbl),
            Paragraph(f"<b>{_safe_str(nombre_display or (paciente.nombre_completo if paciente else '')).upper()}</b>", val_lg),
            Paragraph('Id:', lbl),
            Paragraph(f'<b>{pac_id}</b>', val),
        ],
        [
            Paragraph('Registro:', lbl),
            Paragraph(f'{folio}', val),
            Paragraph('Sexo:', lbl),
            Paragraph(f'<b>{sexo}</b>', val),
        ],
        [
            Paragraph('Medico:', lbl),
            Paragraph(f'{medico_nombre or "A QUIEN CORRESPONDA"}', val),
            Paragraph('Edad:', lbl),
            Paragraph(f'<b>{edad}</b>', val),
        ],
        [
            Paragraph('Fecha:', lbl),
            Paragraph(f'<b>{fecha_display}</b>', val),
            Paragraph('Origen:', lbl),
            Paragraph(f'{_safe_str(origen, "PUBLICO EN GENERAL")}', val),
        ],
    ]
    
    t = Table(data, colWidths=[2.2 * cm, 6.8 * cm, 2.0 * cm, 5.5 * cm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, COLOR_GRID),
    ]))
    return t


def _analitos_para_pdf_detalle(detalle):
    """Analitos LIMS a listar para una línea de orden (analito, perfil o paquete)."""
    if getattr(detalle, 'analito_id', None):
        return [detalle.analito]
    if getattr(detalle, 'perfil_lims_id', None):
        return list(detalle.perfil_lims.analitos.all().order_by('departamento', 'nombre'))
    if getattr(detalle, 'paquete_lims_id', None):
        return list(detalle.paquete_lims.get_todos_analitos().order_by('departamento', 'nombre'))
    return []


def _valor_referencia_analito_pdf(analito, edad_anios, sexo):
    from django.db.models import Q
    from lims.models import ValorReferenciaAnalito

    qs = ValorReferenciaAnalito.objects.filter(analito=analito)
    sx = (sexo or '')[:1].upper() if sexo else ''
    if sx in ('M', 'F'):
        qs = qs.filter(Q(sexo=sx) | Q(sexo='I'))
    else:
        qs = qs.filter(sexo='I')
    if edad_anios is None:
        return None
    try:
        ea = int(float(edad_anios))
        if ea < 1:
            ea = 1
    except (TypeError, ValueError):
        return None
    return (
        qs.filter(
            unidad_edad='ANOS',
            edad_minima__lte=ea,
            edad_maxima__gte=ea,
        )
        .order_by('edad_minima')
        .first()
    )


def _build_results_section(detalle, orden, styles):
    """Sección de resultados por línea de orden — catálogo LIMS v7.5 (Analito / Perfil / Paquete)."""
    from core.lims_cart import detalle_orden_etiqueta

    elements = []
    line_title = _safe_str(detalle_orden_etiqueta(detalle)).upper()
    analitos = _analitos_para_pdf_detalle(detalle)

    elements.append(Spacer(1, 3 * mm))
    cat_data = [[Paragraph(f'<b>{line_title}</b>', styles['section'])]]
    cat_table = Table(cat_data, colWidths=[CONTENT_W])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_SECTION_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(cat_table)

    header_data = [
        Paragraph('<b>Examen</b>', styles['cell_bold']),
        Paragraph('<b>Resultado</b>', styles['cell_bold']),
        Paragraph('<b>Unidades</b>', styles['cell_bold']),
        Paragraph('<b>Valores de Referencia</b>', styles['cell_bold']),
    ]
    col_widths = [5.5 * cm, 3.5 * cm, 2.5 * cm, 5.0 * cm]
    table_data = [header_data]

    _, edad_snapshot, sexo_snapshot = _orden_paciente_display(orden)
    paciente_orden = orden.paciente
    edad_anios = edad_snapshot
    if edad_anios is None and paciente_orden and getattr(paciente_orden, 'fecha_nacimiento', None):
        edad_anios = _calcular_edad_anios(paciente_orden.fecha_nacimiento)
    sexo = sexo_snapshot or (getattr(paciente_orden, 'sexo', None) if paciente_orden else None) or 'I'

    _prev_results = {}
    try:
        _aid = [a.id for a in analitos]
        if _aid and paciente_orden:
            _previos = (
                ResultadoParametro.objects.filter(
                    orden__paciente=paciente_orden,
                    analito_id__in=_aid,
                )
                .exclude(orden=orden)
                .exclude(valor='')
                .exclude(valor='Pendiente')
                .exclude(valor__isnull=True)
                .select_related('orden')
                .order_by('analito_id', '-orden__fecha_creacion')
            )
            for _r in _previos:
                if _r.analito_id not in _prev_results:
                    _prev_results[_r.analito_id] = _r
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _build_results_section (motor_reportes_lab.py)")
        pass

    metodo_info = None

    if not analitos:
        if detalle.resultado:
            table_data.append([
                Paragraph(line_title, styles['cell']),
                Paragraph(_safe_str(detalle.resultado), styles['cell']),
                Paragraph('', styles['cell']),
                Paragraph('', styles['cell_small']),
            ])
    else:
        for analito in analitos:
            valor = 'Pendiente'
            rango_texto = '-'
            fuera_rango = False

            try:
                resultado = ResultadoParametro.objects.get(orden=orden, analito=analito)
                valor = _safe_str(resultado.valor, 'Pendiente')
            except ResultadoParametro.DoesNotExist:
                if len(analitos) == 1 and detalle.resultado:
                    valor = _safe_str(detalle.resultado, 'Pendiente')

            rango = _valor_referencia_analito_pdf(analito, edad_anios, sexo)
            if rango:
                if rango.ref_minimo is not None and rango.ref_maximo is not None:
                    rango_texto = f'{rango.ref_minimo} - {rango.ref_maximo}'
                    try:
                        val_num = float(str(valor).replace(',', '.'))
                        if val_num < float(rango.ref_minimo):
                            fuera_rango = True
                        elif val_num > float(rango.ref_maximo):
                            fuera_rango = True
                    except (ValueError, TypeError):
                        pass
                elif (rango.texto_referencia or '').strip():
                    rango_texto = _safe_str(rango.texto_referencia)

            if (analito.metodologia or '').strip():
                metodo_info = _safe_str(analito.metodologia)

            valor_p = (
                Paragraph(f'<b>* {valor}</b>', styles['cell_bold'])
                if fuera_rango
                else Paragraph(valor, styles['cell'])
            )
            table_data.append([
                Paragraph(_safe_str(analito.nombre), styles['cell']),
                valor_p,
                Paragraph(_safe_str(analito.unidades, ''), styles['cell']),
                Paragraph(_safe_str(rango_texto), styles['cell_small']),
            ])

            _prev = _prev_results.get(analito.id)
            if _prev:
                try:
                    _fecha_prev = (
                        _prev.orden.fecha_creacion.strftime('%d/%m/%Y')
                        if _prev.orden.fecha_creacion
                        else ''
                    )
                    _nota_hist = (
                        f'<font size="6" color="#888888"><i>'
                        f'Resultado anterior: {_safe_str(_prev.valor)} '
                        f'el d\u00eda {_fecha_prev}'
                        f'</i></font>'
                    )
                    table_data.append([
                        Paragraph('', styles['cell']),
                        Paragraph(_nota_hist, styles['cell_small']),
                        Paragraph('', styles['cell']),
                        Paragraph('', styles['cell']),
                    ])
                except Exception:
                    logging.getLogger(__name__).exception("Error inesperado en _build_results_section (motor_reportes_lab.py)")
                    pass

    t = Table(table_data, colWidths=col_widths)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_HEADER_TEXT),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('GRID', (0, 0), (-1, -1), 0.3, COLOR_GRID),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')]),
    ]
    t.setStyle(TableStyle(style_cmds))
    elements.append(t)

    if metodo_info:
        elements.append(Paragraph(
            f'<font size="6.5" color="#555555">Metodo: {metodo_info}</font>',
            ParagraphStyle('metodo_dl', fontSize=6.5, leading=8,
                           spaceBefore=2, spaceAfter=0, leftIndent=2)
        ))
    elements.append(Paragraph(
        '<font size="6" color="#888888">VALORES DE REFERENCIA DE ACUERDO A EDAD, SEXO Y NIVEL DEL MAR.</font>',
        ParagraphStyle('ref_note', fontSize=6, leading=7,
                       spaceBefore=2, spaceAfter=1, leftIndent=2)
    ))

    return elements


def _build_historical_reference(orden, styles):
    """
    Referencia histórica: resultados previos del mismo paciente para los mismos analitos LIMS.
    """
    elements = []
    paciente = orden.paciente

    ordenes_previas = OrdenDeServicio.objects.filter(
        paciente=paciente,
    ).exclude(id=orden.id).order_by('-fecha_creacion')[:5]

    if not ordenes_previas.exists():
        return elements

    analitos_actuales = set()
    resultados_actuales = ResultadoParametro.objects.filter(orden=orden).select_related('analito')
    for r in resultados_actuales:
        if r.analito_id:
            analitos_actuales.add(r.analito_id)

    if not analitos_actuales:
        return elements

    historicos = ResultadoParametro.objects.filter(
        orden__in=ordenes_previas,
        analito_id__in=analitos_actuales,
        valor__isnull=False,
    ).exclude(valor='').exclude(valor='Pendiente').select_related(
        'analito', 'orden'
    ).order_by('analito__nombre', '-orden__fecha_creacion')

    if not historicos.exists():
        return elements

    from collections import defaultdict
    por_analito = defaultdict(list)
    for h in historicos:
        if len(por_analito[h.analito_id]) < 3:
            por_analito[h.analito_id].append(h)

    if not por_analito:
        return elements

    elements.append(Spacer(1, 6 * mm))
    title_data = [[Paragraph(
        '<b>REFERENCIA HISTORICA</b>',
        ParagraphStyle('hist_title', fontSize=9, fontName='Helvetica-Bold',
                       textColor=colors.white)
    )]]
    title_table = Table(title_data, colWidths=[CONTENT_W])
    title_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#6c757d')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(title_table)

    hist_header = [
        Paragraph('<b>Analito</b>', styles['cell_bold']),
        Paragraph('<b>Resultado Previo</b>', styles['cell_bold']),
        Paragraph('<b>Fecha</b>', styles['cell_bold']),
        Paragraph('<b>Unidades</b>', styles['cell_bold']),
    ]
    col_widths = [5.5 * cm, 4.0 * cm, 3.5 * cm, 3.5 * cm]
    table_data = [hist_header]

    for _aid, results in por_analito.items():
        for r in results:
            fecha_str = r.orden.fecha_creacion.strftime('%d/%m/%Y') if r.orden.fecha_creacion else ''
            an = r.analito
            table_data.append([
                Paragraph(_safe_str(an.nombre if an else ''), styles['cell']),
                Paragraph(f'<font color="#6c757d">{_safe_str(r.valor)}</font>', styles['cell']),
                Paragraph(f'<font color="#888888">{fecha_str}</font>', styles['cell_small']),
                Paragraph(_safe_str(an.unidades if an else '', ''), styles['cell_small']),
            ])

    if len(table_data) <= 1:
        return elements  # Solo header, sin datos

    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#495057')),
        ('FONTSIZE', (0, 0), (-1, 0), 7.5),
        ('GRID', (0, 0), (-1, -1), 0.2, colors.HexColor('#dee2e6')),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(t)

    elements.append(Paragraph(
        '<font size="6" color="#999999"><i>Nota: Los valores historicos son de consultas '
        'anteriores del mismo paciente y se presentan como referencia comparativa.</i></font>',
        styles['cell_small']
    ))

    return elements


def _build_footer_row(hoja_num, total_hojas, fecha_impresion, styles):
    """Linea de pie: Fecha impresion + Hoja X/Y."""
    data = [[
        Paragraph(f'Fecha: {fecha_impresion}', styles['footer']),
        Paragraph(f'Hoja: {hoja_num}/{total_hojas}', styles['footer']),
    ]]
    t = Table(data, colWidths=[CONTENT_W / 2, CONTENT_W / 2])
    t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    return t


# ======================================================================
# HELPER: RESPONSABLE SANITARIA COFEPRIS
# ======================================================================

def _obtener_responsable_sanitaria(orden=None) -> dict:
    """
    Retorna los datos del Responsable Sanitario para el pie de firma del PDF.
    Cascada de búsqueda (sin nombres hardcodeados):
      1. Campos responsable_sanitaria_* del modelo Empresa (fuente primaria)
      2. DocumentoCapacitacion más reciente con validado_por_nombre
      3. Variable de entorno PRISLAB_RESPONSABLE_NOMBRE (fallback de despliegue)
      4. Cadena vacía — el PDF mostrará "Responsable Sanitario"
    """
    import os
    empty = {"nombre": "", "cedula": "", "cofepris": ""}

    try:
        empresa = getattr(orden, 'empresa', None) if orden else None
        if empresa:
            # Fuente 1: campos directos del modelo Empresa
            if empresa.responsable_sanitaria_nombre:
                return {
                    "nombre":   empresa.responsable_sanitaria_nombre,
                    "cedula":   empresa.responsable_sanitaria_cedula or "",
                    "cofepris": empresa.responsable_sanitaria_cofepris or "",
                }
            # Fuente 2: DocumentoCapacitacion más reciente
            from core.models import DocumentoCapacitacion
            doc = DocumentoCapacitacion.objects.filter(
                empresa=empresa,
                activo=True,
                validado_por_nombre__isnull=False,
            ).exclude(validado_por_nombre='').order_by('-fecha_actualizacion').first()
            if doc and doc.validado_por_nombre:
                return {
                    "nombre":   doc.validado_por_nombre,
                    "cedula":   getattr(doc, 'cedula_validador', '') or "",
                    "cofepris": "",
                }
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _obtener_responsable_sanitaria (motor_reportes_lab.py)")
        pass

    # Fuente 3: variable de entorno (configurable en producción / .env)
    env_nombre = os.environ.get('PRISLAB_RESPONSABLE_NOMBRE', '').strip()
    if env_nombre:
        return {
            "nombre":   env_nombre,
            "cedula":   os.environ.get('PRISLAB_RESPONSABLE_CEDULA', ''),
            "cofepris": os.environ.get('PRISLAB_RESPONSABLE_COFEPRIS', ''),
        }

    return empty


# ======================================================================
# GENERADOR PRINCIPAL
# ======================================================================
def generar_reporte_pdf(orden, request=None):
    """
    Genera el PDF de resultados con portada institucional como fondo.
    
    Args:
        orden: OrdenDeServicio instance
        request: HttpRequest (para generar URL del QR)
    
    Returns:
        bytes: Contenido del PDF generado
    """
    _exigir_cero_saldo_antes_de_generar_pdf(orden)
    styles = _get_styles()
    portada_path = _get_portada_path()
    
    # ==========================================
    # 1. CONSTRUIR OVERLAY CON REPORTLAB
    # ==========================================
    overlay_buffer = BytesIO()
    doc = SimpleDocTemplate(
        overlay_buffer,
        pagesize=letter,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )
    
    elements = []
    
    # --- Header: Datos del paciente ---
    elements.append(_build_patient_header(orden, styles))
    elements.append(Spacer(1, 4 * mm))
    
    # --- Titulo de tabla ---
    header_bar = [[
        Paragraph('<b>Examen</b>', ParagraphStyle('hdr', fontSize=8, fontName='Helvetica-Bold', textColor=colors.white)),
        Paragraph('<b>Resultado</b>', ParagraphStyle('hdr', fontSize=8, fontName='Helvetica-Bold', textColor=colors.white)),
        Paragraph('<b>Unidades</b>', ParagraphStyle('hdr', fontSize=8, fontName='Helvetica-Bold', textColor=colors.white)),
        Paragraph('<b>Valores de Referencia</b>', ParagraphStyle('hdr', fontSize=8, fontName='Helvetica-Bold', textColor=colors.white)),
    ]]
    
    # --- Resultados por línea de orden (LIMS v7.5) ---
    detalles = (
        DetalleOrden.objects.filter(orden=orden)
        .select_related('analito', 'perfil_lims', 'paquete_lims')
        .order_by('id')
    )
    
    for detalle in detalles:
        section_elements = _build_results_section(detalle, orden, styles)
        elements.extend(section_elements)
        elements.append(Spacer(1, 3 * mm))
    
    # --- Referencia Historica (resultados previos del mismo paciente) ---
    try:
        hist_elements = _build_historical_reference(orden, styles)
        if hist_elements:
            elements.extend(hist_elements)
            elements.append(Spacer(1, 3 * mm))
    except Exception as e:
        logger.warning(f"Error generando referencia historica: {e}")

    # --- Resumen de Bienestar IA (R107) ---
    try:
        from core.services.interpretacion_ia import generar_resumen_bienestar
        resumen_ia = generar_resumen_bienestar(orden)
        if resumen_ia:
            elements.append(Spacer(1, 4 * mm))
            # Titulo
            ia_title = [[Paragraph(
                '<b>RESUMEN DE BIENESTAR</b>',
                ParagraphStyle('ia_title', fontSize=9, fontName='Helvetica-Bold',
                               textColor=colors.white)
            )]]
            ia_title_t = Table(ia_title, colWidths=[CONTENT_W])
            ia_title_t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#198754')),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(ia_title_t)
            # Contenido
            resumen_safe = _safe_str(resumen_ia)
            ia_body = [[Paragraph(
                f'<font size="7.5" color="#333333">{resumen_safe}</font>',
                ParagraphStyle('ia_body', fontSize=7.5, leading=10,
                               spaceBefore=2, spaceAfter=2)
            )]]
            ia_body_t = Table(ia_body, colWidths=[CONTENT_W])
            ia_body_t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0fff4')),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('BOX', (0, 0), (-1, -1), 0.3, colors.HexColor('#198754')),
            ]))
            elements.append(ia_body_t)
            # Disclaimer
            elements.append(Paragraph(
                '<font size="5.5" color="#999"><i>Este resumen es generado por '
                'inteligencia artificial con fines informativos. '
                'No sustituye la consulta medica profesional.</i></font>',
                ParagraphStyle('ia_disc', fontSize=5.5, alignment=TA_CENTER,
                               spaceBefore=2)
            ))
    except Exception as e:
        logger.warning(f"Error generando resumen IA: {e}")

    # --- Firma digital del validador ---
    try:
        from core.models import FirmaDigital
        # Buscar el último validador de la orden
        ultimo_detalle_validado = DetalleOrden.objects.filter(
            orden=orden, validado_por__isnull=False
        ).select_related('validado_por').order_by('-fecha_validacion').first()

        if ultimo_detalle_validado and ultimo_detalle_validado.validado_por:
            validador = ultimo_detalle_validado.validado_por
            firma_obj = FirmaDigital.objects.filter(medico=validador, activa=True).first()

            nombre_validador = validador.get_full_name() or validador.username
            cedula_validador = ''
            if firma_obj:
                cedula_validador = firma_obj.cedula_profesional or ''

            elements.append(Spacer(1, 6 * mm))
            firma_elements = []

            # Intentar cargar imagen de firma
            firma_img = None
            if firma_obj and firma_obj.imagen_firma:
                try:
                    img_path = firma_obj.imagen_firma.path
                    firma_img = RLImage(img_path, width=4 * cm, height=1.5 * cm)
                except Exception:
                    logging.getLogger(__name__).exception("Error inesperado en generar_reporte_pdf (motor_reportes_lab.py)")
                    try:
                        firma_img = RLImage(firma_obj.imagen_firma.url, width=4 * cm, height=1.5 * cm)
                    except Exception:
                        logging.getLogger(__name__).exception("Error inesperado en generar_reporte_pdf (motor_reportes_lab.py)")
                        firma_img = None

            if firma_img:
                firma_elements.append(firma_img)
            else:
                firma_elements.append(Spacer(1, 1.5 * cm))

            firma_elements.append(Paragraph(
                f'<font size="7">____________________________</font>',
                ParagraphStyle('firma_line', alignment=TA_CENTER, fontSize=7)
            ))
            firma_elements.append(Paragraph(
                f'<b>{_safe_str(nombre_validador)}</b>',
                ParagraphStyle('firma_name', alignment=TA_CENTER, fontSize=8,
                               fontName='Helvetica-Bold')
            ))
            if cedula_validador:
                firma_elements.append(Paragraph(
                    f'<font size="7">Céd. Prof. {_safe_str(cedula_validador)}</font>',
                    ParagraphStyle('firma_ced', alignment=TA_CENTER, fontSize=7)
                ))

            # Envolver en tabla centrada
            firma_table = Table([[firma_elements]], colWidths=[CONTENT_W])
            firma_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ]))
            elements.append(firma_table)
    except Exception as e:
        logger.warning(f"Error cargando firma digital del validador: {e}")

    # ── Responsable Sanitaria — Q.B. Giselle Margarita López Gutiérrez ──────────
    # Firma institucional permanente (COFEPRIS/ISO 15189). Siempre aparece.
    try:
        from reportlab.lib.enums import TA_CENTER as _TAC, TA_LEFT as _TAL
        _PS = ParagraphStyle

        responsable_cfg = _obtener_responsable_sanitaria(orden)

        _firma_block = []
        _firma_block.append(Spacer(1, 4 * mm))

        # Línea separadora
        _sep_tbl = Table([['']], colWidths=[CONTENT_W])
        _sep_tbl.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        _firma_block.append(_sep_tbl)
        _firma_block.append(Spacer(1, 3 * mm))

        # Nombre de responsable
        _firma_block.append(Paragraph(
            f'<font size="7">___________________________________</font>',
            _PS('fl', alignment=_TAC, fontSize=7)
        ))
        _firma_block.append(Paragraph(
            f'<b>{_safe_str(responsable_cfg["nombre"])}</b>',
            _PS('fn', alignment=_TAC, fontSize=8, fontName='Helvetica-Bold')
        ))
        _firma_block.append(Paragraph(
            'Responsable Sanitaria — Q.B.F.',
            _PS('ft', alignment=_TAC, fontSize=7, textColor=colors.HexColor('#555555'))
        ))
        if responsable_cfg.get('cedula'):
            _firma_block.append(Paragraph(
                f'Céd. Prof. {_safe_str(responsable_cfg["cedula"])}',
                _PS('fc', alignment=_TAC, fontSize=7, textColor=colors.HexColor('#555555'))
            ))
        if responsable_cfg.get('cofepris'):
            _firma_block.append(Paragraph(
                f'Responsable Sanitario COFEPRIS: {_safe_str(responsable_cfg["cofepris"])}',
                _PS('fcof', alignment=_TAC, fontSize=6.5, textColor=colors.HexColor('#777777'))
            ))

        _resp_tbl = Table([_firma_block], colWidths=[CONTENT_W])
        _resp_tbl.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(_resp_tbl)
    except Exception as _e:
        logger.warning('firma_responsable_sanitaria: %s', _e)

    # --- QR de validacion ---
    if request:
        base_url = f"{request.scheme}://{request.get_host()}"
    else:
        base_url = getattr(settings, 'SITE_URL', '') or os.environ.get('SITE_URL', 'http://localhost:8000')
    
    validacion_url = f"{base_url}/validar/resultado/{orden.token_acceso}/"
    
    elements.append(Spacer(1, 5 * mm))
    
    qr_img = _generar_qr(validacion_url, size=2.2 * cm)
    qr_row = [[
        Paragraph(
            f'<font size="7" color="#666666">Documento verificable en linea. '
            f'Escanee el codigo QR o visite:</font><br/>'
            f'<font size="6" color="#003366">{validacion_url}</font>',
            styles['cell_small']
        ),
        qr_img
    ]]
    qr_table = Table(qr_row, colWidths=[CONTENT_W - 3 * cm, 2.8 * cm])
    qr_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(qr_table)
    
    # --- Construir overlay ---
    # Un solo build (dos builds consumían los elementos platypus y generaban 0 páginas)
    fecha_impresion = timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')
    page_counter = [0]
    
    # Pre-cargar logo de la empresa para PDFs sin portada estática
    _empresa_logo_path = None
    if not portada_path:
        try:
            empresa = orden.empresa
            if empresa and empresa.logo:
                try:
                    _empresa_logo_path = empresa.logo.path
                except Exception:
                    logging.getLogger(__name__).exception("Error inesperado en generar_reporte_pdf (motor_reportes_lab.py)")
                    try:
                        _empresa_logo_path = empresa.logo.url
                    except Exception:
                        logging.getLogger(__name__).exception("Error inesperado en generar_reporte_pdf (motor_reportes_lab.py)")
                        pass
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en generar_reporte_pdf (motor_reportes_lab.py)")
            pass

    def draw_footer(canvas, doc):
        page_counter[0] += 1
        canvas.saveState()

        # Si no hay portada PDF, dibujar logo dinámico y nombre de empresa
        if not portada_path and _empresa_logo_path:
            try:
                canvas.drawImage(
                    _empresa_logo_path, MARGIN_LEFT, PAGE_H - 2.5 * cm,
                    width=3 * cm, height=2 * cm, preserveAspectRatio=True, mask='auto'
                )
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en draw_footer (motor_reportes_lab.py)")
                pass
        if not portada_path:
            try:
                nombre_emp = orden.empresa.nombre if orden.empresa else 'PRISLAB'
                canvas.setFont('Helvetica-Bold', 14)
                canvas.setFillColor(colors.HexColor('#003366'))
                canvas.drawString(MARGIN_LEFT + 3.5 * cm, PAGE_H - 1.5 * cm, nombre_emp)
                canvas.setFont('Helvetica', 8)
                canvas.setFillColor(colors.HexColor('#666666'))
                canvas.drawString(MARGIN_LEFT + 3.5 * cm, PAGE_H - 2 * cm, 'Laboratorio Clínico')
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en draw_footer (motor_reportes_lab.py)")
                pass

        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#888888'))
        # Pie izquierdo
        canvas.drawString(
            MARGIN_LEFT, MARGIN_BOTTOM - 15,
            f'Fecha: {fecha_impresion}'
        )
        # Pie derecho
        canvas.drawRightString(
            PAGE_W - MARGIN_RIGHT, MARGIN_BOTTOM - 15,
            f'Hoja: {page_counter[0]}'
        )
        canvas.restoreState()
    
    doc2 = SimpleDocTemplate(
        overlay_buffer,
        pagesize=letter,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )
    doc2.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)
    overlay_buffer.seek(0)
    
    # ==========================================
    # 2. MERGE: PORTADA (FONDO) + OVERLAY (DATOS)
    # ==========================================
    overlay_reader = PdfReader(overlay_buffer)
    
    if portada_path and os.path.exists(portada_path):
        portada_reader = PdfReader(portada_path)
        portada_page = portada_reader.pages[0]
    else:
        portada_page = None
        logger.warning("Portada institucional no encontrada. Generando sin membrete.")
    
    writer = PdfWriter()
    
    for i, overlay_page in enumerate(overlay_reader.pages):
        if portada_page:
            # Crear copia del fondo para cada pagina
            from copy import deepcopy
            bg = deepcopy(portada_page)
            bg.merge_page(overlay_page)
            writer.add_page(bg)
        else:
            writer.add_page(overlay_page)
    
    # ==========================================
    # 3. GENERAR BYTES FINALES (R107: Compresion optimizada)
    # ==========================================
    # Comprimir streams internos del PDF para reducir tamaño
    for page in writer.pages:
        page.compress_content_streams()
    
    final_buffer = BytesIO()
    writer.write(final_buffer)
    pdf_bytes = final_buffer.getvalue()
    final_buffer.close()
    
    logger.info(
        f"Reporte generado: Orden {orden.folio_orden}, "
        f"{len(overlay_reader.pages)} pagina(s), "
        f"{len(pdf_bytes)} bytes"
    )
    
    return pdf_bytes


def generar_reporte_pdf_simple(orden, request=None):
    """
    MODO CONTINGENCIA: Genera un PDF sin plantilla de fondo.
    Usa solo ReportLab puro - sin pypdf, sin portada institucional.
    Funciona como fallback si el motor principal falla por caracteres
    extraños, imágenes pesadas o errores de merge.

    Args:
        orden: OrdenDeServicio instance
        request: HttpRequest (opcional)

    Returns:
        bytes: PDF minimalista con los resultados
    """
    _exigir_cero_saldo_antes_de_generar_pdf(orden)
    styles = _get_styles()
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=2.5 * cm,
        bottomMargin=2.0 * cm,
    )
    elements = []

    # Header simple
    elements.append(Paragraph(
        '<b>PRIMERO SALUD LABORATORIO - RESULTADOS</b>',
        ParagraphStyle('h_simple', fontSize=14, fontName='Helvetica-Bold',
                       alignment=TA_CENTER, spaceAfter=6)
    ))
    elements.append(Paragraph(
        '<font size="8" color="#999"><i>Documento generado en modo contingencia</i></font>',
        ParagraphStyle('sub', fontSize=8, alignment=TA_CENTER, spaceAfter=12)
    ))

    # Datos del paciente (snapshot al momento de la orden para integridad forense)
    paciente = orden.paciente
    nombre_display, edad_snapshot, sexo_snapshot_simple = _orden_paciente_display(orden)
    nombre = _safe_str(
        nombre_display or (f'{getattr(paciente, "nombres", "") or ""} {getattr(paciente, "apellido_paterno", "") or ""} {getattr(paciente, "apellido_materno", "")}'.strip() or (paciente.nombre_completo if paciente else ''))
    )
    edad_val = edad_snapshot if edad_snapshot is not None else (_calcular_edad_anios(paciente.fecha_nacimiento) if paciente and getattr(paciente, 'fecha_nacimiento', None) else None)
    edad = f'{edad_val} años' if edad_val is not None and edad_val != '' else 'N/D'
    fecha_str = orden.fecha_creacion.strftime('%d/%m/%Y %H:%M') if orden.fecha_creacion else ''
    folio = orden.folio_orden or f'ORD-{orden.id}'

    info_data = [
        [Paragraph(f'<b>Paciente:</b> {nombre}', styles['cell']),
        Paragraph(f'<b>Folio:</b> {folio}', styles['cell'])],
        [Paragraph(f'<b>Edad:</b> {edad}', styles['cell']),
        Paragraph(f'<b>Fecha:</b> {fecha_str}', styles['cell'])],
    ]
    info_t = Table(info_data, colWidths=[CONTENT_W * 0.55, CONTENT_W * 0.45])
    info_t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_t)
    elements.append(Spacer(1, 8 * mm))

    # Resultados por línea LIMS (modo contingencia)
    from core.lims_cart import detalle_orden_etiqueta

    edad_simple = edad_val
    sexo_p = sexo_snapshot_simple or (getattr(paciente, 'sexo', None) or 'I')

    detalles = (
        DetalleOrden.objects.filter(orden=orden)
        .select_related('analito', 'perfil_lims', 'paquete_lims')
        .order_by('id')
    )
    for detalle in detalles:
        line_label = _safe_str(detalle_orden_etiqueta(detalle)).upper()
        elements.append(Paragraph(
            f'<b>{line_label}</b>',
            ParagraphStyle('est', fontSize=9, fontName='Helvetica-Bold',
                           spaceAfter=4, spaceBefore=6)
        ))

        header = [
            Paragraph('<b>Examen</b>', styles['cell_bold']),
            Paragraph('<b>Resultado</b>', styles['cell_bold']),
            Paragraph('<b>Unidades</b>', styles['cell_bold']),
            Paragraph('<b>Ref.</b>', styles['cell_bold']),
        ]
        col_w = [5.5 * cm, 3.5 * cm, 2.5 * cm, 5.0 * cm]
        t_data = [header]

        analitos = _analitos_para_pdf_detalle(detalle)
        if not analitos and detalle.resultado:
            t_data.append([
                Paragraph(line_label, styles['cell']),
                Paragraph(_safe_str(detalle.resultado), styles['cell']),
                Paragraph('', styles['cell']),
                Paragraph('-', styles['cell_small']),
            ])
        for analito in analitos:
            valor = 'Pendiente'
            rango_txt = '-'
            try:
                res = ResultadoParametro.objects.get(orden=orden, analito=analito)
                valor = _safe_str(res.valor, 'Pendiente')
            except ResultadoParametro.DoesNotExist:
                if len(analitos) == 1 and detalle.resultado:
                    valor = _safe_str(detalle.resultado, 'Pendiente')
            rango = _valor_referencia_analito_pdf(analito, edad_simple, sexo_p)
            if rango:
                if rango.ref_minimo is not None and rango.ref_maximo is not None:
                    rango_txt = f'{rango.ref_minimo} - {rango.ref_maximo}'
                elif (rango.texto_referencia or '').strip():
                    rango_txt = _safe_str(rango.texto_referencia)

            t_data.append([
                Paragraph(_safe_str(analito.nombre), styles['cell']),
                Paragraph(valor, styles['cell']),
                Paragraph(_safe_str(analito.unidades, ''), styles['cell']),
                Paragraph(_safe_str(rango_txt), styles['cell_small']),
            ])

        t = Table(t_data, colWidths=col_w)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)

    # Footer
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        '<font size="7" color="#888">Este documento fue generado en modo '
        'contingencia. Solicite su reporte con formato institucional.</font>',
        ParagraphStyle('ft', fontSize=7, alignment=TA_CENTER)
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"PDF SIMPLE (contingencia) generado: Orden {folio}, {len(pdf_bytes)} bytes")
    return pdf_bytes


def guardar_reporte_en_storage(orden, pdf_bytes):
    """
    Guarda el PDF en el storage (GCS en produccion, local en desarrollo).
    Actualiza el campo archivo_resultado de la orden.
    
    Returns:
        str: URL del archivo guardado, o None si falla
    """
    try:
        filename = (
            f"resultados_pdf/"
            f"{orden.folio_orden or f'ORD-{orden.id}'}"
            f"_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        
        pdf_file = ContentFile(pdf_bytes)
        orden.archivo_resultado.save(filename, pdf_file, save=True)
        
        url = orden.archivo_resultado.url
        logger.info(f"PDF guardado en storage: {filename} → {url}")
        return url
        
    except Exception as e:
        logger.error(f"Error guardando PDF en storage: {e}")
        return None