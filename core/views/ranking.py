"""
Vistas para el Sistema de Ranking de Desempeño.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import Usuario, IncidenciaOperativa
from core.utils.ranking import calcular_score_empleado, calcular_tendencia


@login_required
def ranking_desempeno(request):
    """
    Vista del ranking de desempeño de empleados.
    Muestra podio de honor (top 3) y tabla general.
    """
    if not request.user.is_superuser:
        return render(request, 'core/error_403.html', {
            'mensaje': 'Solo el Director puede acceder al ranking de desempeño.'
        }, status=403)
    
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    hoy = timezone.localdate()
    
    # Periodo actual
    mes_actual = hoy.month
    anio_actual = hoy.year
    
    # Periodo anterior (mes pasado)
    if mes_actual == 1:
        mes_anterior = 12
        anio_anterior = anio_actual - 1
    else:
        mes_anterior = mes_actual - 1
        anio_anterior = anio_actual
    
    # Obtener todos los empleados activos de la empresa
    empleados = Usuario.objects.filter(
        empresa=empresa,
        is_active=True
    ).exclude(is_superuser=True).order_by('first_name', 'last_name')
    
    # Calcular scores para cada empleado
    ranking_data = []
    for empleado in empleados:
        score_actual = calcular_score_empleado(empleado.id, mes_actual, anio_actual)
        score_anterior = calcular_score_empleado(empleado.id, mes_anterior, anio_anterior)
        tendencia = calcular_tendencia(score_actual['score_total'], score_anterior['score_total'])
        
        ranking_data.append({
            'empleado': empleado,
            'score': score_actual,
            'tendencia': tendencia,
            'score_anterior': score_anterior['score_total']
        })
    
    # Ordenar por score total (descendente)
    ranking_data.sort(key=lambda x: x['score']['score_total'], reverse=True)
    
    # Podio de Honor (top 3)
    podio = ranking_data[:3] if len(ranking_data) >= 3 else ranking_data
    
    # Tabla General (todos los empleados)
    tabla_general = ranking_data
    
    return render(request, 'core/ranking_desempeno.html', {
        'titulo': 'Ranking de Desempeño',
        'podio': podio,
        'tabla_general': tabla_general,
        'mes_actual': mes_actual,
        'anio_actual': anio_actual,
        'mes_nombre': ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                      'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'][mes_actual - 1]
    })


@login_required
def detalle_empleado_ranking(request, empleado_id):
    """
    Vista detallada de un empleado con su historial de incidencias.
    """
    if not request.user.is_superuser:
        return render(request, 'core/error_403.html', {
            'mensaje': 'Solo el Director puede ver el detalle de empleados.'
        }, status=403)
    
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    empleado = get_object_or_404(Usuario, id=empleado_id, empresa=empresa)
    
    # Calcular score actual
    hoy = timezone.localdate()
    score_actual = calcular_score_empleado(empleado.id, hoy.month, hoy.year)
    
    # Obtener historial de incidencias
    incidencias = IncidenciaOperativa.objects.filter(
        empresa=empresa,
        usuario_responsable=empleado
    ).order_by('-fecha_hora')
    
    # Agrupar por mes
    incidencias_por_mes = {}
    for incidencia in incidencias:
        mes_key = incidencia.fecha_hora.strftime('%Y-%m')
        if mes_key not in incidencias_por_mes:
            incidencias_por_mes[mes_key] = []
        incidencias_por_mes[mes_key].append(incidencia)
    
    return render(request, 'core/detalle_empleado_ranking.html', {
        'titulo': f'Detalle de Desempeño - {getattr(empleado, "nombre_completo", None) or empleado.get_full_name() or empleado.username}',
        'empleado': empleado,
        'score': score_actual,
        'incidencias': incidencias,
        'incidencias_por_mes': incidencias_por_mes,
        'total_incidencias': incidencias.count(),
        'incidencias_pendientes': incidencias.filter(estado_revision='PENDIENTE').count(),
    })
