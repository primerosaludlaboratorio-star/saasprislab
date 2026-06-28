"""
PRISLAB V5.0 - GENERADOR DE ETIQUETAS TÉRMICAS PARA LABORATORIO
===============================================================
Fecha: 1 de Febrero de 2026
Objetivo: Generar etiquetas adhesivas con código de barras para tubos de ensayo

CARACTERÍSTICAS:
✅ ReportLab para control preciso de medidas
✅ Tamaño estándar: 50mm × 25mm (etiquetas Zebra/Dymo)
✅ Código de barras Code128
✅ Datos de identificación del paciente
✅ Fecha y tipo de muestra
✅ Optimizado para impresoras térmicas

FILOSOFÍA:
"Un clic = Etiqueta lista para pegar en el tubo"
"""

import io
import logging
from datetime import datetime
from django.utils import timezone
from typing import Optional

from reportlab.lib.pagesizes import mm
from reportlab.lib.units import mm as mm_unit
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

logger = logging.getLogger('etiquetas')


# ==============================================================================
# CONFIGURACIÓN DE ETIQUETAS
# ==============================================================================

# Dimensiones estándar para etiquetas de laboratorio
LABEL_WIDTH = 50 * mm_unit  # 50mm
LABEL_HEIGHT = 25 * mm_unit  # 25mm

# Márgenes
MARGIN_LEFT = 2 * mm_unit
MARGIN_RIGHT = 2 * mm_unit
MARGIN_TOP = 2 * mm_unit
MARGIN_BOTTOM = 2 * mm_unit

# Área útil
USABLE_WIDTH = LABEL_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
USABLE_HEIGHT = LABEL_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM


# ==============================================================================
# FUNCIÓN PRINCIPAL: GENERAR ETIQUETA
# ==============================================================================

def generar_etiqueta_tubo(
    folio_orden: str,
    nombre_paciente: str,
    tipo_muestra: str = "Suero",
    fecha: Optional[datetime] = None,
    incluir_logo: bool = False
) -> bytes:
    """
    Genera una etiqueta adhesiva en PDF para impresoras térmicas.
    
    Args:
        folio_orden: Folio de la orden (usado para el código de barras)
        nombre_paciente: Nombre completo del paciente
        tipo_muestra: Tipo de muestra (Suero, Orina, Sangre, etc.)
        fecha: Fecha de toma de muestra (default: hoy)
        incluir_logo: Incluir logo pequeño en la etiqueta
        
    Returns:
        bytes: PDF de la etiqueta
        
    Ejemplo:
        pdf_bytes = generar_etiqueta_tubo(
            folio_orden='ORD-001',
            nombre_paciente='Juan Pérez López',
            tipo_muestra='Suero',
            fecha=timezone.localtime(timezone.now())
        )
    """
    try:
        logger.info(f"Generando etiqueta para orden: {folio_orden}")
        
        # Crear buffer en memoria
        buffer = io.BytesIO()
        
        # Crear canvas con dimensiones de etiqueta
        c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))
        
        # Configurar fuentes
        c.setTitle(f"Etiqueta {folio_orden}")
        
        # Usar fecha actual si no se proporciona
        if fecha is None:
            fecha = timezone.localtime(timezone.now())
        
        # Truncar nombre del paciente si es muy largo
        nombre_truncado = truncar_texto(nombre_paciente, max_chars=25)
        
        # Posición Y inicial (desde arriba)
        y_pos = LABEL_HEIGHT - MARGIN_TOP
        
        # ==============================================================================
        # 1. NOMBRE DEL PACIENTE (Arriba, negrita)
        # ==============================================================================
        
        c.setFont("Helvetica-Bold", 8)
        c.drawString(MARGIN_LEFT, y_pos, nombre_truncado.upper())
        y_pos -= 4 * mm_unit
        
        # ==============================================================================
        # 2. CÓDIGO DE BARRAS (Centro)
        # ==============================================================================
        
        # Generar código de barras Code128
        barcode_drawing = generar_codigo_barras(folio_orden)
        
        # Calcular posición centrada
        barcode_width = 40 * mm_unit
        barcode_height = 10 * mm_unit
        barcode_x = MARGIN_LEFT + (USABLE_WIDTH - barcode_width) / 2
        barcode_y = y_pos - barcode_height - 2 * mm_unit
        
        # Renderizar código de barras
        renderPDF.draw(barcode_drawing, c, barcode_x, barcode_y)
        
        y_pos = barcode_y - 2 * mm_unit
        
        # ==============================================================================
        # 3. FOLIO (Debajo del código de barras, centrado)
        # ==============================================================================
        
        c.setFont("Helvetica", 6)
        folio_width = c.stringWidth(folio_orden, "Helvetica", 6)
        folio_x = MARGIN_LEFT + (USABLE_WIDTH - folio_width) / 2
        c.drawString(folio_x, y_pos, folio_orden)
        y_pos -= 3 * mm_unit
        
        # ==============================================================================
        # 4. FECHA Y TIPO DE MUESTRA (Abajo)
        # ==============================================================================
        
        c.setFont("Helvetica", 6)
        
        # Fecha (izquierda)
        fecha_str = fecha.strftime("%d/%m/%Y")
        c.drawString(MARGIN_LEFT, MARGIN_BOTTOM + 2 * mm_unit, fecha_str)
        
        # Tipo de muestra (derecha)
        tipo_width = c.stringWidth(tipo_muestra, "Helvetica", 6)
        c.drawString(
            LABEL_WIDTH - MARGIN_RIGHT - tipo_width,
            MARGIN_BOTTOM + 2 * mm_unit,
            tipo_muestra
        )
        
        # Línea separadora superior (opcional)
        # c.setStrokeColor(colors.grey)
        # c.setLineWidth(0.5)
        # c.line(MARGIN_LEFT, LABEL_HEIGHT - 5 * mm_unit, LABEL_WIDTH - MARGIN_RIGHT, LABEL_HEIGHT - 5 * mm_unit)
        
        # ==============================================================================
        # 5. FINALIZAR
        # ==============================================================================
        
        c.showPage()
        c.save()
        
        # Obtener bytes del PDF
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"✓ Etiqueta generada: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except (ValueError, TypeError, AttributeError, ImportError) as e:
        logger.error(f"Error al generar etiqueta: {e}", exc_info=True)
        raise RuntimeError(f"Error al generar etiqueta: {str(e)}") from e


# ==============================================================================
# GENERADOR DE CÓDIGO DE BARRAS
# ==============================================================================

def generar_codigo_barras(texto: str, ancho: float = 40, alto: float = 10) -> Drawing:
    """
    Genera un código de barras Code128.
    
    Args:
        texto: Texto a codificar
        ancho: Ancho en mm
        alto: Alto en mm
        
    Returns:
        Drawing: Objeto de dibujo de ReportLab
    """
    try:
        # Crear código de barras compatible con versiones recientes de ReportLab
        # donde los objetos Code128 ya no se pueden insertar directamente en Group.
        drawing = createBarcodeDrawing(
            'Code128',
            value=texto,
            barWidth=ancho * mm_unit,
            barHeight=alto * mm_unit,
            humanReadable=False,
        )
        return drawing
        
    except (ValueError, TypeError, AttributeError) as e:
        logger.error(f"Error al generar código de barras: {e}")
        # Retornar dibujo vacío en caso de error
        return Drawing(ancho * mm_unit, alto * mm_unit)


# ==============================================================================
# FUNCIÓN: ETIQUETA MÚLTIPLE (VARIOS TUBOS)
# ==============================================================================

def generar_etiquetas_multiples(ordenes: list) -> bytes:
    """
    Genera múltiples etiquetas en un solo PDF (una por página).
    
    Args:
        ordenes: Lista de diccionarios con datos de las órdenes
            [
                {
                    'folio_orden': 'ORD-001',
                    'nombre_paciente': 'Juan Pérez',
                    'tipo_muestra': 'Suero',
                    'fecha': timezone.localtime(timezone.now())
                },
                ...
            ]
        
    Returns:
        bytes: PDF con múltiples etiquetas
        
    Útil para: Imprimir todas las etiquetas de la mañana de una vez
    """
    try:
        logger.info(f"Generando {len(ordenes)} etiquetas")
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))
        
        for orden in ordenes:
            # Crear nueva página para cada etiqueta
            c.setTitle(f"Etiquetas Múltiples")
            
            folio_orden = orden.get('folio_orden', 'SIN-FOLIO')
            nombre_paciente = orden.get('nombre_paciente', 'SIN NOMBRE')
            tipo_muestra = orden.get('tipo_muestra', 'Suero')
            fecha = orden.get('fecha', timezone.localtime(timezone.now()))
            
            # Nombre del paciente
            nombre_truncado = truncar_texto(nombre_paciente, max_chars=25)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(MARGIN_LEFT, LABEL_HEIGHT - MARGIN_TOP, nombre_truncado.upper())
            
            # Código de barras
            barcode_drawing = generar_codigo_barras(folio_orden)
            barcode_x = MARGIN_LEFT + (USABLE_WIDTH - 40 * mm_unit) / 2
            barcode_y = LABEL_HEIGHT / 2 - 5 * mm_unit
            renderPDF.draw(barcode_drawing, c, barcode_x, barcode_y)
            
            # Folio
            c.setFont("Helvetica", 6)
            folio_width = c.stringWidth(folio_orden, "Helvetica", 6)
            folio_x = MARGIN_LEFT + (USABLE_WIDTH - folio_width) / 2
            c.drawString(folio_x, barcode_y - 2 * mm_unit, folio_orden)
            
            # Fecha y tipo
            fecha_str = fecha.strftime("%d/%m/%Y")
            c.drawString(MARGIN_LEFT, MARGIN_BOTTOM + 2 * mm_unit, fecha_str)
            tipo_width = c.stringWidth(tipo_muestra, "Helvetica", 6)
            c.drawString(
                LABEL_WIDTH - MARGIN_RIGHT - tipo_width,
                MARGIN_BOTTOM + 2 * mm_unit,
                tipo_muestra
            )
            
            # Nueva página para la siguiente etiqueta
            c.showPage()
        
        c.save()
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"✓ {len(ordenes)} etiquetas generadas: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except (ValueError, TypeError, AttributeError, ImportError) as e:
        logger.error(f"Error al generar etiquetas múltiples: {e}", exc_info=True)
        raise RuntimeError(f"Error al generar etiquetas múltiples: {str(e)}") from e


# ==============================================================================
# FUNCIÓN: ETIQUETA CON QR (ALTERNATIVA)
# ==============================================================================

def generar_etiqueta_con_qr(
    folio_orden: str,
    nombre_paciente: str,
    tipo_muestra: str = "Suero",
    fecha: Optional[datetime] = None
) -> bytes:
    """
    Genera una etiqueta con QR en lugar de código de barras.
    
    Útil para: Trazabilidad avanzada con smartphones
    """
    try:
        import qrcode
        from reportlab.platypus import Image
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))
        
        # Generar QR
        qr = qrcode.QRCode(version=1, box_size=2, border=1)
        qr.add_data(f"PRISLAB:{folio_orden}")
        qr.make(fit=True)
        
        # Guardar QR en buffer temporal
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        # Dibujar en canvas
        c.setFont("Helvetica-Bold", 7)
        nombre_truncado = truncar_texto(nombre_paciente, max_chars=25)
        c.drawString(MARGIN_LEFT, LABEL_HEIGHT - MARGIN_TOP, nombre_truncado.upper())
        
        # QR en el centro
        qr_size = 15 * mm_unit
        qr_x = MARGIN_LEFT + (USABLE_WIDTH - qr_size) / 2
        qr_y = LABEL_HEIGHT / 2 - qr_size / 2
        c.drawImage(qr_buffer, qr_x, qr_y, width=qr_size, height=qr_size)
        
        # Folio y fecha
        if fecha is None:
            fecha = timezone.localtime(timezone.now())
        
        c.setFont("Helvetica", 6)
        fecha_str = fecha.strftime("%d/%m/%Y")
        c.drawString(MARGIN_LEFT, MARGIN_BOTTOM + 2 * mm_unit, fecha_str)
        c.drawString(MARGIN_LEFT, MARGIN_BOTTOM + 5 * mm_unit, folio_orden)
        
        tipo_width = c.stringWidth(tipo_muestra, "Helvetica", 6)
        c.drawString(
            LABEL_WIDTH - MARGIN_RIGHT - tipo_width,
            MARGIN_BOTTOM + 2 * mm_unit,
            tipo_muestra
        )
        
        c.showPage()
        c.save()
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"✓ Etiqueta con QR generada")
        return pdf_bytes
        
    except (ImportError, ValueError, TypeError, AttributeError) as e:
        logger.error(f"Error al generar etiqueta con QR: {e}", exc_info=True)
        # Fallback a etiqueta normal
        return generar_etiqueta_tubo(folio_orden, nombre_paciente, tipo_muestra, fecha)


# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def truncar_texto(texto: str, max_chars: int = 25) -> str:
    """
    Trunca texto para que quepa en la etiqueta.
    
    Args:
        texto: Texto a truncar
        max_chars: Máximo de caracteres
        
    Returns:
        str: Texto truncado
    """
    if len(texto) <= max_chars:
        return texto
    
    # Truncar y agregar puntos suspensivos
    return texto[:max_chars - 3] + "..."


def validar_codigo_barras(codigo: str) -> str:
    """
    Valida y limpia el código para el código de barras.
    
    Args:
        codigo: Código a validar
        
    Returns:
        str: Código limpio
    """
    # Code128 soporta ASCII 0-127
    # Eliminar caracteres no válidos
    codigo_limpio = ''.join(c for c in codigo if ord(c) < 128)
    
    # Limitar longitud (Code128 puede manejar hasta ~80 caracteres, pero mejor mantenerlo corto)
    if len(codigo_limpio) > 20:
        logger.warning(f"Código muy largo: {len(codigo_limpio)} caracteres. Truncando a 20.")
        codigo_limpio = codigo_limpio[:20]
    
    return codigo_limpio


# ==============================================================================
# FUNCIÓN DE PRUEBA
# ==============================================================================

def test_generar_etiqueta():
    """
    Prueba la generación de una etiqueta.
    """
    try:
        pdf_bytes = generar_etiqueta_tubo(
            folio_orden='ORD-001',
            nombre_paciente='Juan Pérez López',
            tipo_muestra='Suero',
            fecha=timezone.localtime(timezone.now())
        )
        
        # Guardar en archivo temporal (autoeliminado al salir)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=True) as f:
            f.write(pdf_bytes)
            f.flush()
            print(f"✅ Etiqueta de prueba generada: {len(pdf_bytes)} bytes")
            print("   Guardado temporalmente en: %s" % f.name)
        return True
        
    except (RuntimeError, ValueError, TypeError, ImportError) as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    print("Probando generación de etiqueta...")
    test_generar_etiqueta()
