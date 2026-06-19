"""
PRISLAB V5 - Motor de Recetas Medicas V1.0
============================================
Genera PDFs de recetas medicas usando recetario_institucional.pdf
como capa de fondo (underlay), replicando el formato oficial de
Primero Salud Laboratorio.

Arquitectura: PDF Background (recetario) + ReportLab Overlay (datos)
Firma Digital: Automatica si la Dra. tiene firma cargada
Ajuste de Texto: Margenes automaticos para no invadir logos/pie
"""

import logging
import os
from datetime import date, datetime
from django.utils import timezone
from io import BytesIO

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

logger = logging.getLogger(__name__)

# ======================================================================
# COORDENADAS Y MARGENES
# Tamano carta: 612 x 792 pts (21.59 x 27.94 cm)
# ======================================================================
PAGE_W, PAGE_H = letter

# Margenes que respetan el membrete del recetario
# (logos laterales, encabezado con nombre/cedula, pie con direccion)
MARGIN_TOP = 5.5 * cm       # Debajo del encabezado del medico
MARGIN_BOTTOM = 2.8 * cm    # Arriba del pie (direccion, telefonos)
MARGIN_LEFT = 2.0 * cm      # Respeta logo izquierdo
MARGIN_RIGHT = 1.8 * cm     # Respeta logo derecho

CONTENT_W = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT

# Colores
COLOR_LABEL = colors.HexColor('#555555')
COLOR_VALUE = colors.HexColor('#111111')
COLOR_RX = colors.HexColor('#0066cc')
COLOR_LINE = colors.HexColor('#cccccc')
COLOR_ACCENT = colors.HexColor('#003366')


def _get_recetario_path():
    """Obtiene la ruta al PDF del recetario institucional."""
    for base in ['staticfiles', 'static']:
        path = os.path.join(settings.BASE_DIR, base, 'pdf', 'recetario_institucional.pdf')
        if os.path.exists(path):
            return path
    return None


def _calcular_edad(fecha_nacimiento):
    """Calcula edad legible."""
    if not fecha_nacimiento:
        return '___'
    hoy = date.today()
    dias = (hoy - fecha_nacimiento).days
    if dias < 365:
        return f"{int(dias / 30.44)} meses"
    return f"{int(dias / 365.25)} anios"


def _safe(val, default='___'):
    """
    Valor seguro para impresion de PDF (SENTINEL 2.0).
    Normaliza Unicode, elimina emojis y caracteres que rompen ReportLab.
    """
    import unicodedata
    import re

    if val is None or val == '':
        return default
    s = str(val).strip()
    if not s:
        return default

    # Normalizar Unicode NFC
    s = unicodedata.normalize('NFC', s)

    # Reemplazar caracteres problematicos comunes
    reemplazos = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-', '\u2026': '...',
        '\u00a0': ' ', '\u200b': '', '\u200e': '', '\u200f': '',
        '\ufeff': '',
    }
    for viejo, nuevo in reemplazos.items():
        s = s.replace(viejo, nuevo)

    # Eliminar emojis y simbolos exoticos
    s = ''.join(
        c for c in s
        if unicodedata.category(c) not in ('So', 'Sk', 'Cs')
    )

    # Intentar codificar a latin-1 (limite de ReportLab)
    try:
        s.encode('latin-1')
    except UnicodeEncodeError:
        s = s.encode('ascii', 'replace').decode('ascii')

    return s or default


# ======================================================================
# ESTILOS
# ======================================================================
def _get_styles():
    base = getSampleStyleSheet()
    return {
        'label': ParagraphStyle(
            'lbl', parent=base['Normal'],
            fontSize=8, textColor=COLOR_LABEL, leading=10,
            fontName='Helvetica-Bold',
        ),
        'value': ParagraphStyle(
            'val', parent=base['Normal'],
            fontSize=9.5, fontName='Helvetica-Bold',
            textColor=COLOR_VALUE, leading=12,
        ),
        'value_small': ParagraphStyle(
            'val_sm', parent=base['Normal'],
            fontSize=8.5, fontName='Helvetica',
            textColor=COLOR_VALUE, leading=11,
        ),
        'signos': ParagraphStyle(
            'signos', parent=base['Normal'],
            fontSize=8.5, fontName='Helvetica',
            leading=11,
        ),
        'rx_title': ParagraphStyle(
            'rx', parent=base['Normal'],
            fontSize=32, fontName='Helvetica-Bold',
            textColor=COLOR_RX, leading=36,
        ),
        'tratamiento': ParagraphStyle(
            'trat', parent=base['Normal'],
            fontSize=10, fontName='Helvetica',
            leading=16, spaceAfter=4,
        ),
        'diagnostico': ParagraphStyle(
            'diag', parent=base['Normal'],
            fontSize=9.5, fontName='Helvetica-Bold',
            textColor=COLOR_ACCENT, leading=13,
        ),
        'cita': ParagraphStyle(
            'cita', parent=base['Normal'],
            fontSize=9, fontName='Helvetica-Bold',
            leading=12,
        ),
        'firma': ParagraphStyle(
            'firma', parent=base['Normal'],
            fontSize=9, fontName='Helvetica',
            alignment=TA_CENTER, leading=12,
        ),
        'footer': ParagraphStyle(
            'foot', parent=base['Normal'],
            fontSize=7, alignment=TA_CENTER,
            textColor=colors.HexColor('#888888'),
        ),
    }


# ======================================================================
# BUILDERS
# ======================================================================
def _build_patient_info(consulta, styles):
    """Bloque: Nombre, Edad, Fecha."""
    paciente = consulta.paciente
    edad = _calcular_edad(paciente.fecha_nacimiento)
    fecha = consulta.fecha_consulta.strftime('%d/%m/%Y') if consulta.fecha_consulta else timezone.localtime(timezone.now()).strftime('%d/%m/%Y')

    data = [
        [
            Paragraph('<b>NOMBRE:</b>', styles['label']),
            Paragraph(f'<b>{_safe(paciente.nombre_completo).upper()}</b>', styles['value']),
            Paragraph('<b>EDAD:</b>', styles['label']),
            Paragraph(f'<b>{edad}</b>', styles['value_small']),
            Paragraph('<b>FECHA:</b>', styles['label']),
            Paragraph(f'<b>{fecha}</b>', styles['value_small']),
        ],
    ]

    col_widths = [2.0 * cm, 6.0 * cm, 1.3 * cm, 2.5 * cm, 1.3 * cm, 3.0 * cm]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, COLOR_LINE),
    ]))
    return t


def _build_signos_vitales(consulta, styles):
    """Bloque: T/A, FC, FR, Temp, Peso, Talla, IMC."""
    sv = None
    if hasattr(consulta, 'signos_vitales') and consulta.signos_vitales:
        sv = consulta.signos_vitales

    # Tambien verificar datos directos en la receta
    receta = None
    if hasattr(consulta, 'receta') and consulta.receta:
        receta = consulta.receta

    def get_val(sv_field, receta_field=None):
        """Intenta obtener de signos vitales primero, luego de receta."""
        if sv:
            val = getattr(sv, sv_field, None)
            if val is not None:
                return str(val)
        if receta and receta_field:
            val = getattr(receta, receta_field, None)
            if val is not None:
                return str(val)
        return '___'

    pa_s = get_val('presion_arterial_sistolica', 'presion_arterial_sistolica')
    pa_d = get_val('presion_arterial_diastolica', 'presion_arterial_diastolica')
    presion = f"{pa_s}/{pa_d}" if pa_s != '___' else '___/___'

    data = [
        [
            Paragraph(f'<b>T/A:</b> {presion} mmHg', styles['signos']),
            Paragraph(f'<b>FC:</b> {get_val("frecuencia_cardiaca", "frecuencia_cardiaca")}', styles['signos']),
            Paragraph(f'<b>FR:</b> {get_val("frecuencia_respiratoria", "frecuencia_respiratoria")}', styles['signos']),
            Paragraph(f'<b>Temp:</b> {get_val("temperatura", "temperatura")} C', styles['signos']),
        ],
        [
            Paragraph(f'<b>Peso:</b> {get_val("peso", "peso")} kg', styles['signos']),
            Paragraph(f'<b>Talla:</b> {get_val("talla", "talla")} m', styles['signos']),
            Paragraph(f'<b>IMC:</b> {get_val("imc", "imc")}', styles['signos']),
            Paragraph('', styles['signos']),
        ],
    ]

    col_w = CONTENT_W / 4
    t = Table(data, colWidths=[col_w] * 4)
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('BOX', (0, 0), (-1, -1), 0.3, COLOR_LINE),
    ]))
    return t


def _build_diagnostico_alergias(consulta, styles):
    """Bloque: Alergias + Diagnostico (IDX)."""
    elements = []

    # Alergias
    alergias = 'Ninguna conocida'
    paciente = consulta.paciente
    if hasattr(paciente, 'alergias') and paciente.alergias:
        alergias = paciente.alergias
    elif hasattr(paciente, 'historia_clinica'):
        try:
            hc = paciente.historia_clinica
            if hc and hasattr(hc, 'alergias') and hc.alergias:
                alergias = hc.alergias
        except Exception:
            pass

    elements.append(Paragraph(
        f'<b>ALERGIAS:</b> <font color="#dc3545">{_safe(alergias, "Ninguna conocida")}</font>',
        styles['value_small']
    ))
    elements.append(Spacer(1, 2 * mm))

    # Diagnostico
    idx = _safe(consulta.diagnostico_principal, 'Sin diagnostico')
    if consulta.diagnostico_cie10:
        idx += f' ({consulta.diagnostico_cie10})'

    elements.append(Paragraph(f'<b>IDX:</b> {idx}', styles['diagnostico']))

    if consulta.diagnosticos_secundarios:
        elements.append(Paragraph(
            f'<font size="8" color="#666">{consulta.diagnosticos_secundarios}</font>',
            styles['value_small']
        ))

    return elements


def _build_tratamiento(consulta, styles):
    """Bloque: Rx + Plan de tratamiento."""
    elements = []

    # Rx grande
    elements.append(Paragraph('<b>Rx</b>', styles['rx_title']))
    elements.append(Spacer(1, 3 * mm))

    # Obtener texto del tratamiento
    texto = ''

    # Prioridad 1: Items de la receta (si existen)
    if hasattr(consulta, 'receta') and consulta.receta:
        receta = consulta.receta
        if hasattr(receta, 'items') and receta.items.exists():
            for item in receta.items.all():
                # Nombre del medicamento (producto del catálogo o texto libre)
                nombre_med = ''
                if item.medicamento:
                    nombre_med = item.medicamento.nombre
                elif item.texto_libre:
                    # texto_libre puede tener formato: "Nombre | Dosis: X | Duración: Y"
                    partes = item.texto_libre.split(' | ')
                    nombre_med = partes[0] if partes else item.texto_libre
                
                texto += f'<b>{nombre_med}</b><br/>'
                
                # Extraer dosis y duración del texto_libre
                if item.texto_libre and ' | ' in item.texto_libre:
                    partes = item.texto_libre.split(' | ')
                    for parte in partes[1:]:
                        texto += f'  {parte}<br/>'
                
                if item.cantidad and item.cantidad > 1:
                    texto += f'  Cantidad: {item.cantidad}<br/>'
                texto += '<br/>'
        elif receta.indicaciones:
            texto = receta.indicaciones.replace('\n', '<br/>')

    # Prioridad 2: Plan de tratamiento de la consulta
    if not texto and consulta.plan_tratamiento:
        texto = consulta.plan_tratamiento.replace('\n', '<br/>')

    if not texto:
        texto = ('_' * 60 + '<br/>') * 6

    elements.append(Paragraph(texto, styles['tratamiento']))
    return elements


def _build_cita_y_firma(consulta, styles):
    """Bloque: Proxima cita + Firma."""
    elements = []

    # Proxima cita
    prox = '___/___/___'
    if consulta.fecha_proxima_cita:
        prox = consulta.fecha_proxima_cita.strftime('%d/%m/%Y')

    elements.append(Paragraph(
        f'<b>PROXIMA CITA:</b> {prox}',
        styles['cita']
    ))
    elements.append(Spacer(1, 8 * mm))

    # Firma digital
    firma_insertada = False
    medico = consulta.medico

    # Intentar obtener firma desde FirmaDigital
    try:
        from core.models import FirmaDigital
        firma_obj = None

        if medico and medico.cedula_profesional:
            firma_obj = FirmaDigital.objects.filter(
                cedula_profesional=medico.cedula_profesional,
                activa=True
            ).first()

        if not firma_obj:
            firma_obj = FirmaDigital.objects.filter(activa=True).first()

        if firma_obj and firma_obj.imagen_firma:
            try:
                import os as _os
                firma_path = firma_obj.imagen_firma.path
                if _os.path.exists(firma_path):
                    from PIL import Image as PILImage
                    pil = PILImage.open(firma_path)
                    w, h = pil.size
                    max_w = 5 * cm
                    ratio = h / w
                    fw = max_w
                    fh = max_w * ratio
                    if fh > 2.5 * cm:
                        fh = 2.5 * cm
                        fw = fh / ratio

                    img = RLImage(firma_path, width=fw, height=fh)
                    t = Table([[img]], colWidths=[CONTENT_W])
                    t.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), -6),
                    ]))
                    elements.append(t)
                    firma_insertada = True
            except Exception as e:
                logger.warning(f"Error cargando firma: {e}")

    except Exception:
        pass

    # Tambien intentar firma desde Receta.medico_firma_digital
    if not firma_insertada:
        try:
            if hasattr(consulta, 'receta') and consulta.receta and consulta.receta.medico_firma_digital:
                firma_field = consulta.receta.medico_firma_digital
                try:
                    firma_path = firma_field.path
                    if os.path.exists(firma_path):
                        from PIL import Image as PILImage
                        pil = PILImage.open(firma_path)
                        w, h = pil.size
                        max_w = 5 * cm
                        ratio = h / w
                        fw = max_w
                        fh = max_w * ratio
                        if fh > 2.5 * cm:
                            fh = 2.5 * cm
                            fw = fh / ratio
                        img = RLImage(firma_path, width=fw, height=fh)
                        t = Table([[img]], colWidths=[CONTENT_W])
                        t.setStyle(TableStyle([
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), -6),
                        ]))
                        elements.append(t)
                        firma_insertada = True
                except Exception:
                    pass
        except Exception:
            pass

    if not firma_insertada:
        elements.append(Spacer(1, 2 * cm))

    # Linea de firma + datos
    nombre = f"Dra. {medico.nombre_completo}" if medico else "FIRMA"
    cedula = medico.cedula_profesional if medico else ''
    especialidad = medico.especialidad if medico else ''

    firma_data = [
        [Paragraph('_' * 50, styles['firma'])],
        [Paragraph(f'<b>{nombre}</b>', styles['firma'])],
        [Paragraph(f'{especialidad}', styles['firma'])],
        [Paragraph(f'Ced. Prof. {cedula}', styles['firma'])],
    ]

    tf = Table(firma_data, colWidths=[CONTENT_W])
    tf.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(tf)

    return elements


# ======================================================================
# CANVAS CON NUMERACION AUTOMATICA DE PAGINAS
# ======================================================================
from reportlab.pdfgen import canvas as _canvas_module


class NumberedCanvas(_canvas_module.Canvas):
    """
    Canvas personalizado que agrega pie de pagina con fecha de impresion
    y numeracion automatica X/Y en cada pagina.
    
    Resuelve el bug de ReportLab donde doc.build() consume la lista de
    elementos, haciendo imposible un segundo build para agregar footers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        super().showPage()

    def save(self):
        total = len(self._saved_page_states)
        fecha_impresion = timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')
        for idx, state in enumerate(self._saved_page_states, 1):
            self.__dict__.update(state)
            self.saveState()
            self.setFont('Helvetica', 6.5)
            self.setFillColor(colors.HexColor('#999999'))
            self.drawString(
                MARGIN_LEFT, MARGIN_BOTTOM - 12,
                f'Impreso: {fecha_impresion}'
            )
            if total > 1:
                self.drawRightString(
                    PAGE_W - MARGIN_RIGHT, MARGIN_BOTTOM - 12,
                    f'Hoja {idx}/{total}'
                )
            self.restoreState()
            super().showPage()
        super().save()


# ======================================================================
# GENERADOR PRINCIPAL
# ======================================================================
def generar_receta_pdf(consulta, request=None):
    """
    Genera el PDF de receta medica con recetario institucional como fondo.

    CORREGIDO: Usa un unico build con NumberedCanvas para evitar
    el bug de ReportLab donde el segundo build tiene la lista de
    elementos vacia (consumida por el primer build).

    Args:
        consulta: ConsultaMedica instance
        request: HttpRequest (opcional)

    Returns:
        bytes: Contenido del PDF generado
    """
    if hasattr(consulta, 'receta') and consulta.receta:
        consulta.receta.validar_items_antes_de_emitir()

    styles = _get_styles()
    recetario_path = _get_recetario_path()

    # ==========================================
    # 1. CONSTRUIR OVERLAY CON REPORTLAB
    # ==========================================
    overlay_buffer = BytesIO()

    doc = SimpleDocTemplate(
        overlay_buffer, pagesize=letter,
        leftMargin=MARGIN_LEFT, rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
    )

    elements = []

    # --- Datos del paciente ---
    elements.append(_build_patient_info(consulta, styles))
    elements.append(Spacer(1, 3 * mm))

    # --- Signos vitales ---
    elements.append(_build_signos_vitales(consulta, styles))
    elements.append(Spacer(1, 3 * mm))

    # --- Diagnostico y alergias ---
    elements.extend(_build_diagnostico_alergias(consulta, styles))
    elements.append(Spacer(1, 4 * mm))

    # --- Tratamiento (Rx) ---
    elements.extend(_build_tratamiento(consulta, styles))
    elements.append(Spacer(1, 4 * mm))

    # --- Cita y firma ---
    elements.extend(_build_cita_y_firma(consulta, styles))

    # Build UNICO con NumberedCanvas (agrega pie de pagina automaticamente)
    # IMPORTANTE: NO usar dos builds - ReportLab consume la lista de elements
    # en el primer build, dejandola vacia para el segundo (genera PDF en blanco).
    doc.build(elements, canvasmaker=NumberedCanvas)

    overlay_buffer.seek(0)

    # ==========================================
    # 2. MERGE: RECETARIO (FONDO) + OVERLAY
    # ==========================================
    overlay_reader = PdfReader(overlay_buffer)

    recetario_page = None
    if recetario_path and os.path.exists(recetario_path):
        recetario_reader = PdfReader(recetario_path)
        recetario_page = recetario_reader.pages[0]
    else:
        logger.info("Recetario institucional no encontrado. Generando sin membrete.")

    writer = PdfWriter()

    for overlay_page in overlay_reader.pages:
        if recetario_page:
            from copy import deepcopy
            bg = deepcopy(recetario_page)
            bg.merge_page(overlay_page)
            writer.add_page(bg)
        else:
            writer.add_page(overlay_page)

    # ==========================================
    # 3. GENERAR BYTES FINALES
    # ==========================================
    final_buffer = BytesIO()
    writer.write(final_buffer)
    pdf_bytes = final_buffer.getvalue()
    final_buffer.close()

    logger.info(
        f"Receta generada: Consulta {consulta.folio_consulta}, "
        f"{len(overlay_reader.pages)} pagina(s), "
        f"{len(pdf_bytes)} bytes"
    )

    return pdf_bytes
