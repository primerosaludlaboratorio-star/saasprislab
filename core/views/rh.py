"""
Módulo de Vistas para Recursos Humanos.
Incluye: Bitácora 39-A, evaluación de empleados, gestión de talento.
"""
import json
import hashlib
import io
from datetime import datetime, timedelta
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
import qrcode
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

from core.models import (
    Empresa, Usuario, Empleado, Bitacora39A, FirmaDigital,
    EvaluacionDesempeno, PlanDesarrollo, DetalleEvaluacion, Competencia
)
from core.utils.rh_utils import generar_pdi_automatico


@login_required
def lista_evaluaciones_39a(request):
    """Lista todas las evaluaciones 39-A."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    # Filtrar por empleado si se especifica
    empleado_id = request.GET.get('empleado_id')
    evaluaciones = Bitacora39A.objects.filter(
        empleado__empresa=empresa
    ).select_related('empleado__usuario', 'evaluador').order_by('-fecha_inicio')
    
    if empleado_id:
        evaluaciones = evaluaciones.filter(empleado_id=empleado_id)
    
    empleados = Empleado.objects.filter(empresa=empresa, activo=True).select_related('usuario')
    
    return render(request, 'core/lista_evaluaciones_39a.html', {
        'evaluaciones': evaluaciones,
        'empleados': empleados,
        'empleado_seleccionado': int(empleado_id) if empleado_id else None,
        'empresa': empresa
    })


@login_required
def crear_evaluacion_39a(request, empleado_id=None):
    """Formulario para crear una nueva evaluación 39-A."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    empleado = None
    if empleado_id:
        empleado = get_object_or_404(Empleado, id=empleado_id, empresa=empresa)
    
    empleados = Empleado.objects.filter(empresa=empresa, activo=True).select_related('usuario')
    
    # Calcular periodo semanal actual
    hoy = timezone.now().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # Lunes de la semana actual
    fin_semana = inicio_semana + timedelta(days=6)  # Domingo de la semana actual
    periodo_semanal = f"{hoy.year}-S{hoy.isocalendar()[1]:02d}"
    
    if request.method == 'POST':
        try:
            data = request.POST
            
            empleado_id_post = int(data.get('empleado'))
            empleado = get_object_or_404(Empleado, id=empleado_id_post, empresa=empresa)
            
            periodo_semanal_post = data.get('periodo_semanal', periodo_semanal)
            fecha_inicio = datetime.strptime(data.get('fecha_inicio'), '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(data.get('fecha_fin'), '%Y-%m-%d').date()
            
            # Validar que no exista ya una evaluación para este periodo
            if Bitacora39A.objects.filter(empleado=empleado, periodo_semanal=periodo_semanal_post).exists():
                return render(request, 'core/crear_evaluacion_39a.html', {
                    'empleado': empleado,
                    'empleados': empleados,
                    'periodo_semanal': periodo_semanal_post,
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                    'error': f'Ya existe una evaluación para el periodo {periodo_semanal_post}',
                    'empresa': empresa
                })
            
            # Crear evaluación
            evaluacion = Bitacora39A.objects.create(
                empleado=empleado,
                periodo_semanal=periodo_semanal_post,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                puntualidad=int(data.get('puntualidad', 0)),
                calidad_captura=int(data.get('calidad_captura', 0)),
                atencion_cliente=int(data.get('atencion_cliente', 0)),
                cumplimiento_procesos=int(data.get('cumplimiento_procesos', 0)),
                trabajo_equipo=int(data.get('trabajo_equipo', 0)),
                calificacion_general=int(data.get('calificacion_general', 0)),
                notas_objetivas=data.get('notas_objetivas', ''),
                recomendacion=data.get('recomendacion', 'PRORROGAR'),
                aptitud_medica=data.get('aptitud_medica') == 'on',
                evaluador=request.user
            )
            
            # Generar PDF firmado
            pdf_buffer, hash_pdf = generar_pdf_evaluacion_39a(evaluacion, empresa)
            
            # Guardar PDF
            from django.core.files.base import ContentFile
            evaluacion.pdf_firmado.save(
                f'evaluacion_{evaluacion.id}_{periodo_semanal_post}.pdf',
                ContentFile(pdf_buffer.getvalue()),
                save=False
            )
            evaluacion.hash_pdf = hash_pdf
            evaluacion.save()
            
            return redirect('ver_evaluacion_39a', evaluacion_id=evaluacion.id)
            
        except Exception as e:
            return render(request, 'core/crear_evaluacion_39a.html', {
                'empleado': empleado,
                'empleados': empleados,
                'periodo_semanal': periodo_semanal,
                'fecha_inicio': inicio_semana,
                'fecha_fin': fin_semana,
                'error': f'Error al crear evaluación: {str(e)}',
                'empresa': empresa
            })
    
    return render(request, 'core/crear_evaluacion_39a.html', {
        'empleado': empleado,
        'empleados': empleados,
        'periodo_semanal': periodo_semanal,
        'fecha_inicio': inicio_semana,
        'fecha_fin': fin_semana,
        'empresa': empresa
    })


@login_required
def ver_evaluacion_39a(request, evaluacion_id):
    """Ver detalles de una evaluación 39-A."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    evaluacion = get_object_or_404(
        Bitacora39A.objects.select_related('empleado__usuario', 'evaluador'),
        id=evaluacion_id,
        empleado__empresa=empresa
    )
    
    return render(request, 'core/ver_evaluacion_39a.html', {
        'evaluacion': evaluacion,
        'empresa': empresa
    })


@login_required
def descargar_pdf_evaluacion_39a(request, evaluacion_id):
    """Descargar PDF firmado de evaluación 39-A."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return HttpResponse(status=403)
    evaluacion = get_object_or_404(
        Bitacora39A.objects.select_related('empleado__usuario', 'evaluador'),
        id=evaluacion_id,
        empleado__empresa=empresa
    )
    
    if evaluacion.pdf_firmado:
        response = HttpResponse(evaluacion.pdf_firmado.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Evaluacion_39A_{evaluacion.periodo_semanal}_{evaluacion.empleado.usuario.get_full_name()}.pdf"'
        return response
    else:
        # Regenerar PDF si no existe
        pdf_buffer, hash_pdf = generar_pdf_evaluacion_39a(evaluacion, empresa)
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Evaluacion_39A_{evaluacion.periodo_semanal}_{evaluacion.empleado.usuario.get_full_name()}.pdf"'
        return response


def generar_pdf_evaluacion_39a(evaluacion, empresa):
    """Genera PDF firmado digitalmente de evaluación 39-A."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor(empresa.color_primario or '#D9230F'),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2B3A42'),
        spaceAfter=12
    )
    
    # Encabezado
    story.append(Paragraph(f"{empresa.nombre}", title_style))
    story.append(Paragraph("Bitácora de Evaluación Semanal - Art. 39-A LFT", styles['Heading2']))
    story.append(Spacer(1, 0.2*inch))
    
    # Datos del Empleado
    story.append(Paragraph("<b>DATOS DEL EMPLEADO:</b>", heading_style))
    datos_empleado = [
        ['Nombre:', evaluacion.empleado.usuario.get_full_name()],
        ['Puesto:', evaluacion.empleado.puesto],
        ['Sucursal:', evaluacion.empleado.sucursal.nombre if evaluacion.empleado.sucursal else 'N/A'],
        ['Periodo Semanal:', evaluacion.periodo_semanal],
        ['Fecha Inicio:', evaluacion.fecha_inicio.strftime('%d/%m/%Y')],
        ['Fecha Fin:', evaluacion.fecha_fin.strftime('%d/%m/%Y')],
    ]
    tabla_empleado = Table(datos_empleado, colWidths=[2*inch, 4*inch])
    tabla_empleado.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(tabla_empleado)
    story.append(Spacer(1, 0.3*inch))
    
    # 5 Métricas de Evaluación
    story.append(Paragraph("<b>MÉTRICAS DE EVALUACIÓN:</b>", heading_style))
    metricas = [
        ['Métrica', 'Calificación (0-100)'],
        ['Puntualidad', str(evaluacion.puntualidad)],
        ['Calidad de Captura', str(evaluacion.calidad_captura)],
        ['Atención al Cliente', str(evaluacion.atencion_cliente)],
        ['Cumplimiento de Procesos', str(evaluacion.cumplimiento_procesos)],
        ['Trabajo en Equipo', str(evaluacion.trabajo_equipo)],
        ['<b>Promedio General</b>', f'<b>{evaluacion.calificacion_general}</b>'],
    ]
    tabla_metricas = Table(metricas, colWidths=[4*inch, 2*inch])
    tabla_metricas.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(empresa.color_primario or '#D9230F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F5F5F5')),
    ]))
    story.append(tabla_metricas)
    story.append(Spacer(1, 0.3*inch))
    
    # Notas Objetivas
    if evaluacion.notas_objetivas:
        story.append(Paragraph("<b>NOTAS OBJETIVAS:</b>", heading_style))
        story.append(Paragraph(evaluacion.notas_objetivas, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
    
    # Recomendación y Aptitud
    story.append(Paragraph("<b>RECOMENDACIÓN Y APTITUD:</b>", heading_style))
    recomendacion_texto = dict(Bitacora39A._meta.get_field('recomendacion').choices)[evaluacion.recomendacion]
    aptitud_texto = "Sí" if evaluacion.aptitud_medica else "No"
    datos_recomendacion = [
        ['Recomendación:', recomendacion_texto],
        ['Dictamen de Aptitud Médica:', aptitud_texto],
    ]
    tabla_recomendacion = Table(datos_recomendacion, colWidths=[2*inch, 4*inch])
    tabla_recomendacion.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(tabla_recomendacion)
    story.append(Spacer(1, 0.3*inch))
    
    # Firma Digital
    story.append(Paragraph("<b>FIRMA DIGITAL:</b>", heading_style))
    datos_firma = [
        ['Evaluador:', evaluacion.evaluador.get_full_name() if evaluacion.evaluador else 'N/A'],
        ['Fecha de Evaluación:', evaluacion.fecha_evaluacion.strftime('%d/%m/%Y %H:%M')],
    ]
    
    # Buscar firma digital del evaluador
    try:
        firma_digital = FirmaDigital.objects.filter(
            medico=evaluacion.evaluador,
            activa=True
        ).first()
        if firma_digital:
            firma_img = Image(firma_digital.imagen_firma.path, width=2*inch, height=0.5*inch)
            story.append(firma_img)
    except Exception:
        pass
    
    tabla_firma = Table(datos_firma, colWidths=[2*inch, 4*inch])
    tabla_firma.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(tabla_firma)
    
    # Generar QR de validación
    qr_data = f"EVAL-39A-{evaluacion.id}-{evaluacion.periodo_semanal}"
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    qr_image = Image(qr_buffer, width=1*inch, height=1*inch)
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("<i>Código QR de Validación:</i>", styles['Normal']))
    story.append(qr_image)
    
    # Construir PDF
    doc.build(story)
    buffer.seek(0)
    
    # Calcular hash SHA-256
    hash_pdf = hashlib.sha256(buffer.getvalue()).hexdigest()
    
    return buffer, hash_pdf


# ==============================================================================
# MÓDULO DE EVALUACIÓN DE DESEMPEÑO Y DESARROLLO DE TALENTO (Buk-Inspired)
# ==============================================================================

@login_required
def nueva_evaluacion_desempeno(request, empleado_id=None):
    """Formulario para crear una nueva evaluación de desempeño."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    if request.method == 'POST':
        try:
            if request.headers.get('Content-Type') == 'application/json':
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    messages.error(request, 'JSON inválido.')
                    return redirect('home')
            else:
                data = request.POST
            
            empleado = get_object_or_404(Empleado, id=data.get('empleado_id'), empresa=empresa)
            periodo = data.get('periodo', f'Q{timezone.now().month // 4 + 1} {timezone.now().year}')
            cumplimiento_kpis = float(data.get('cumplimiento_kpis', 0))
            
            # Crear evaluación
            evaluacion = EvaluacionDesempeno.objects.create(
                empleado=empleado,
                evaluador=request.user,
                periodo=periodo,
                cumplimiento_kpis=cumplimiento_kpis,
                estado='BORRADOR'
            )
            
            # Crear detalles de competencias
            competencias = Competencia.objects.filter(activa=True)
            promedio_total = 0
            count = 0
            
            for competencia in competencias:
                calificacion = int(data.get(f'competencia_{competencia.id}', 3))
                observacion = data.get(f'observacion_{competencia.id}', '')
                
                DetalleEvaluacion.objects.create(
                    evaluacion=evaluacion,
                    competencia=competencia,
                    calificacion=calificacion,
                    observacion=observacion
                )
                
                promedio_total += calificacion
                count += 1
            
            # Calcular promedios
            if count > 0:
                promedio_competencias = (promedio_total / count) * 20  # Convertir de 1-5 a 0-100
                evaluacion.promedio_competencias = promedio_competencias
                evaluacion.desempeno_score = (promedio_competencias + cumplimiento_kpis) / 2
                evaluacion.potencial_score = promedio_competencias  # Por ahora igual al desempeño
                
                # Calcular cuadrante 9-Box
                evaluacion.cuadrante_9box = evaluacion.calcular_cuadrante_9box()
                evaluacion.estado = 'COMPLETADA'
                evaluacion.save()
                
                # Generar PDI automático
                plan = generar_pdi_automatico(evaluacion.id)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'mensaje': 'Evaluación creada exitosamente',
                        'evaluacion_id': evaluacion.id,
                        'plan_id': plan.id if plan else None,
                        'cuadrante': evaluacion.get_cuadrante_9box_display()
                    })
                
                return redirect('ver_evaluacion_desempeno', evaluacion_id=evaluacion.id)
            else:
                return JsonResponse({'status': 'error', 'mensaje': 'No hay competencias activas'}, status=400)
                
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)
            # Para formularios normales, mostrar error en la página
            from django.contrib import messages as django_messages
            django_messages.error(request, f'Error al guardar la evaluación: {str(e)}')
    
    # GET: Mostrar formulario
    empleados = Empleado.objects.filter(empresa=empresa, activo=True).select_related('usuario')
    competencias = Competencia.objects.filter(activa=True).order_by('tipo', 'nombre')
    empleado_seleccionado = get_object_or_404(Empleado, id=empleado_id, empresa=empresa) if empleado_id else None
    
    return render(request, 'core/nueva_evaluacion_desempeno.html', {
        'empleados': empleados,
        'competencias': competencias,
        'empleado_seleccionado': empleado_seleccionado,
        'periodo_actual': f'Q{timezone.now().month // 4 + 1} {timezone.now().year}'
    })


@login_required
def ver_evaluacion_desempeno(request, evaluacion_id):
    """Ver detalle de una evaluación de desempeño."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    evaluacion = get_object_or_404(
        EvaluacionDesempeno.objects.select_related('empleado__usuario', 'evaluador').prefetch_related('detalles__competencia'),
        id=evaluacion_id,
        empleado__empresa=empresa
    )
    
    plan = PlanDesarrollo.objects.filter(evaluacion_origen=evaluacion).first()
    
    return render(request, 'core/ver_evaluacion_desempeno.html', {
        'evaluacion': evaluacion,
        'plan': plan
    })


@login_required
def mis_resultados(request):
    """Vista para que el empleado vea sus resultados de evaluación."""
    usuario = request.user
    
    # Obtener ficha de empleado si existe
    try:
        empleado = usuario.ficha_empleado
        evaluaciones = EvaluacionDesempeno.objects.filter(
            empleado=empleado
        ).select_related('evaluador').prefetch_related('detalles__competencia').order_by('-fecha')
        
        planes = PlanDesarrollo.objects.filter(empleado=empleado).select_related('evaluacion_origen').order_by('-fecha_creacion')
        
    except Empleado.DoesNotExist:
        evaluaciones = EvaluacionDesempeno.objects.none()
        planes = PlanDesarrollo.objects.none()
        empleado = None
    
    return render(request, 'core/mis_resultados.html', {
        'evaluaciones': evaluaciones,
        'planes': planes,
        'empleado': empleado
    })


@login_required
def matriz_talento(request):
    """Vista gráfica de la matriz 9-Box para el director."""
    empresa = getattr(request.user, 'empresa', None)
    
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        from django.shortcuts import redirect
        return redirect('home')
    
    # Obtener todas las evaluaciones completadas
    try:
        evaluaciones = EvaluacionDesempeno.objects.filter(
            empleado__empresa=empresa,
            estado='COMPLETADA'
        ).select_related('empleado__usuario').order_by('-fecha')[:50]
    except Exception as e:
        import logging
        logger = logging.getLogger('core')
        logger.error(f"Error en matriz_talento: {str(e)}", exc_info=True)
        evaluaciones = EvaluacionDesempeno.objects.none()
    
    # Preparar datos para el gráfico
    datos_grafico = []
    for eval in evaluaciones:
        datos_grafico.append({
            'empleado': eval.empleado.usuario.get_full_name(),
            'desempeno': eval.desempeno_score,
            'potencial': eval.potencial_score,
            'cuadrante': eval.get_cuadrante_9box_display() if eval.cuadrante_9box else 'No clasificado',
            'periodo': eval.periodo,
            'id': eval.id
        })
    
    return render(request, 'core/matriz_talento.html', {
        'evaluaciones': evaluaciones,
        'datos_grafico': json.dumps(datos_grafico)
    })
