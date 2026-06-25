"""
VISTAS PDF DUALES - CONSULTORIO MÉDICO
Sistema de generación de PDFs con dos enfoques:
1. PDF PARA PACIENTE: Receta limpia y profesional
2. PDF FORENSE: Expediente completo con trazabilidad
"""
from datetime import datetime
from django.utils import timezone
from io import BytesIO

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required

from core.utils.empresa_request import empresa_efectiva_request

from reportlab.lib.pagesizes import letter  # US Letter: 8.5" x 11" (215.9mm x 279.4mm)
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, Frame, PageTemplate
)
from reportlab.pdfgen import canvas

import qrcode
from PIL import Image as PILImage

from core.models import ConsultaMedica, Empresa, FirmaDigital


# ==============================================================================
# CONFIGURACIÓN DE DIMENSIONES - TAMAÑO CARTA (US LETTER)
# ==============================================================================
# Dimensiones exactas: 215.9mm x 279.4mm (8.5" x 11")
# Márgenes calibrados para impresión estándar en México
PAGE_SIZE = letter  # (612 points x 792 points)
MARGIN_TOP = 10 * mm      # Margen superior: 10mm
MARGIN_BOTTOM = 10 * mm   # Margen inferior: 10mm
MARGIN_LEFT = 15 * mm     # Margen izquierdo: 15mm (para encuadernado)
MARGIN_RIGHT = 10 * mm    # Margen derecho: 10mm


# ==============================================================================
# PDF TIPO A: RECETA PARA PACIENTE (LIMPIO Y PROFESIONAL)
# ==============================================================================

@login_required
def imprimir_receta_paciente(request, consulta_id):
    """
    PDF PROFESIONAL estilo PRISLAB (formato receta Monserrat).
    Formato limpio y profesional para el paciente.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Empresa no disponible.")
    consulta = get_object_or_404(ConsultaMedica, id=consulta_id, empresa=empresa)
    
    # Crear respuesta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="receta_{consulta.folio_consulta}.pdf"'
    
    # Crear documento PDF con dimensiones exactas TAMAÑO CARTA
    # US Letter: 215.9mm x 279.4mm (8.5" x 11")
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=PAGE_SIZE,           # Tamaño Carta (letter)
        topMargin=MARGIN_TOP,         # 10mm
        bottomMargin=MARGIN_BOTTOM,   # 10mm
        leftMargin=MARGIN_LEFT,       # 15mm (espacio para encuadernado)
        rightMargin=MARGIN_RIGHT      # 10mm
    )
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    style_titulo = ParagraphStyle(
        'Titulo',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#007bff'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    style_subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#6c757d'),
        spaceAfter=6
    )
    
    style_normal = styles['Normal']
    style_normal.fontSize = 10
    
    # ========== ENCABEZADO ==========
    elements.append(Paragraph(empresa.nombre.upper(), style_titulo))
    elements.append(Paragraph(f"{empresa.direccion}", ParagraphStyle('direccion', parent=style_normal, alignment=TA_CENTER, fontSize=9)))
    if hasattr(empresa, 'telefono'):
        elements.append(Paragraph(f"Tel: {empresa.telefono}", ParagraphStyle('telefono', parent=style_normal, alignment=TA_CENTER, fontSize=9)))
    elements.append(Spacer(1, 0.5*cm))
    
    # Línea separadora
    elements.append(Paragraph('<para borderWidth="1" borderColor="#007bff"></para>', style_normal))
    elements.append(Spacer(1, 0.3*cm))
    
    # ========== INFORMACIÓN DEL PACIENTE ==========
    elements.append(Paragraph("<b>DATOS DEL PACIENTE</b>", style_subtitulo))
    paciente = consulta.paciente
    medico = consulta.medico
    edad_str = (paciente.edad if paciente and paciente.edad is not None else '—')
    try:
        sexo_str = paciente.get_sexo_display() if (paciente and hasattr(paciente, 'get_sexo_display')) else '—'
    except Exception:
        sexo_str = '—'
    fecha_consulta_str = consulta.fecha_consulta.strftime('%d/%m/%Y %H:%M') if consulta.fecha_consulta else '—'
    datos_paciente = [
        [f"<b>Nombre:</b> {(paciente.nombre_completo if paciente else '—')}", f"<b>Folio:</b> {consulta.folio_consulta or '—'}"],
        [f"<b>Edad:</b> {edad_str} años", f"<b>Fecha:</b> {fecha_consulta_str}"],
        [f"<b>Sexo:</b> {sexo_str}", f"<b>Médico:</b> Dr. {(medico.nombre_completo if medico else '—')}"],
    ]
    
    tabla_paciente = Table(datos_paciente, colWidths=[9*cm, 9*cm])
    tabla_paciente.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(tabla_paciente)
    elements.append(Spacer(1, 0.5*cm))
    
    # ========== SIGNOS VITALES (PÚBLICOS) ==========
    if consulta.signos_vitales:
        elements.append(Paragraph("<b>SIGNOS VITALES</b>", style_subtitulo))
        sv = consulta.signos_vitales
        pa_s, pa_d = getattr(sv, 'presion_arterial_sistolica', None), getattr(sv, 'presion_arterial_diastolica', None)
        pa = f"{pa_s}/{pa_d}" if (pa_s is not None and pa_d is not None) else "—/—"
        imc_val = getattr(sv, 'imc', None)
        imc_str = f"{imc_val:.1f}" if imc_val is not None else "—"
        signos_data = [
            ["PA", "FC", "FR", "Temp", "Peso", "Talla", "IMC"],
            [
                pa,
                str(sv.frecuencia_cardiaca) if getattr(sv, 'frecuencia_cardiaca', None) is not None else "—",
                str(sv.frecuencia_respiratoria) if getattr(sv, 'frecuencia_respiratoria', None) is not None else "—",
                f"{sv.temperatura}°C" if getattr(sv, 'temperatura', None) is not None else "—",
                f"{sv.peso} kg" if getattr(sv, 'peso', None) is not None else "—",
                f"{sv.talla} m" if getattr(sv, 'talla', None) is not None else "—",
                imc_str,
            ]
        ]
        
        tabla_signos = Table(signos_data, colWidths=[2.5*cm]*7)
        tabla_signos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(tabla_signos)
        elements.append(Spacer(1, 0.5*cm))
    
    # ========== DIAGNÓSTICO ==========
    elements.append(Paragraph("<b>DIAGNÓSTICO</b>", style_subtitulo))
    elements.append(Paragraph(consulta.diagnostico_principal or 'Sin diagnóstico', style_normal))
    if consulta.diagnostico_cie10:
        elements.append(Paragraph(f"<b>CIE-10:</b> {consulta.diagnostico_cie10}", style_normal))
    elements.append(Spacer(1, 0.5*cm))
    
    # ========== PLAN DE TRATAMIENTO (RECETA) ==========
    elements.append(Paragraph("<b>TRATAMIENTO INDICADO</b>", style_subtitulo))
    
    # Rx estilizado
    elements.append(Paragraph(f'<font size="24" color="#007bff"><b>Rx</b></font>', style_normal))
    elements.append(Spacer(1, 0.2*cm))
    
    tratamiento_parrafos = (consulta.plan_tratamiento or '').split('\n')
    for parrafo in tratamiento_parrafos:
        if parrafo.strip():
            elements.append(Paragraph(f"• {parrafo.strip()}", style_normal))
    
    elements.append(Spacer(1, 1*cm))
    
    # ========== FIRMA MÉDICA DIGITAL ==========
    elements.append(Spacer(1, 0.5*cm))
    
    # Intentar obtener la firma digital del médico
    # ConsultaMedica.medico es modelo Medico, FirmaDigital.medico es Usuario
    firma_imagen_ok = False
    try:
        firma_obj = None
        medico_consulta = consulta.medico
        empresa_pdf = getattr(consulta, 'empresa', None)
        if hasattr(medico_consulta, 'cedula_profesional') and medico_consulta.cedula_profesional:
            _f_q = FirmaDigital.objects.filter(
                cedula_profesional=medico_consulta.cedula_profesional,
                activa=True,
            )
            if empresa_pdf:
                _f_q = _f_q.filter(medico__empresa=empresa_pdf)
            firma_obj = _f_q.first()
        # Fallback solo dentro de la misma empresa (no cross-tenant)
        if not firma_obj and empresa_pdf:
            firma_obj = FirmaDigital.objects.filter(
                medico__empresa=empresa_pdf, activa=True
            ).first()
        
        if firma_obj and firma_obj.imagen_firma:
            try:
                import os as _os
                firma_path = firma_obj.imagen_firma.path
                if _os.path.exists(firma_path):
                    # Obtener proporciones reales
                    pil_img = PILImage.open(firma_path)
                    img_w, img_h = pil_img.size
                    max_width = 5 * cm
                    aspect = img_h / img_w
                    fw = max_width
                    fh = max_width * aspect
                    if fh > 2.5 * cm:
                        fh = 2.5 * cm
                        fw = fh / aspect
                    
                    img_firma = Image(firma_path, width=fw, height=fh)
                    tabla_img = Table([[img_firma]], colWidths=[15*cm])
                    tabla_img.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), -6),
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ]))
                    elements.append(tabla_img)
                    firma_imagen_ok = True
            except Exception:
                pass
    except Exception:
        pass
    
    if not firma_imagen_ok:
        elements.append(Spacer(1, 2*cm))
    
    firma_data = [
        ["_" * 60],
        [f"Dr. {consulta.medico.nombre_completo}"],
        [f"Cédula Profesional: {consulta.medico.cedula_profesional}"]
    ]
    
    tabla_firma = Table(firma_data, colWidths=[15*cm])
    tabla_firma.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 2), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(tabla_firma)
    
    # ========== PIE DE PÁGINA ==========
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(
        f'<font size="7" color="grey">Impreso el {timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M")} | {consulta.folio_consulta}</font>',
        ParagraphStyle('footer', parent=style_normal, alignment=TA_CENTER, fontSize=7, textColor=colors.grey)
    ))
    
    # Construir PDF
    doc.build(elements)
    
    # Obtener PDF del buffer
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response


# ==============================================================================
# PDF TIPO B: EXPEDIENTE FORENSE (COMPLETO Y TRAZABLE)
# ==============================================================================

@login_required
@permission_required('core.ver_historia_completa', raise_exception=True)
def imprimir_expediente_forense(request, consulta_id):
    """
    PDF forense para archivo clínico.
    Contiene: SOAP completo, Transcripción de audio, Tiempos, Notas privadas,
    Historial de cambios, Firma digital, Hash de integridad.
    """
    empresa = empresa_efectiva_request(request)  # canónico: request.empresa_actual ∥ user.empresa
    if not empresa:
        from django.http import HttpResponse
        return HttpResponse('Usuario sin empresa asignada', status=403)
    consulta = get_object_or_404(ConsultaMedica, id=consulta_id, empresa=empresa)
    
    # Crear respuesta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="expediente_forense_{consulta.folio_consulta}.pdf"'
    
    # Crear documento PDF con dimensiones exactas TAMAÑO CARTA
    # US Letter: 215.9mm x 279.4mm (8.5" x 11")
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=PAGE_SIZE,           # Tamaño Carta (letter)
        topMargin=MARGIN_TOP,         # 10mm
        bottomMargin=MARGIN_BOTTOM,   # 10mm
        leftMargin=MARGIN_LEFT,       # 15mm (espacio para encuadernado)
        rightMargin=MARGIN_RIGHT      # 10mm
    )
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    style_titulo_forense = ParagraphStyle(
        'TituloForense',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#dc3545'),
        alignment=TA_CENTER,
        spaceAfter=10,
        spaceBefore=10,
        borderWidth=2,
        borderColor=colors.HexColor('#dc3545'),
        borderPadding=10
    )
    
    style_seccion = ParagraphStyle(
        'Seccion',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#343a40'),
        spaceAfter=8,
        spaceBefore=8,
        borderWidth=1,
        borderColor=colors.HexColor('#6c757d'),
        borderPadding=5,
        backColor=colors.HexColor('#f8f9fa')
    )
    
    style_normal = styles['Normal']
    style_normal.fontSize = 9
    
    style_codigo = ParagraphStyle(
        'Codigo',
        parent=style_normal,
        fontName='Courier',
        fontSize=8,
        leftIndent=10,
        textColor=colors.HexColor('#6c757d'),
        backColor=colors.HexColor('#f8f9fa')
    )
    
    # ========== MARCA DE AGUA "CONFIDENCIAL" ==========
    elements.append(Paragraph(
        '<font size="24" color="red"><b>⚠️ DOCUMENTO CONFIDENCIAL - USO EXCLUSIVO MÉDICO-LEGAL</b></font>',
        ParagraphStyle('confidencial', parent=style_titulo_forense, fontSize=14, textColor=colors.red)
    ))
    elements.append(Spacer(1, 0.5*cm))
    
    # ========== INFORMACIÓN DE CONSULTA ==========
    elements.append(Paragraph("<b>EXPEDIENTE FORENSE - CONSULTA MÉDICA</b>", style_seccion))
    
    fecha_consulta_f = consulta.fecha_consulta.strftime('%d/%m/%Y %H:%M:%S') if consulta.fecha_consulta else 'N/A'
    edad_forense = (consulta.paciente.edad if consulta.paciente and consulta.paciente.edad is not None else '—')
    cedula_forense = (consulta.medico.cedula_profesional or '—') if consulta.medico else '—'
    info_consulta = [
        [f"<b>Folio:</b> {consulta.folio_consulta or '—'}", f"<b>Tipo:</b> {consulta.get_tipo_consulta_display()}"],
        [f"<b>Fecha Consulta:</b> {fecha_consulta_f}", f"<b>Estado:</b> {consulta.get_estado_display()}"],
        [f"<b>Paciente:</b> {consulta.paciente.nombre_completo if consulta.paciente else '—'}", f"<b>Edad:</b> {edad_forense} años"],
        [f"<b>Médico:</b> Dr. {(consulta.medico.nombre_completo if consulta.medico else '—')}", f"<b>Cédula:</b> {cedula_forense}"],
    ]
    
    tabla_info = Table(info_consulta, colWidths=[9*cm, 9*cm])
    tabla_info.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(tabla_info)
    elements.append(Spacer(1, 0.4*cm))
    
    # ========== SIGNOS VITALES COMPLETOS ==========
    if consulta.signos_vitales:
        elements.append(Paragraph("<b>SIGNOS VITALES</b>", style_seccion))
        sv = consulta.signos_vitales
        
        pa_s, pa_d = getattr(sv, 'presion_arterial_sistolica', None), getattr(sv, 'presion_arterial_diastolica', None)
        pa_str = f"{pa_s}/{pa_d}" if (pa_s is not None and pa_d is not None) else "—/—"
        imc_v = getattr(sv, 'imc', None)
        imc_f = f"{imc_v:.2f}" if imc_v is not None else "—"
        clas_imc = getattr(sv, 'clasificacion_imc', None) or "—"
        sv_completo = f"""
        PA: {pa_str} mmHg | FC: {sv.frecuencia_cardiaca or '—'} lat/min | FR: {sv.frecuencia_respiratoria or '—'} resp/min |
        Temp: {sv.temperatura or '—'}°C | Peso: {sv.peso or '—'} kg | Talla: {sv.talla or '—'} m | IMC: {imc_f} ({clas_imc})
        """
        if getattr(sv, 'saturacion_oxigeno', None):
            sv_completo += f" | SpO₂: {sv.saturacion_oxigeno}%"
        if getattr(sv, 'glucosa_capilar', None):
            sv_completo += f" | Glucosa: {sv.glucosa_capilar} mg/dL"
        elements.append(Paragraph(sv_completo.strip(), style_normal))
        reg_por = getattr(getattr(sv, 'registrado_por', None), 'username', None) or 'Sistema'
        fecha_reg = sv.fecha_registro.strftime('%d/%m/%Y %H:%M') if getattr(sv, 'fecha_registro', None) else 'N/A'
        elements.append(Paragraph(f"<i>Registrado por: {reg_por} el {fecha_reg}</i>",
                                 ParagraphStyle('metadata', parent=style_normal, fontSize=7, textColor=colors.grey)))
        elements.append(Spacer(1, 0.3*cm))
    
    # ========== FORMATO SOAP COMPLETO ==========
    elements.append(Paragraph("<b>FORMATO SOAP (COMPLETO)</b>", style_seccion))
    
    # S - SUBJETIVO
    elements.append(Paragraph("<b>S - SUBJETIVO</b>", ParagraphStyle('soap', parent=style_normal, fontSize=10, textColor=colors.HexColor('#007bff'))))
    elements.append(Paragraph(f"<b>Motivo:</b> {consulta.motivo_consulta or '—'}", style_normal))
    elements.append(Paragraph(f"<b>Padecimiento:</b> {consulta.padecimiento_actual or '—'}", style_normal))
    elements.append(Spacer(1, 0.2*cm))
    # O - OBJETIVO
    elements.append(Paragraph("<b>O - OBJETIVO</b>", ParagraphStyle('soap', parent=style_normal, fontSize=10, textColor=colors.HexColor('#28a745'))))
    elements.append(Paragraph(f"<b>Exploración Física:</b> {consulta.exploracion_fisica or '—'}", style_normal))
    elements.append(Spacer(1, 0.2*cm))
    # A - ASSESSMENT
    elements.append(Paragraph("<b>A - ASSESSMENT</b>", ParagraphStyle('soap', parent=style_normal, fontSize=10, textColor=colors.HexColor('#ffc107'))))
    elements.append(Paragraph(f"<b>Diagnóstico Principal:</b> {consulta.diagnostico_principal or '—'}", style_normal))
    if consulta.diagnostico_cie10:
        elements.append(Paragraph(f"<b>CIE-10:</b> {consulta.diagnostico_cie10}", style_normal))
    if consulta.diagnosticos_secundarios:
        elements.append(Paragraph(f"<b>Secundarios:</b> {consulta.diagnosticos_secundarios}", style_normal))
    elements.append(Spacer(1, 0.2*cm))
    # P - PLAN
    elements.append(Paragraph("<b>P - PLAN</b>", ParagraphStyle('soap', parent=style_normal, fontSize=10, textColor=colors.HexColor('#dc3545'))))
    elements.append(Paragraph(f"<b>Tratamiento:</b> {consulta.plan_tratamiento or '—'}", style_normal))
    if consulta.estudios_solicitados:
        elements.append(Paragraph(f"<b>Estudios:</b> {consulta.estudios_solicitados}", style_normal))
    try:
        pronostico_display = consulta.get_pronostico_display() if getattr(consulta, 'pronostico', None) else '—'
    except Exception:
        pronostico_display = '—'
    elements.append(Paragraph(f"<b>Pronóstico:</b> {pronostico_display}", style_normal))
    elements.append(Spacer(1, 0.4*cm))
    
    # ========== TRANSCRIPCIÓN DE AUDIO (SI EXISTE) ==========
    if hasattr(consulta, 'audio_sesion') and consulta.audio_sesion:
        elements.append(PageBreak())
        elements.append(Paragraph("<b>🔴 TRANSCRIPCIÓN DE AUDIO (CAJA NEGRA)</b>", style_seccion))
        
        audio = consulta.audio_sesion
        elements.append(Paragraph(f"<b>Duración:</b> {audio.duracion_formato}", style_normal))
        elements.append(Paragraph(f"<b>Hash SHA256:</b> <font face='Courier' size='7'>{audio.hash_sha256}</font>", style_codigo))
        elements.append(Paragraph(f"<b>Timestamps:</b> {audio.timestamp_inicio.strftime('%H:%M:%S')} - {audio.timestamp_fin.strftime('%H:%M:%S')}", style_normal))
        elements.append(Spacer(1, 0.2*cm))
        
        if audio.transcripcion_bruta:
            elements.append(Paragraph("<b>Transcripción Automática:</b>", style_normal))
            elements.append(Paragraph(audio.transcripcion_bruta, style_codigo))
        else:
            elements.append(Paragraph("<i>Transcripción pendiente de procesamiento</i>", 
                                     ParagraphStyle('pending', parent=style_normal, fontSize=8, textColor=colors.grey, fontName='Helvetica-Oblique')))
        
        elements.append(Spacer(1, 0.3*cm))
    
    # ========== HISTORIAL DE CAMBIOS (SI EXISTE) ==========
    if consulta.historial_cambios.exists():
        elements.append(PageBreak())
        elements.append(Paragraph("<b>📋 HISTORIAL DE MODIFICACIONES</b>", style_seccion))
        
        for cambio in consulta.historial_cambios.all()[:10]:  # Últimos 10 cambios
            elements.append(Paragraph(
                f"<b>{cambio.timestamp.strftime('%d/%m/%Y %H:%M')}</b> - {getattr(cambio.usuario_modificador, 'username', 'N/A')} modificó <b>{cambio.campo_modificado}</b>",
                style_normal
            ))
            elements.append(Paragraph(f"<i>Razón:</i> {cambio.razon_cambio}", style_codigo))
            elements.append(Spacer(1, 0.1*cm))
    
    # ========== FIRMA DIGITAL Y HASH ==========
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("<b>VALIDACIÓN FORENSE</b>", style_seccion))
    
    # Insertar firma digital del médico si existe
    try:
        firma_forense = None
        empresa_forense = getattr(consulta, 'empresa', None)
        if hasattr(consulta.medico, 'cedula_profesional') and consulta.medico.cedula_profesional:
            _fq = FirmaDigital.objects.filter(
                cedula_profesional=consulta.medico.cedula_profesional,
                activa=True,
            )
            if empresa_forense:
                _fq = _fq.filter(medico__empresa=empresa_forense)
            firma_forense = _fq.first()
        if not firma_forense and empresa_forense:
            firma_forense = FirmaDigital.objects.filter(
                medico__empresa=empresa_forense, activa=True
            ).first()
        if firma_forense and firma_forense.imagen_firma:
            try:
                img_firma_f = Image(
                    firma_forense.imagen_firma.path,
                    width=4*cm,
                    height=2*cm
                )
                tabla_firma_f = Table(
                    [[img_firma_f, f"Dr. {consulta.medico.nombre_completo}\nCédula: {consulta.medico.cedula_profesional}"]],
                    colWidths=[5*cm, 13*cm]
                )
                tabla_firma_f.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (1, 0), (1, 0), 9),
                ]))
                elements.append(tabla_firma_f)
                elements.append(Spacer(1, 0.3*cm))
            except Exception:
                pass
    except Exception:
        pass
    
    elements.append(Paragraph(f"<b>Documento generado:</b> {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S')}", style_normal))
    elements.append(Paragraph(f"<b>Generado por:</b> {request.user.get_full_name()}", style_normal))
    
    # Hash de integridad del documento
    import hashlib
    hash_doc = hashlib.sha256(f"{consulta.id}{consulta.folio_consulta}{timezone.localtime(timezone.now())}".encode()).hexdigest()
    elements.append(Paragraph(f"<b>Hash del documento:</b> <font face='Courier' size='6'>{hash_doc}</font>", style_codigo))
    
    # Construir PDF
    doc.build(elements)
    
    # Obtener PDF del buffer
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response
