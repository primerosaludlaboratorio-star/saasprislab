"""
MÓDULO PACIENTES - HISTORIAL 360° INTEGRAL
Sistema de Expediente Clínico Electrónico (ECE) NOM-004-SSA3-2012
Visualización completa de toda la información clínica y administrativa del paciente
"""
import json
from datetime import date, datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.db.models import Count, Q, Max, Min, Avg
from django.utils import timezone
from core.models import (
    Paciente, HistoriaClinica, ConsultaMedica, SignosVitales,
    CitaMedica, OrdenDeServicio, Receta, CertificadoMedico,
    EstudioImagen, AudioConsulta, LogAccesoExpediente, AuditLog
)
from core.utils.empresa_request import empresa_efectiva_request


# ==============================================================================
# VISTA PRINCIPAL: HISTORIAL 360° DEL PACIENTE
# ==============================================================================
@login_required
def historial_360_paciente(request, paciente_id):
    """
    Vista principal del Historial 360°.
    
    Integra TODA la información del paciente en una sola pantalla:
    - Datos demográficos
    - Historia clínica (antecedentes)
    - Timeline de consultas
    - Gráficas de signos vitales
    - Estudios de laboratorio
    - Recetas activas
    - Estudios de imagen
    - Certificados médicos
    - Audio/transcripciones (forense)
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
    
    # ===========================================================================
    # 1. HISTORIA CLÍNICA (ANTECEDENTES)
    # ===========================================================================
    try:
        historia_clinica = paciente.historia_clinica
    except HistoriaClinica.DoesNotExist:
        historia_clinica = None
    
    # ===========================================================================
    # 2. TIMELINE DE CONSULTAS (ÚLTIMAS 20)
    # ===========================================================================
    consultas = ConsultaMedica.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).select_related(
        'medico', 'signos_vitales'
    ).order_by('-fecha_consulta')[:20]
    
    # ===========================================================================
    # 3. SIGNOS VITALES - DATOS PARA GRÁFICAS
    # ===========================================================================
    signos_vitales = SignosVitales.objects.filter(
        cita__paciente=paciente,
        cita__empresa=empresa
    ).order_by('-cita__fecha_cita')[:30]  # Últimos 30 registros
    
    # Preparar datos para Chart.js (serializado a JSON para uso seguro en templates)
    datos_graficas = json.dumps(preparar_datos_graficas(signos_vitales))
    
    # ===========================================================================
    # 4. ÓRDENES DE LABORATORIO
    # ===========================================================================
    ordenes_lab = OrdenDeServicio.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).select_related('responsable_ingreso').order_by('-fecha_creacion')[:10]

    detalle_ids_por_orden = {
        orden.id: list(orden.detalles.values_list('id', flat=True))
        for orden in ordenes_lab
    }
    todos_detalle_ids = [
        detalle_id
        for detalle_ids in detalle_ids_por_orden.values()
        for detalle_id in detalle_ids
    ]
    forensic_logs = AuditLog.objects.filter(
        empresa=empresa,
        accion=AuditLog.ACCION_UPDATE,
        modelo_afectado='DetalleOrden',
        objeto_id__in=[str(detalle_id) for detalle_id in todos_detalle_ids],
    ).select_related('usuario').order_by('-fecha_cierta') if todos_detalle_ids else []

    forensic_map = {}
    if todos_detalle_ids:
        orden_por_detalle = {
            str(detalle_id): orden_id
            for orden_id, detalle_ids in detalle_ids_por_orden.items()
            for detalle_id in detalle_ids
        }
        for log in forensic_logs:
            orden_id = orden_por_detalle.get(str(log.objeto_id))
            if orden_id and orden_id not in forensic_map:
                usuario_nombre = ''
                if log.usuario:
                    usuario_nombre = log.usuario.get_full_name() or log.usuario.username
                forensic_map[orden_id] = {
                    'usuario': usuario_nombre or 'Usuario staff',
                    'fecha': timezone.localtime(log.fecha_cierta) if log.fecha_cierta else None,
                }

    for orden in ordenes_lab:
        orden.forensic_badge = forensic_map.get(orden.id)
    
    # ===========================================================================
    # 5. RECETAS ACTIVAS
    # ===========================================================================
    recetas_activas = Receta.objects.filter(
        paciente=paciente,
        empresa=empresa,
        fecha_emision__gte=timezone.now() - timedelta(days=90)
    ).select_related('medico').order_by('-fecha_emision')
    
    # ===========================================================================
    # 6. ESTUDIOS DE IMAGEN (ULTRASONIDO, RX)
    # ===========================================================================
    estudios_imagen = EstudioImagen.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).select_related('medico_interpretador').order_by('-fecha_estudio')[:10]
    
    # ===========================================================================
    # 7. CERTIFICADOS MÉDICOS
    # ===========================================================================
    certificados = CertificadoMedico.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).select_related('medico').order_by('-fecha_emision')[:10]
    
    # ===========================================================================
    # 8. ESTADÍSTICAS GENERALES
    # ===========================================================================
    stats = {
        'total_consultas': ConsultaMedica.objects.filter(
            paciente=paciente, empresa=empresa, estado='FINALIZADA'
        ).count(),
        'total_ordenes_lab': ordenes_lab.count(),
        'total_recetas': recetas_activas.count(),
        'total_estudios_imagen': estudios_imagen.count(),
        'total_certificados': certificados.count(),
        'primera_consulta': consultas.last().fecha_consulta if consultas.exists() else None,
        'ultima_consulta': consultas.first().fecha_consulta if consultas.exists() else None,
    }
    
    # ===========================================================================
    # 9. ALERTAS Y BANDERAS CLÍNICAS
    # ===========================================================================
    alertas = generar_alertas_clinicas(paciente, historia_clinica, signos_vitales.first())
    
    # ===========================================================================
    # 10. LOG DE ACCESO FORENSE
    # ===========================================================================
    # Registrar acceso al expediente (trazabilidad NOM-004)
    if historia_clinica:
        LogAccesoExpediente.objects.create(
            historia_clinica=historia_clinica,
            usuario=request.user,
            tipo_acceso='LECTURA',
            seccion_accedida='CONSULTA_COMPLETA',
            ip_origen=request.META.get('REMOTE_ADDR'),
        )
    
    return render(request, 'pacientes/historial_360.html', {
        'paciente': paciente,
        'historia_clinica': historia_clinica,
        'consultas': consultas,
        'signos_vitales': signos_vitales,
        'datos_graficas': datos_graficas,
        'ordenes_lab': ordenes_lab,
        'recetas_activas': recetas_activas,
        'estudios_imagen': estudios_imagen,
        'certificados': certificados,
        'stats': stats,
        'alertas': alertas,
    })


# ==============================================================================
# VISTA: TIMELINE COMPLETO DE CONSULTAS
# ==============================================================================
@login_required
def timeline_consultas(request, paciente_id):
    """
    Timeline completo de TODAS las consultas del paciente.
    Vista extendida con paginación.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
    
    consultas_qs = ConsultaMedica.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).select_related(
        'medico', 'signos_vitales', 'historia_clinica'
    ).prefetch_related(
        'recetas', 'audio_consultas', 'historial_cambios'
    ).order_by('-fecha_consulta')

    paginator = Paginator(consultas_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'pacientes/timeline_consultas.html', {
        'paciente': paciente,
        'consultas': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
    })


# ==============================================================================
# VISTA: GRÁFICAS DE SIGNOS VITALES
# ==============================================================================
@login_required
def graficas_signos_vitales(request, paciente_id):
    """
    Vista dedicada a gráficas interactivas de signos vitales.
    Chart.js con zoom, filtros por fecha, exportación.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
    
    # Filtros
    meses = int(request.GET.get('meses', 6))  # Por defecto 6 meses
    fecha_desde = timezone.now() - timedelta(days=meses * 30)
    
    signos = SignosVitales.objects.filter(
        cita__paciente=paciente,
        cita__empresa=empresa,
        cita__fecha_cita__gte=fecha_desde
    ).select_related('cita').order_by('cita__fecha_cita')
    
    datos_graficas = json.dumps(preparar_datos_graficas(signos))
    
    return render(request, 'pacientes/graficas_signos_vitales.html', {
        'paciente': paciente,
        'signos': signos,
        'datos_graficas': datos_graficas,
        'meses_seleccionados': meses,
    })


# ==============================================================================
# VISTA: HISTORIA CLÍNICA COMPLETA (ANTECEDENTES)
# ==============================================================================
@login_required
def historia_clinica_completa(request, paciente_id):
    """
    Vista detallada de la Historia Clínica (Antecedentes).
    NOM-004: AHF, APNP, APP, AGO.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
    
    try:
        historia = paciente.historia_clinica
    except HistoriaClinica.DoesNotExist:
        historia = None
    
    return render(request, 'pacientes/historia_clinica_completa.html', {
        'paciente': paciente,
        'historia': historia,
    })


# ==============================================================================
# VISTA: CREAR NUEVO PACIENTE
# ==============================================================================
@login_required
def crear_paciente(request):
    """
    Vista para crear un nuevo paciente.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    from django.forms import ModelForm
    from core.models import Paciente as PacienteModel

    class PacienteForm(ModelForm):
        class Meta:
            model = PacienteModel
            fields = ['nombre_completo', 'nombres', 'apellido_paterno', 'apellido_materno',
                      'telefono', 'email', 'fecha_nacimiento', 'sexo', 'alergias', 'tipo']

    if request.method == 'POST':
        form = PacienteForm(request.POST)
        if form.is_valid():
            paciente = form.save(commit=False)
            paciente.empresa = empresa
            paciente.save()
            messages.success(request, f'Paciente {paciente.nombre_completo} creado exitosamente.')
            return redirect('pacientes:lista_pacientes')
        else:
            messages.error(request, 'Error al crear paciente. Verifique los datos.')
    else:
        form = PacienteForm()
    
    return render(request, 'pacientes/crear_paciente.html', {
        'form': form,
    })


# ==============================================================================
# VISTA: BUSCAR PACIENTE (API)
# ==============================================================================
@login_required
def buscar_paciente(request):
    """
    API para buscar pacientes por nombre, teléfono o email.
    Retorna JSON con resultados.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'pacientes': []})
    
    pacientes = Paciente.objects.filter(
        empresa=empresa
    ).filter(
        Q(nombre_completo__icontains=query) |
        Q(telefono__icontains=query) |
        Q(email__icontains=query)
    )[:20]
    
    resultados = []
    for p in pacientes:
        resultados.append({
            'id': p.id,
            'nombre_completo': p.nombre_completo,
            'telefono': p.telefono or '',
            'email': p.email or '',
            'fecha_nacimiento': p.fecha_nacimiento.isoformat() if p.fecha_nacimiento else None,
        })
    
    return JsonResponse({'pacientes': resultados})


# ==============================================================================
# VISTA: LISTADO DE PACIENTES
# ==============================================================================
@login_required
def lista_pacientes(request):
    """
    Listado de pacientes con búsqueda y filtros.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    # Búsqueda
    query = request.GET.get('q', '')
    qs = Paciente.objects.filter(empresa=empresa).order_by('nombre_completo')
    if query:
        qs = qs.filter(
            Q(nombre_completo__icontains=query) |
            Q(telefono__icontains=query) |
            Q(email__icontains=query),
        )

    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'pacientes/lista_pacientes.html', {
        'pacientes': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'query': query,
    })


# ==============================================================================
# API: DATOS PARA GRÁFICAS (AJAX)
# ==============================================================================
@login_required
def api_datos_graficas_signos(request, paciente_id):
    """
    API AJAX para obtener datos de signos vitales en formato JSON.
    Usado para actualizar gráficas dinámicamente.
    """
    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({}, status=403)
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
    
    meses = int(request.GET.get('meses', 6))
    fecha_desde = timezone.now() - timedelta(days=meses * 30)
    
    signos = SignosVitales.objects.filter(
        cita__paciente=paciente,
        cita__empresa=empresa,
        cita__fecha_cita__gte=fecha_desde
    ).select_related('cita').order_by('cita__fecha_cita')
    
    datos = preparar_datos_graficas(signos)
    
    return JsonResponse(datos, safe=False)


# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def preparar_datos_graficas(signos_queryset):
    """
    Prepara datos de signos vitales para Chart.js.
    Retorna diccionario con arrays listos para graficar.
    """
    fechas = []
    presion_sistolica = []
    presion_diastolica = []
    frecuencia_cardiaca = []
    temperatura = []
    peso = []
    imc = []
    saturacion_o2 = []
    
    for signo in signos_queryset:
        if not signo.cita:
            continue
        fecha = signo.cita.fecha_cita.strftime('%Y-%m-%d')
        fechas.append(fecha)
        
        if signo.presion_arterial_sistolica:
            presion_sistolica.append(float(signo.presion_arterial_sistolica))
        else:
            presion_sistolica.append(None)
        
        if signo.presion_arterial_diastolica:
            presion_diastolica.append(float(signo.presion_arterial_diastolica))
        else:
            presion_diastolica.append(None)
        
        if signo.frecuencia_cardiaca:
            frecuencia_cardiaca.append(float(signo.frecuencia_cardiaca))
        else:
            frecuencia_cardiaca.append(None)
        
        if signo.temperatura:
            temperatura.append(float(signo.temperatura))
        else:
            temperatura.append(None)
        
        if signo.peso:
            peso.append(float(signo.peso))
        else:
            peso.append(None)
        
        if signo.imc:
            imc.append(float(signo.imc))
        else:
            imc.append(None)
        
        if signo.saturacion_oxigeno:
            saturacion_o2.append(float(signo.saturacion_oxigeno))
        else:
            saturacion_o2.append(None)
    
    return {
        'fechas': fechas,
        'presion_sistolica': presion_sistolica,
        'presion_diastolica': presion_diastolica,
        'frecuencia_cardiaca': frecuencia_cardiaca,
        'temperatura': temperatura,
        'peso': peso,
        'imc': imc,
        'saturacion_o2': saturacion_o2,
    }


def generar_alertas_clinicas(paciente, historia_clinica, ultimo_signo):
    """
    Genera alertas clínicas basadas en:
    - Alergias del paciente
    - Condiciones crónicas
    - Signos vitales fuera de rango
    - Medicamentos contraindicados
    """
    alertas = []
    
    # Alerta de alergias
    if historia_clinica and historia_clinica.alergias:
        alertas.append({
            'tipo': 'danger',
            'icono': 'exclamation-triangle-fill',
            'titulo': 'ALERGIAS REGISTRADAS',
            'mensaje': historia_clinica.alergias
        })
    
    # Alerta de enfermedades crónicas
    if historia_clinica and historia_clinica.app_enfermedades_cronicas:
        alertas.append({
            'tipo': 'warning',
            'icono': 'heart-pulse',
            'titulo': 'ENFERMEDADES CRÓNICAS',
            'mensaje': historia_clinica.app_enfermedades_cronicas
        })
    
    # Alertas de signos vitales fuera de rango
    if ultimo_signo:
        # Presión arterial alta
        if (ultimo_signo.presion_arterial_sistolica and 
            ultimo_signo.presion_arterial_sistolica > 140):
            alertas.append({
                'tipo': 'danger',
                'icono': 'activity',
                'titulo': 'PRESIÓN ARTERIAL ELEVADA',
                'mensaje': f'Última medición: {ultimo_signo.presion_arterial_sistolica}/{ultimo_signo.presion_arterial_diastolica} mmHg'
            })
        
        # Saturación de oxígeno baja
        if (ultimo_signo.saturacion_oxigeno and 
            ultimo_signo.saturacion_oxigeno < 95):
            alertas.append({
                'tipo': 'danger',
                'icono': 'lungs',
                'titulo': 'SATURACIÓN DE OXÍGENO BAJA',
                'mensaje': f'Última medición: {ultimo_signo.saturacion_oxigeno}%'
            })
        
        # IMC fuera de rango normal
        if ultimo_signo.imc:
            if ultimo_signo.imc < 18.5:
                alertas.append({
                    'tipo': 'warning',
                    'icono': 'person-fill',
                    'titulo': 'BAJO PESO',
                    'mensaje': f'IMC: {ultimo_signo.imc} (Normal: 18.5-24.9)'
                })
            elif ultimo_signo.imc > 30:
                alertas.append({
                    'tipo': 'warning',
                    'icono': 'person-fill',
                    'titulo': 'OBESIDAD',
                    'mensaje': f'IMC: {ultimo_signo.imc} (Normal: 18.5-24.9)'
                })
    
    # Si no hay alertas, mostrar mensaje positivo
    if not alertas:
        alertas.append({
            'tipo': 'success',
            'icono': 'check-circle-fill',
            'titulo': 'SIN ALERTAS ACTIVAS',
            'mensaje': 'El paciente no tiene alertas clínicas registradas'
        })
    
    return alertas
