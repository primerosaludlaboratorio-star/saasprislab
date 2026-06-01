"""
PRISLAB V5 - Vistas para Gestión de Pacientes
Timeline 360° y búsqueda inteligente
"""

import logging
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q

from core.models import Paciente
from core.services.paciente_service import obtener_timeline_paciente, buscar_paciente_existente

logger = logging.getLogger(__name__)


@login_required
def timeline_paciente(request, paciente_id):
    """
    Vista del Timeline 360° del paciente.
    Muestra cronológicamente: Consultas + Lab + Farmacia.
    """
    paciente = get_object_or_404(Paciente, pk=paciente_id, activo=True, deleted_at__isnull=True)
    
    # Verificar permisos (solo médicos, directores y recepción)
    if not (request.user.is_superuser or 
            request.user.groups.filter(name__in=['MEDICO', 'RECEPCION', 'LABORATORIO']).exists()):
        return render(request, '403.html', status=403)
    
    # Obtener timeline completo
    eventos = obtener_timeline_paciente(paciente)
    
    context = {
        'paciente': paciente,
        'eventos': eventos,
        'total_eventos': len(eventos),
    }
    
    return render(request, 'core/paciente_timeline.html', context)


@login_required
@require_http_methods(["GET"])
def buscar_paciente_api(request):
    """
    API: Búsqueda inteligente de pacientes para evitar duplicados.
    
    Query params:
        - nombre: Nombre del paciente
        - fecha_nacimiento: Fecha de nacimiento (YYYY-MM-DD)
        - telefono: Teléfono
    
    Returns:
        JSON con pacientes encontrados
    """
    nombre = request.GET.get('nombre', '').strip()
    fecha_nac = request.GET.get('fecha_nacimiento')
    telefono = request.GET.get('telefono', '').strip()
    
    if not nombre and not telefono:
        return JsonResponse({
            'status': 'error',
            'message': 'Se requiere al menos nombre o teléfono'
        }, status=400)
    
    try:
        # Buscar paciente existente
        from datetime import datetime
        fecha_nac_obj = None
        if fecha_nac:
            try:
                fecha_nac_obj = datetime.strptime(fecha_nac, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        paciente_encontrado = buscar_paciente_existente(
            nombre_completo=nombre,
            fecha_nacimiento=fecha_nac_obj,
            telefono=telefono,
            empresa=getattr(request.user, 'empresa', None)
        )
        
        if paciente_encontrado:
            return JsonResponse({
                'status': 'found',
                'paciente': {
                    'id': paciente_encontrado.id,
                    'uuid': str(paciente_encontrado.uuid),
                    'nombre': paciente_encontrado.nombre_completo,
                    'fecha_nacimiento': paciente_encontrado.fecha_nacimiento.isoformat() if paciente_encontrado.fecha_nacimiento else None,
                    'sexo': paciente_encontrado.get_sexo_display() if paciente_encontrado.sexo else None,
                    'telefono': paciente_encontrado.telefono,
                    'alergias': paciente_encontrado.alergias,
                    'tipo': paciente_encontrado.get_tipo_display(),
                    'edad': paciente_encontrado.edad,
                }
            })
        else:
            return JsonResponse({
                'status': 'not_found',
                'message': 'No se encontró un paciente con esos datos'
            })
    
    except Exception as e:
        logger.error(f"Error en búsqueda de paciente: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Error del servidor: {type(e).__name__}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def lista_pacientes_api(request):
    """
    API: Lista de pacientes con paginación y búsqueda.
    
    Query params:
        - q: Término de búsqueda (nombre, teléfono)
        - limit: Número de resultados (default: 20)
        - offset: Offset para paginación
    """
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 20))
    offset = int(request.GET.get('offset', 0))
    
    # Filtros base
    pacientes = Paciente.objects.filter(
        empresa=getattr(request.user, 'empresa', None),
        activo=True,
        deleted_at__isnull=True
    )
    
    # Búsqueda por término
    if query:
        pacientes = pacientes.filter(
            Q(nombre_completo__icontains=query) |
            Q(telefono__icontains=query)
        )
    
    # Paginación
    total = pacientes.count()
    pacientes = pacientes[offset:offset + limit]
    
    # Serializar
    resultados = []
    for pac in pacientes:
        resultados.append({
            'id': pac.id,
            'uuid': str(pac.uuid),
            'nombre': pac.nombre_completo,
            'fecha_nacimiento': pac.fecha_nacimiento.isoformat() if pac.fecha_nacimiento else None,
            'sexo': pac.get_sexo_display() if pac.sexo else None,
            'telefono': pac.telefono,
            'edad': pac.edad,
            'tipo': pac.get_tipo_display(),
        })
    
    return JsonResponse({
        'status': 'success',
        'total': total,
        'limit': limit,
        'offset': offset,
        'pacientes': resultados
    })
