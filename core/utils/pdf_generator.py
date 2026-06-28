"""
PRISLAB V5.0 - GENERADOR FORENSE DE PDF
========================================
Fecha: 1 de Febrero de 2026
Objetivo: Generar PDFs de alta calidad con elementos de seguridad

CARACTERÍSTICAS:
✅ WeasyPrint para renderizado HTML → PDF
✅ Carga explícita de CSS para mantener estilos
✅ Generación de QR de validación
✅ Incrustación de firma digital
✅ Tamaño carta exacto (Letter)
✅ Alta resolución
✅ Guardado automático en Google Drive

FILOSOFÍA:
"El PDF debe ser VISUALMENTE IDÉNTICO a la vista previa en pantalla"
"""

import os
import io
import base64
import logging
import qrcode
from pathlib import Path
from datetime import datetime
from django.utils import timezone
from typing import Dict, Any, Optional
import uuid

from django.conf import settings
from django.template.loader import render_to_string
from django.core.files.base import ContentFile

# WeasyPrint (en Ubuntu/CI sin libcairo/pango el wheel importa pero puede lanzar OSError)
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as exc:
    WEASYPRINT_AVAILABLE = False
    logging.warning("WeasyPrint no disponible (%s): pip install weasyprint + libs sistema (p. ej. libcairo2, libpango).", exc)

logger = logging.getLogger('pdf')


def _empresa_logo_uri_para_weasyprint(empresa) -> Optional[str]:
    """
    Ruta file:// al logo en disco para WeasyPrint (evita URLs relativas rotas).
    Si no hay archivo válido, retorna None y el template usa fallback textual.
    """
    if not empresa:
        return None
    logo = getattr(empresa, 'logo', None)
    if not logo:
        return None
    try:
        storage_path = getattr(logo, 'path', None)
        if storage_path and os.path.isfile(storage_path):
            return Path(storage_path).as_uri()
    except Exception as exc:
        logging.getLogger(__name__).exception("Error inesperado en _empresa_logo_uri_para_weasyprint (pdf_generator.py)")
        logger.debug('Logo empresa no resuelto para PDF: %s', exc)
    return None


# ==============================================================================
# FUNCIÓN PRINCIPAL: RENDER TO PDF
# ==============================================================================

def render_to_pdf(template_path: str, context: Dict[str, Any], css_files: Optional[list] = None) -> bytes:
    """
    Renderiza un template HTML a PDF de alta calidad.
    
    Args:
        template_path: Ruta del template HTML
        context: Diccionario de contexto para el template
        css_files: Lista de archivos CSS adicionales (opcionales)
        
    Returns:
        bytes: Contenido del PDF
        
    Raises:
        Exception: Si hay error en la generación
        
    Ejemplo:
        pdf_bytes = render_to_pdf(
            'pdfs/receta_print.html',
            {'paciente': paciente, 'receta': receta},
            css_files=['css/paper_sheet.css', 'css/bootstrap.min.css']
        )
    """
    if not WEASYPRINT_AVAILABLE:
        raise Exception("WeasyPrint no está instalado")
    
    try:
        logger.info(f"Iniciando renderizado de PDF: {template_path}")
        
        # Renderizar template HTML
        html_string = render_to_string(template_path, context)
        
        # Configuración de fuentes
        font_config = FontConfiguration()
        
        # Preparar CSS
        css_list = []
        
        # CSS del sistema (Bootstrap, etc.)
        base_css_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR, 'static', 'css')
        
        # Si css_files no se especifica, usar defaults
        if css_files is None:
            css_files = [
                'css/bootstrap.min.css',
                'css/paper_sheet.css'
            ]
        
        # Cargar archivos CSS
        for css_file in css_files:
            css_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR, 'static', css_file)
            
            if os.path.exists(css_path):
                css_list.append(CSS(filename=css_path, font_config=font_config))
                logger.info(f"✓ CSS cargado: {css_file}")
            else:
                logger.warning(f"CSS no encontrado: {css_path}")
        
        # CSS inline para ajustes finales
        inline_css = CSS(string='''
            @page {
                size: Letter;
                margin: 0;
            }
            
            body {
                margin: 0;
                padding: 0;
                font-family: 'Times New Roman', serif;
            }
            
            * {
                box-sizing: border-box;
            }
        ''', font_config=font_config)
        
        css_list.append(inline_css)
        
        # Generar PDF
        logger.info("Generando PDF...")
        html = HTML(string=html_string, base_url=settings.STATIC_URL)
        pdf_bytes = html.write_pdf(stylesheets=css_list, font_config=font_config)
        
        logger.info(f"✓ PDF generado exitosamente: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Error al generar PDF: {e}", exc_info=True)
        raise Exception(f"Error al generar PDF: {str(e)}")


# ==============================================================================
# GENERADOR DE QR DE SEGURIDAD
# ==============================================================================

def generar_qr_validacion(documento_id: str, tipo: str = 'receta') -> str:
    """
    Genera un QR con URL de validación única.
    
    Args:
        documento_id: UUID o ID del documento
        tipo: Tipo de documento ('receta', 'laboratorio', etc.)
        
    Returns:
        str: Base64 del QR en formato PNG
        
    Ejemplo:
        qr_base64 = generar_qr_validacion(receta.uuid, 'receta')
        # En template: <img src="data:image/png;base64,{{ qr_base64 }}">
    """
    try:
        # Construir URL de validación
        base_url = getattr(settings, 'SITE_URL', 'https://prislab.com')
        url_validacion = f"{base_url}/validar/{tipo}/{documento_id}"
        
        logger.info(f"Generando QR para: {url_validacion}")
        
        # Crear QR
        qr = qrcode.QRCode(
            version=1,  # Tamaño automático
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # Alta corrección de errores
            box_size=10,
            border=4,
        )
        
        qr.add_data(url_validacion)
        qr.make(fit=True)
        
        # Generar imagen
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        logger.info("✓ QR generado exitosamente")
        return img_base64
        
    except Exception as e:
        logger.error(f"Error al generar QR: {e}", exc_info=True)
        return ""


def generar_qr_con_datos_cifrados(datos: Dict[str, Any]) -> str:
    """
    Genera un QR con datos cifrados del documento.
    
    Args:
        datos: Diccionario con datos a cifrar
        
    Returns:
        str: Base64 del QR
        
    Nota: Útil para validación offline
    """
    try:
        import json
        import hashlib
        
        # Convertir datos a JSON
        json_data = json.dumps(datos, sort_keys=True)
        
        # Generar hash
        hash_data = hashlib.sha256(json_data.encode()).hexdigest()
        
        # Crear QR con el hash
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        
        qr.add_data(hash_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return img_base64
        
    except Exception as e:
        logger.error(f"Error al generar QR cifrado: {e}", exc_info=True)
        return ""


# ==============================================================================
# FUNCIONES ESPECÍFICAS: RECETA MÉDICA
# ==============================================================================

def generar_pdf_receta(receta, paciente, medico) -> bytes:
    """
    Genera PDF de receta médica con firma y QR.
    
    Args:
        receta: Instancia del modelo Receta
        paciente: Instancia del modelo Paciente
        medico: Instancia del modelo Usuario (médico)
        
    Returns:
        bytes: PDF generado
    """
    try:
        logger.info(f"Generando PDF de receta: {receta.id}")
        
        # Generar UUID si no existe
        if not hasattr(receta, 'uuid') or not receta.uuid:
            receta.uuid = str(uuid.uuid4())
            receta.save(update_fields=['uuid'])
        
        # Generar QR de validación
        qr_base64 = generar_qr_validacion(str(receta.uuid), 'receta')
        
        # Preparar contexto
        context = {
            'receta': receta,
            'paciente': paciente,
            'medico': medico,
            'qr_code': qr_base64,
            'fecha_generacion': timezone.localtime(timezone.now()),
            'empresa': getattr(medico, 'empresa', None),
        }
        
        # Agregar firma digital si existe
        if hasattr(medico, 'firma_digital') and medico.firma_digital:
            try:
                # Convertir firma a base64 para incrustar en PDF
                with medico.firma_digital.open('rb') as f:
                    firma_base64 = base64.b64encode(f.read()).decode()
                context['firma_digital_base64'] = firma_base64
            except Exception as e:
                logger.warning(f"No se pudo cargar firma digital: {e}")
                context['firma_digital_base64'] = None
        else:
            context['firma_digital_base64'] = None
        
        # Generar PDF
        pdf_bytes = render_to_pdf('pdfs/receta_print.html', context)
        
        logger.info(f"✓ PDF de receta generado: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Error al generar PDF de receta: {e}", exc_info=True)
        raise


# ==============================================================================
# FUNCIONES ESPECÍFICAS: RESULTADO DE LABORATORIO
# ==============================================================================

def generar_pdf_resultado_lab(orden, resultados, empresa) -> bytes:
    """
    Genera PDF de resultados de laboratorio con QR.
    
    Args:
        orden: Instancia del modelo OrdenDeServicio
        resultados: QuerySet de ResultadoParametro
        empresa: Instancia del modelo Empresa
        
    Returns:
        bytes: PDF generado
    """
    try:
        logger.info(f"Generando PDF de resultados: Orden {orden.folio_orden}")
        
        # Generar UUID si no existe
        if not hasattr(orden, 'uuid') or not orden.uuid:
            orden.uuid = str(uuid.uuid4())
            orden.save(update_fields=['uuid'])
        
        # Generar QR de validación
        qr_base64 = generar_qr_validacion(str(orden.uuid), 'laboratorio')
        
        # Integridad forense: usar snapshot de paciente al momento de la orden si existe
        paciente_obj = orden.paciente
        paciente_nombre_display = getattr(orden, 'paciente_nombre_snapshot', None) or (paciente_obj.nombre_completo if paciente_obj else '')
        paciente_edad_display = getattr(orden, 'paciente_edad_snapshot', None)
        if paciente_edad_display is None and paciente_obj:
            paciente_edad_display = getattr(paciente_obj, 'edad', None)
        paciente_sexo_display = getattr(orden, 'paciente_sexo_snapshot', None) or (getattr(paciente_obj, 'sexo', '') if paciente_obj else '')
        
        # Preparar contexto
        context = {
            'orden': orden,
            'paciente': paciente_obj,
            'paciente_nombre_display': paciente_nombre_display,
            'paciente_edad_display': paciente_edad_display,
            'paciente_sexo_display': paciente_sexo_display,
            'resultados': resultados,
            'qr_code': qr_base64,
            'fecha_generacion': timezone.localtime(timezone.now()),
            'empresa': empresa,
            'empresa_logo_uri': _empresa_logo_uri_para_weasyprint(empresa),
            'medico_solicitante': getattr(orden, 'medico', None),
            'quimico_responsable': getattr(orden, 'quimico_responsable', None),
        }
        
        # Agregar firma del químico si existe
        if hasattr(orden, 'quimico_responsable') and orden.quimico_responsable:
            quimico = orden.quimico_responsable
            if hasattr(quimico, 'firma_digital') and quimico.firma_digital:
                try:
                    with quimico.firma_digital.open('rb') as f:
                        firma_base64 = base64.b64encode(f.read()).decode()
                    context['firma_quimico_base64'] = firma_base64
                except Exception as e:
                    logger.warning(f"No se pudo cargar firma del químico: {e}")
                    context['firma_quimico_base64'] = None
            else:
                context['firma_quimico_base64'] = None
        else:
            context['firma_quimico_base64'] = None
        
        # Generar PDF
        pdf_bytes = render_to_pdf('pdfs/resultado_lab_print.html', context)
        
        logger.info(f"✓ PDF de resultados generado: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Error al generar PDF de resultados: {e}", exc_info=True)
        raise


# ==============================================================================
# FUNCIÓN AUXILIAR: GUARDAR PDF EN MODELO
# ==============================================================================

def guardar_pdf_en_modelo(pdf_bytes: bytes, instancia, campo_nombre: str, nombre_archivo: str):
    """
    Guarda el PDF en un campo FileField del modelo y dispara la subida a Drive.
    
    Args:
        pdf_bytes: Contenido del PDF
        instancia: Instancia del modelo
        campo_nombre: Nombre del campo FileField (ej: 'archivo_receta')
        nombre_archivo: Nombre del archivo (ej: 'receta_123.pdf')
        
    Ejemplo:
        guardar_pdf_en_modelo(
            pdf_bytes,
            receta,
            'archivo_receta',
            f'receta_{receta.folio}.pdf'
        )
    """
    try:
        # Crear ContentFile
        pdf_file = ContentFile(pdf_bytes)
        
        # Obtener el campo
        campo = getattr(instancia, campo_nombre)
        
        # Guardar (esto dispara la subida a Google Drive)
        campo.save(nombre_archivo, pdf_file, save=True)
        
        logger.info(f"✓ PDF guardado en {campo_nombre}: {nombre_archivo}")
        logger.info(f"   URL: {campo.url if campo else 'N/A'}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error al guardar PDF en modelo: {e}", exc_info=True)
        return False


# ==============================================================================
# FUNCIÓN DE PRUEBA
# ==============================================================================

def test_pdf_generation():
    """
    Prueba la generación de PDF con un template simple.
    """
    try:
        if not WEASYPRINT_AVAILABLE:
            print("❌ WeasyPrint no está instalado")
            return False
        
        # Template de prueba
        html_test = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @page { size: Letter; margin: 2cm; }
                body { font-family: Arial; }
                h1 { color: #dc3545; }
            </style>
        </head>
        <body>
            <h1>PRISLAB V5.0</h1>
            <p>PDF de prueba generado correctamente.</p>
            <p>Fecha: {{ fecha }}</p>
        </body>
        </html>
        """
        
        # Renderizar
        from django.template import Template, Context
        template = Template(html_test)
        html_string = template.render(Context({'fecha': timezone.localtime(timezone.now())}))
        
        # Generar PDF
        html = HTML(string=html_string)
        pdf_bytes = html.write_pdf()
        
        # Guardar en archivo temporal (autoeliminado al salir)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=True) as f:
            f.write(pdf_bytes)
            f.flush()
            print(f"✅ PDF de prueba generado: {len(pdf_bytes)} bytes")
            print("   Guardado temporalmente en: %s" % f.name)
        return True
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_pdf_generation (pdf_generator.py)")
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    print("Probando generación de PDF...")
    test_pdf_generation()


# =============================================================================
# BLINDAJE v2.0 — Generación de PDF para Notas Selladas
# =============================================================================

def generar_pdf_nota_sellada(nota_soap, sello, expediente_sha):
    """
    Genera un PDF firmado de una nota SOAP sellada (Blindaje v2.0).
    
    Args:
        nota_soap: Instancia de NotaClinicaSOAP
        sello: Instancia de NotaClinicaSellar
        expediente_sha: Instancia de ExpedienteNotaSHA
    
    Returns:
        str: Ruta del archivo PDF generado
    """
    import hashlib
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    
    try:
        # Datos para el template
        context = {
            'nota': nota_soap,
            'sello': sello,
            'expediente': expediente_sha,
            'paciente': nota_soap.paciente,
            'medico': nota_soap.medico,
            'hash_corto': expediente_sha.hash_sha256[:32],
            'fecha_generacion': timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S'),
            'qr_url': sello.qr_verificacion,
            'token_corto': str(sello.token_verificacion)[:16],
        }
        
        # Renderizar HTML
        html_string = render_to_string('core/expedientes/nota_sellada.html', context)
        
        # Generar PDF con WeasyPrint
        if not WEASYPRINT_AVAILABLE:
            raise ImportError("WeasyPrint no está instalado")
        
        html = HTML(string=html_string)
        pdf_bytes = html.write_pdf()
        
        # Calcular hash del PDF
        hash_pdf = hashlib.sha256(pdf_bytes).hexdigest()
        
        # Guardar archivo
        filename = f"expedientes/pdf_firmados/{timezone.localtime(timezone.now()).year}/{timezone.localtime(timezone.now()).month:02d}/{sello.folio_unico}_{hash_pdf[:8]}.pdf"
        path = default_storage.save(filename, ContentFile(pdf_bytes))
        
        logger.info(f"[PDF-BLINDAJE] Generado PDF firmado: {path} hash={hash_pdf[:16]}...")
        
        return path
        
    except Exception as e:
        logger.error(f"[PDF-BLINDAJE] Error generando PDF: {e}", exc_info=True)
        raise