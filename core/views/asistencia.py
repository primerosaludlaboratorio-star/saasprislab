"""
Módulo de Asistencia - PRISLAB
Gestión de horarios, registro de asistencia e incidencias.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
from datetime import date, datetime, timedelta

from core.models import (
    Empresa, Empleado, RegistroAsistencia, Sucursal, Usuario,
    HorarioTrabajo, IncidenciaAsistencia,
)
import logging

@login_required
def dashboard_asistencia(request):
    """Dashboard principal del módulo de asistencia."""
    empresa = getattr(request.user, 'empresa', None)
    
    # Estadísticas del día
    hoy = date.today()
    asistencias_hoy = RegistroAsistencia.objects.filter(
        empresa=empresa,
        fecha_hora__date=hoy
    ).count()
    
    faltas_hoy = Empleado.objects.filter(
        empresa=empresa,
        activo=True
    ).exclude(
        id__in=RegistroAsistencia.objects.filter(
            empresa=empresa,
            fecha_hora__date=hoy,
            tipo_registro='ENTRADA'
        ).values_list('empleado_id', flat=True)
    ).count()
    
    # Incidencias pendientes
    incidencias_pendientes = IncidenciaAsistencia.objects.filter(
        empresa=empresa,
        estado='PENDIENTE'
    ).select_related('empleado').order_by('-fecha_solicitud')[:10]
    
    # Registros recientes
    registros_recientes = RegistroAsistencia.objects.filter(
        empresa=empresa
    ).select_related('empleado').order_by('-fecha_hora')[:10]
    
    return render(request, 'core/asistencia/dashboard.html', {
        'empresa': empresa,
        'hoy': hoy,
        'asistencias_hoy': asistencias_hoy,
        'faltas_hoy': faltas_hoy,
        'incidencias_pendientes': incidencias_pendientes,
        'registros_recientes': registros_recientes,
    })


@login_required
def registro_asistencia(request):
    """Registro manual de asistencia."""
    empresa = getattr(request.user, 'empresa', None)
    
    # Filtros
    fecha = request.GET.get('fecha', date.today().isoformat())
    empleado_id = request.GET.get('empleado', '')
    
    registros = RegistroAsistencia.objects.filter(empresa=empresa)
    
    if fecha:
        registros = registros.filter(fecha_hora__date=fecha)
    if empleado_id:
        registros = registros.filter(empleado_id=empleado_id)
    
    registros = registros.select_related('empleado', 'sucursal').order_by('-fecha_hora')
    
    # Paginación
    paginator = Paginator(registros, 50)
    page = request.GET.get('page')
    registros_pag = paginator.get_page(page)
    
    empleados = Empleado.objects.filter(empresa=empresa, activo=True).order_by('id')
    
    return render(request, 'core/asistencia/registro_asistencia.html', {
        'empresa': empresa,
        'registros': registros_pag,
        'empleados': empleados,
        'fecha': fecha,
        'empleado_id': empleado_id,
    })


@login_required
@require_http_methods(["GET", "POST"])
def registrar_entrada_salida(request):
    """Registrar entrada o salida de un empleado."""
    empresa = getattr(request.user, 'empresa', None)
    
    if request.method == 'POST':
        try:
            empleado_id = request.POST.get('empleado_id')
            tipo_registro = request.POST.get('tipo_registro', 'ENTRADA')
            observaciones = request.POST.get('observaciones', '').strip()
            
            empleado = get_object_or_404(Empleado, id=empleado_id, empresa=empresa)

            from core.utils.sucursal_helpers import get_user_primary_sucursal
            user_sucursal = get_user_primary_sucursal(request.user)

            registro = RegistroAsistencia.objects.create(
                empresa=empresa,
                empleado=empleado,
                tipo_registro=tipo_registro,
                metodo_registro='WEB',
                sucursal=user_sucursal,
                observaciones=observaciones
            )
            
            messages.success(request, f'{tipo_registro} registrada para {str(empleado.usuario)}')
            return redirect('registro_asistencia')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en registrar_entrada_salida (asistencia.py)")
            messages.error(request, f'Error al registrar asistencia: {str(e)}')
    
    # GET: Mostrar formulario
    empleados = Empleado.objects.filter(empresa=empresa, activo=True).order_by('id')
    
    return render(request, 'core/asistencia/registrar_entrada_salida.html', {
        'empresa': empresa,
        'empleados': empleados,
    })


@login_required
def horarios_trabajo(request):
    """Gestionar horarios de trabajo de empleados."""
    empresa = getattr(request.user, 'empresa', None)
    
    empleado_id = request.GET.get('empleado', '')
    horarios = HorarioTrabajo.objects.filter(empresa=empresa, activo=True)
    
    if empleado_id:
        horarios = horarios.filter(empleado_id=empleado_id)
    
    horarios = horarios.select_related('empleado').order_by('empleado__id', 'dia_semana')
    
    empleados = Empleado.objects.filter(empresa=empresa, activo=True).order_by('id')
    
    return render(request, 'core/asistencia/horarios_trabajo.html', {
        'empresa': empresa,
        'horarios': horarios,
        'empleados': empleados,
        'empleado_id': empleado_id,
    })


@login_required
@require_http_methods(["GET", "POST"])
def crear_horario(request):
    """Crear o editar horario de trabajo."""
    empresa = getattr(request.user, 'empresa', None)
    horario_id = request.GET.get('id') or request.POST.get('horario_id')
    
    if request.method == 'POST':
        try:
            if horario_id:
                horario = get_object_or_404(HorarioTrabajo, id=horario_id, empresa=empresa)
            else:
                horario = HorarioTrabajo(empresa=empresa)
            
            horario.empleado_id = request.POST.get('empleado_id')
            horario.dia_semana = request.POST.get('dia_semana')
            horario.hora_entrada = request.POST.get('hora_entrada')
            horario.hora_salida = request.POST.get('hora_salida')
            horario.activo = request.POST.get('activo') == 'on'
            
            # Calcular horas de trabajo
            entrada = datetime.strptime(horario.hora_entrada, '%H:%M').time()
            salida = datetime.strptime(horario.hora_salida, '%H:%M').time()
            entrada_dt = datetime.combine(date.today(), entrada)
            salida_dt = datetime.combine(date.today(), salida)
            if salida_dt < entrada_dt:
                salida_dt += timedelta(days=1)
            diferencia = salida_dt - entrada_dt
            horario.horas_trabajo = Decimal(str(diferencia.total_seconds() / 3600))
            
            horario.save()
            
            messages.success(request, 'Horario guardado exitosamente')
            return redirect('horarios_trabajo')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en crear_horario (asistencia.py)")
            messages.error(request, f'Error al guardar horario: {str(e)}')
    
    # GET: Mostrar formulario
    horario = None
    if horario_id:
        horario = get_object_or_404(HorarioTrabajo, id=horario_id, empresa=empresa)
    
    empleados = Empleado.objects.filter(empresa=empresa, activo=True).order_by('id')
    
    return render(request, 'core/asistencia/crear_horario.html', {
        'empresa': empresa,
        'horario': horario,
        'empleados': empleados,
    })


@login_required
def incidencias_asistencia(request):
    """Lista de incidencias de asistencia."""
    empresa = getattr(request.user, 'empresa', None)
    
    # Filtros
    estado = request.GET.get('estado', '')
    tipo = request.GET.get('tipo', '')
    empleado_id = request.GET.get('empleado', '')
    
    incidencias = IncidenciaAsistencia.objects.filter(empresa=empresa)
    
    if estado:
        incidencias = incidencias.filter(estado=estado)
    if tipo:
        incidencias = incidencias.filter(tipo_incidencia=tipo)
    if empleado_id:
        incidencias = incidencias.filter(empleado_id=empleado_id)
    
    incidencias = incidencias.select_related('empleado', 'autorizado_por').order_by('-fecha_inicio')
    
    # Paginación
    paginator = Paginator(incidencias, 20)
    page = request.GET.get('page')
    incidencias_pag = paginator.get_page(page)
    
    empleados = Empleado.objects.filter(empresa=empresa, activo=True).order_by('id')
    
    return render(request, 'core/asistencia/incidencias.html', {
        'empresa': empresa,
        'incidencias': incidencias_pag,
        'empleados': empleados,
        'estado': estado,
        'tipo': tipo,
        'empleado_id': empleado_id,
    })


@login_required
@require_http_methods(["GET", "POST"])
def crear_incidencia(request):
    """Crear o editar incidencia de asistencia."""
    empresa = getattr(request.user, 'empresa', None)
    incidencia_id = request.GET.get('id') or request.POST.get('incidencia_id')
    
    if request.method == 'POST':
        try:
            if incidencia_id:
                incidencia = get_object_or_404(IncidenciaAsistencia, id=incidencia_id, empresa=empresa)
            else:
                incidencia = IncidenciaAsistencia(empresa=empresa)
            
            incidencia.empleado_id = request.POST.get('empleado_id')
            incidencia.tipo = request.POST.get('tipo_incidencia') or request.POST.get('tipo')
            incidencia.fecha_inicio = request.POST.get('fecha_inicio')
            incidencia.fecha_fin = request.POST.get('fecha_fin')
            incidencia.motivo = request.POST.get('motivo', '').strip()
            
            # Calcular días
            fecha_inicio = datetime.strptime(incidencia.fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(incidencia.fecha_fin, '%Y-%m-%d').date()
            incidencia.dias = (fecha_fin - fecha_inicio).days + 1
            
            if 'documento_soporte' in request.FILES:
                incidencia.documento_soporte = request.FILES['documento_soporte']
            
            incidencia.save()
            
            messages.success(request, 'Incidencia registrada exitosamente')
            return redirect('incidencias_asistencia')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en crear_incidencia (asistencia.py)")
            messages.error(request, f'Error al guardar incidencia: {str(e)}')
    
    # GET: Mostrar formulario
    incidencia = None
    if incidencia_id:
        incidencia = get_object_or_404(IncidenciaAsistencia, id=incidencia_id, empresa=empresa)
    
    empleados = Empleado.objects.filter(empresa=empresa, activo=True).order_by('id')
    
    return render(request, 'core/asistencia/crear_incidencia.html', {
        'empresa': empresa,
        'incidencia': incidencia,
        'empleados': empleados,
        'today': date.today().isoformat(),
    })


@login_required
@require_http_methods(["POST"])
def autorizar_incidencia(request, incidencia_id):
    """Autorizar o rechazar una incidencia."""
    empresa = getattr(request.user, 'empresa', None)
    incidencia = get_object_or_404(IncidenciaAsistencia, id=incidencia_id, empresa=empresa)
    
    accion = request.POST.get('accion', 'AUTORIZADA')
    
    if accion == 'AUTORIZADA':
        incidencia.estado = 'AUTORIZADA'
        incidencia.autorizado_por = request.user
        messages.success(request, 'Incidencia autorizada')
    else:
        incidencia.estado = 'RECHAZADA'
        incidencia.autorizado_por = request.user
        messages.success(request, 'Incidencia rechazada')
    
    incidencia.save()
    
    return redirect('incidencias_asistencia')