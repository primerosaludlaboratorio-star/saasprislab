"""
Módulo de Vistas para Expediente Clínico Universal.
Incluye: Búsqueda avanzada de pacientes, vista unificada con timeline.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone

from core.models import Paciente, OrdenDeServicio
from consultorio.models import ConsultaMedica


@login_required
def api_buscar_paciente_avanzado(request):
    """API para búsqueda avanzada de pacientes (Nombre + Fecha de Nacimiento)."""
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)
    
    nombre = request.GET.get('nombre', '').strip()
    fecha_nacimiento = request.GET.get('fecha_nacimiento', '').strip()
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    
    if not nombre or len(nombre) < 2:
        return JsonResponse({'status': 'error', 'mensaje': 'Nombre requerido (mínimo 2 caracteres)'}, status=400)
    
    # Búsqueda por nombre
    pacientes = Paciente.objects.filter(
        empresa=empresa,
        activo=True,
        nombre_completo__icontains=nombre
    )
    
    # Si se proporciona fecha de nacimiento, filtrar también por eso
    if fecha_nacimiento:
        try:
            from datetime import datetime
            fecha_obj = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
            pacientes = pacientes.filter(fecha_nacimiento=fecha_obj)
        except ValueError:
            return JsonResponse({'status': 'error', 'mensaje': 'Formato de fecha inválido. Use YYYY-MM-DD'}, status=400)
    
    pacientes = pacientes[:20]
    
    resultados = []
    for p in pacientes:
        resultados.append({
            'id': p.id,
            'nombre': p.nombre_completo,
            'fecha_nacimiento': p.fecha_nacimiento.strftime('%Y-%m-%d') if p.fecha_nacimiento else None,
            'edad': p.calcular_edad() if hasattr(p, 'calcular_edad') else None,
            'sexo': p.sexo if hasattr(p, 'sexo') else '',
            'telefono': p.telefono or '',
        })
    
    return JsonResponse({'status': 'success', 'pacientes': resultados})


@login_required
def expediente_clinico(request, paciente_id):
    """Vista unificada del expediente clínico con timeline de consultas y laboratorios."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    
    # Verificar que el usuario tenga permiso de médico para ver historial completo
    puede_ver_historial = request.user.rol == 'MEDICO' or request.user.is_superuser
    
    if not puede_ver_historial:
        return JsonResponse({'status': 'error', 'mensaje': 'No tiene permisos para ver el expediente clínico'}, status=403)
    
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa, activo=True)
    
    # Obtener todas las consultas médicas del paciente (de CUALQUIER médico)
    consultas = ConsultaMedica.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).select_related('medico', 'paciente').order_by('-fecha_creacion')[:50]
    
    # Obtener todas las órdenes de laboratorio del paciente
    ordenes_lab = OrdenDeServicio.objects.filter(
        paciente=paciente,
        empresa=empresa
    ).prefetch_related('detalles__estudio').order_by('-fecha_creacion')[:50]
    
    # Crear timeline combinado
    timeline_items = []
    
    for consulta in consultas:
        timeline_items.append({
            'tipo': 'consulta',
            'id': consulta.id,
            'fecha': consulta.fecha_creacion,
            'medico': (consulta.medico.nombre_completo if consulta.medico else 'N/A'),
            'diagnostico': getattr(consulta, 'diagnostico_principal', None) or getattr(consulta, 'diagnostico_texto', None) or getattr(consulta, 'motivo_consulta', None) or getattr(consulta, 'motivo', None) or 'Sin diagnóstico registrado',
            'tratamiento': consulta.tratamiento or '',
            'consulta': consulta
        })
    
    for orden in ordenes_lab:
        estudios = ", ".join([d.estudio.nombre for d in orden.detalles.all()[:5]])
        timeline_items.append({
            'tipo': 'laboratorio',
            'id': orden.id,
            'fecha': orden.fecha_creacion,
            'folio': orden.folio_orden or f'ORD-{orden.id}',
            'estudios': estudios,
            'estado': orden.estado,
            'tiene_pdf': orden.estado in ['RESULTADOS_LISTOS', 'ENTREGADO'],
            'orden': orden
        })
    
    # Ordenar por fecha (más reciente primero)
    timeline_items.sort(key=lambda x: x['fecha'], reverse=True)
    
    return render(request, 'core/expediente_clinico.html', {
        'paciente': paciente,
        'timeline_items': timeline_items,
        'total_consultas': consultas.count(),
        'total_ordenes': ordenes_lab.count(),
    })
