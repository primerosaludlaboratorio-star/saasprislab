"""
core/views/medico/receta.py
Ver receta, generar PDF con ReportLab, QR de validación.
"""
import base64
import hashlib
import io
import json
from datetime import date

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.models import Receta
from core.utils.auditoria_helper import crear_log_auditoria, calcular_hash_auditoria
from core.utils.empresa_request import empresa_efectiva_request
import logging


@login_required
def ver_receta_medica(request, receta_id):
    """Ver receta médica 4.0 con QR de validación."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    receta = get_object_or_404(Receta, id=receta_id, empresa=empresa)
    
    return render(request, 'core/ver_receta_medica.html', {
        'empresa': empresa,
        'receta': receta
    })


@login_required
def generar_pdf_receta(request, receta_id):
    """Genera PDF de receta médica 4.0 con QR de validación."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        return HttpResponse('Usuario sin empresa asignada', status=403)
    receta = get_object_or_404(Receta, id=receta_id, empresa=empresa)

    try:
        receta.validar_items_antes_de_emitir()
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en generar_pdf_receta (receta.py)")
        messages.error(request, str(e))
        return redirect('ver_receta_medica', receta_id=receta.id)

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    color_primario = empresa.color_primario or '#D9230F'
    
    p.setFillColor(color_primario)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 50, "RECETA MÉDICA")
    
    p.setFont("Helvetica", 10)
    p.setFillColor("black")
    y = height - 100
    
    if receta.paciente:
        p.drawString(50, y, f"Paciente: {receta.paciente.nombre_completo}")
        y -= 20
        if receta.paciente.fecha_nacimiento:
            edad = (date.today() - receta.paciente.fecha_nacimiento).days // 365
            p.drawString(50, y, f"Edad: {edad} años")
            y -= 20
        if receta.paciente.telefono:
            p.drawString(50, y, f"Teléfono: {receta.paciente.telefono}")
            y -= 20
    
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Signos Vitales:")
    p.setFont("Helvetica", 10)
    y -= 20
    
    if receta.presion_arterial_sistolica and receta.presion_arterial_diastolica:
        p.drawString(50, y, f"PA: {receta.presion_arterial_sistolica}/{receta.presion_arterial_diastolica} mmHg")
        y -= 15
    if receta.frecuencia_cardiaca:
        p.drawString(50, y, f"FC: {receta.frecuencia_cardiaca} lat/min")
        y -= 15
    if receta.temperatura:
        p.drawString(50, y, f"Temp: {receta.temperatura}°C")
        y -= 15
    if receta.peso and receta.talla:
        imc_txt = f"{receta.imc:.2f}" if receta.imc is not None else "N/A"
        p.drawString(50, y, f"Peso: {receta.peso} kg | Talla: {receta.talla} m | IMC: {imc_txt}")
        y -= 15
    
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Diagnóstico:")
    p.setFont("Helvetica", 10)
    y -= 20
    p.drawString(50, y, receta.diagnostico_principal)
    y -= 15
    if receta.diagnostico_secundario:
        p.drawString(50, y, receta.diagnostico_secundario)
        y -= 15
    
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "MEDICAMENTOS PRESCRITOS:")
    p.setFont("Helvetica", 10)
    y -= 25
    
    indicaciones_lines = receta.indicaciones.split('\n')
    medicamento_num = 1
    
    for line in indicaciones_lines:
        if not line.strip():
            continue
        if y < 120:
            p.showPage()
            y = height - 50
        
        line_clean = line.strip()
        
        if ' - ' in line_clean:
            partes = line_clean.split(' - ')
            if len(partes) >= 2:
                medicamento = partes[0].strip()
                dosis = partes[1].strip() if len(partes) > 1 else ''
                frecuencia = partes[2].strip() if len(partes) > 2 else ''
                p.setFont("Helvetica-Bold", 10)
                p.drawString(50, y, f"{medicamento_num}. {medicamento}")
                y -= 16
                p.setFont("Helvetica", 9)
                if dosis:
                    p.drawString(70, y, f"• Dosis: {dosis}")
                    y -= 14
                if frecuencia:
                    p.drawString(70, y, f"• Frecuencia: {frecuencia}")
                    y -= 14
                medicamento_num += 1
                y -= 5
                continue
        
        if ',' in line_clean and line_clean.count(',') >= 2:
            partes = [pt.strip() for pt in line_clean.split(',')]
            if len(partes) >= 2:
                medicamento = partes[0]
                dosis = partes[1] if len(partes) > 1 else ''
                frecuencia = partes[2] if len(partes) > 2 else ''
                p.setFont("Helvetica-Bold", 10)
                p.drawString(50, y, f"{medicamento_num}. {medicamento}")
                y -= 16
                p.setFont("Helvetica", 9)
                if dosis:
                    p.drawString(70, y, f"• Dosis: {dosis}")
                    y -= 14
                if frecuencia:
                    p.drawString(70, y, f"• Frecuencia: {frecuencia}")
                    y -= 14
                medicamento_num += 1
                y -= 5
                continue
        
        if ':' in line_clean and ' - ' in line_clean:
            partes_colon = line_clean.split(':', 1)
            if len(partes_colon) == 2:
                medicamento = partes_colon[0].strip()
                resto = partes_colon[1].strip()
                if ' - ' in resto:
                    partes_dash = resto.split(' - ', 1)
                    dosis = partes_dash[0].strip()
                    frecuencia = partes_dash[1].strip() if len(partes_dash) > 1 else ''
                else:
                    dosis = resto
                    frecuencia = ''
                p.setFont("Helvetica-Bold", 10)
                p.drawString(50, y, f"{medicamento_num}. {medicamento}")
                y -= 16
                p.setFont("Helvetica", 9)
                if dosis:
                    p.drawString(70, y, f"• Dosis: {dosis}")
                    y -= 14
                if frecuencia:
                    p.drawString(70, y, f"• Frecuencia: {frecuencia}")
                    y -= 14
                medicamento_num += 1
                y -= 5
                continue
        
        if line_clean[0].isdigit() and (line_clean[1] == '.' or line_clean[1:3] == '. '):
            line_clean = line_clean.split('.', 1)[1].strip() if '.' in line_clean else line_clean
        
        p.setFont("Helvetica", 10)
        if len(line_clean) > 75:
            palabras = line_clean.split()
            linea_actual = f"{medicamento_num}. "
            for palabra in palabras:
                if len(linea_actual + palabra) > 75:
                    p.drawString(50, y, linea_actual)
                    y -= 15
                    linea_actual = "   " + palabra + " "
                else:
                    linea_actual += palabra + " "
            if linea_actual.strip():
                p.drawString(50, y, linea_actual)
                y -= 15
        else:
            p.drawString(50, y, f"{medicamento_num}. {line_clean}")
            y -= 15
        
        medicamento_num += 1
        y -= 5
        
        if medicamento_num > 25:
            break
    
    if y < 250:
        p.showPage()
        y = height - 50
    
    y -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "DATOS DEL MÉDICO:")
    p.setFont("Helvetica", 10)
    y -= 20
    
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, f"Dr. {receta.medico_nombre_completo}")
    y -= 18
    
    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Cédula Profesional: {receta.medico_cedula}")
    y -= 18
    
    medico_universidad = getattr(receta, 'medico_universidad', None)
    if medico_universidad:
        p.drawString(50, y, f"Universidad: {medico_universidad}")
        y -= 18
    else:
        p.setFont("Helvetica-Oblique", 9)
        p.setFillColor("gray")
        p.drawString(50, y, "Universidad: [No especificada]")
        p.setFillColor("black")
        y -= 18
    
    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Especialidad: {receta.medico_especialidad}")
    y -= 30
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Firma del Médico:")
    y -= 5
    
    firma_x = 50
    firma_y = y - 50
    firma_width = 150
    firma_height = 50
    p.rect(firma_x, firma_y, firma_width, firma_height)
    
    if receta.medico_firma_digital:
        try:
            import os
            from django.conf import settings
            from reportlab.lib.utils import ImageReader as IR
            if hasattr(receta.medico_firma_digital, 'path'):
                firma_path = receta.medico_firma_digital.path
            else:
                firma_path = os.path.join(settings.MEDIA_ROOT, str(receta.medico_firma_digital))
            if os.path.exists(firma_path):
                firma_image = IR(firma_path)
                p.drawImage(firma_image, firma_x + 5, firma_y + 5, width=firma_width - 10, height=firma_height - 10, preserveAspectRatio=True)
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en generar_pdf_receta (receta.py)")
            p.setFont("Helvetica-Oblique", 8)
            p.setFillColor("gray")
            p.drawString(firma_x + 10, firma_y + 20, "[Firma no disponible]")
            p.setFillColor("black")
    else:
        p.setFont("Helvetica-Oblique", 8)
        p.setFillColor("gray")
        p.drawString(firma_x + 10, firma_y + 20, "[Espacio para firma]")
        p.setFillColor("black")
    
    y = firma_y - 30
    p.setFont("Helvetica-Bold", 10)
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
             'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    fecha_str = f"{receta.fecha_emision.day} de {meses[receta.fecha_emision.month - 1]} de {receta.fecha_emision.year}"
    p.drawString(50, y, f"Fecha de Emisión: {fecha_str}")
    y -= 15
    p.setFont("Helvetica", 9)
    p.drawString(50, y, f"Folio: {receta.folio_receta}")
    
    if receta.qr_verificacion:
        try:
            from reportlab.lib.utils import ImageReader as IR
            qr_image = IR(io.BytesIO(base64.b64decode(receta.qr_verificacion)))
            qr_size = 60
            qr_x = width - qr_size - 50
            qr_y = height - qr_size - 50
            p.drawImage(qr_image, qr_x, qr_y, width=qr_size, height=qr_size)
            p.setFont("Helvetica", 7)
            p.drawString(qr_x, qr_y - 15, "Validar QR")
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en generar_pdf_receta (receta.py)")
            pass
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receta_{receta.folio_receta}.pdf"'
    return response


def calcular_hash_verificacion_receta(receta):
    """Calcula hash SHA-256 para verificación de autenticidad de receta."""
    datos = {
        'folio': receta.folio_receta,
        'medico_cedula': receta.medico_cedula,
        'fecha_emision': receta.fecha_emision.isoformat(),
        'diagnostico': receta.diagnostico_principal,
        'paciente': receta.paciente.nombre_completo if receta.paciente else ''
    }
    return calcular_hash_auditoria(datos)


@login_required
def verificar_qr_receta(request):
    """API para verificar autenticidad de receta mediante QR."""
    if request.method == 'POST':
        try:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'status': 'error', 'mensaje': 'Cuerpo JSON inválido'}, status=400)
            raw_qr = data.get('qr_data') or '{}'
            if isinstance(raw_qr, str):
                try:
                    qr_data = json.loads(raw_qr)
                except json.JSONDecodeError:
                    return JsonResponse({'status': 'error', 'mensaje': 'qr_data inválido'}, status=400)
            else:
                qr_data = raw_qr if isinstance(raw_qr, dict) else {}
            
            folio = qr_data.get('folio')
            if not folio:
                return JsonResponse({'status': 'error', 'mensaje': 'Folio no válido'}, status=400)

            empresa = empresa_efectiva_request(request)
            receta = Receta.objects.filter(folio_receta=folio, empresa=empresa).first()
            if not receta:
                return JsonResponse({
                    'status': 'error',
                    'mensaje': 'Receta no encontrada',
                    'autentica': False
                })
            
            hash_calculado = calcular_hash_verificacion_receta(receta)
            hash_recibido = qr_data.get('hash')
            
            autentica = hash_calculado == hash_recibido == receta.hash_verificacion
            
            cedula_vigente = receta.cedula_vigente
            if receta.fecha_vencimiento_cedula:
                cedula_vigente = receta.fecha_vencimiento_cedula >= date.today()
            
            return JsonResponse({
                'status': 'success',
                'autentica': autentica,
                'receta': {
                    'folio': receta.folio_receta,
                    'medico': receta.medico_nombre_completo,
                    'cedula': receta.medico_cedula,
                    'fecha_emision': receta.fecha_emision.isoformat(),
                    'paciente': receta.paciente.nombre_completo if receta.paciente else 'Paciente Externo',
                    'diagnostico': receta.diagnostico_principal
                },
                'cedula_vigente': cedula_vigente,
                'fecha_vencimiento_cedula': receta.fecha_vencimiento_cedula.isoformat() if receta.fecha_vencimiento_cedula else None
            })
        
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en verificar_qr_receta (receta.py)")
            return JsonResponse({
                'status': 'error',
                'mensaje': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error'}, status=405)