"""
Vistas para el Sistema de Registro de Incidencias por Excepción de Política.
"""
import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Count, Q
from datetime import datetime, timedelta
from core.models import IncidenciaOperativa, Usuario, Empresa


@login_required
@require_http_methods(["POST"])
def registrar_incidencia(request):
    """
    API para registrar una nueva incidencia operativa.
    Body JSON: {
        tipo_incidencia: str,
        justificacion: str,
        monto_afectado: float (opcional),
        datos_contexto: dict (opcional)
    }
    """
    try:
        data = json.loads(request.body)
        tipo_incidencia = data.get('tipo_incidencia')
        justificacion = data.get('justificacion', '').strip()
        monto_afectado = data.get('monto_afectado')
        datos_contexto = data.get('datos_contexto', {})
        
        # Validaciones
        if not tipo_incidencia or not justificacion:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Tipo de incidencia y justificación son requeridos.'
            }, status=400)
        
        if len(justificacion) < 15:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'La justificación debe tener al menos 15 caracteres.'
            }, status=400)
        
        # Validar que el tipo de incidencia sea válido
        tipos_validos = [choice[0] for choice in IncidenciaOperativa.TIPO_INCIDENCIA_CHOICES]
        if tipo_incidencia not in tipos_validos:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Tipo de incidencia inválido.'
            }, status=400)
        
        # Obtener empresa del usuario
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Usuario sin empresa asignada.'
            }, status=400)
        
        # Crear la incidencia
        incidencia = IncidenciaOperativa.objects.create(
            empresa=empresa,
            usuario_responsable=request.user,
            tipo_incidencia=tipo_incidencia,
            justificacion=justificacion,
            monto_afectado=monto_afectado if monto_afectado else None,
            datos_contexto=datos_contexto,
            estado_revision='PENDIENTE'
        )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Incidencia registrada exitosamente. La operación continúa.',
            'incidencia_id': incidencia.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Error al procesar los datos JSON.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=500)


@login_required
def panel_auditoria_incidencias(request):
    """
    Panel de auditoría del Director para revisar incidencias operativas.
    """
    if not request.user.is_superuser:
        return render(request, 'core/error_403.html', {
            'mensaje': 'Solo el Director puede acceder a este panel.'
        }, status=403)
    
    empresa = getattr(request.user, 'empresa', None)
    hoy = timezone.localdate()
    
    # Filtros
    filtro_estado = request.GET.get('estado', 'PENDIENTE')
    filtro_fecha = request.GET.get('fecha', 'hoy')  # hoy, semana, mes, todas
    
    # Construir queryset base
    incidencias = IncidenciaOperativa.objects.filter(
        empresa=empresa
    ).select_related('usuario_responsable', 'revisado_por').order_by('-fecha_hora')
    
    # Aplicar filtros
    if filtro_estado != 'TODAS':
        incidencias = incidencias.filter(estado_revision=filtro_estado)
    
    if filtro_fecha == 'hoy':
        incidencias = incidencias.filter(fecha_hora__date=hoy)
    elif filtro_fecha == 'semana':
        inicio_semana = hoy - timedelta(days=7)
        incidencias = incidencias.filter(fecha_hora__date__gte=inicio_semana)
    elif filtro_fecha == 'mes':
        inicio_mes = hoy.replace(day=1)
        incidencias = incidencias.filter(fecha_hora__date__gte=inicio_mes)
    
    # Estadísticas
    estadisticas = {
        'total': IncidenciaOperativa.objects.filter(empresa=empresa).count(),
        'pendientes': IncidenciaOperativa.objects.filter(empresa=empresa, estado_revision='PENDIENTE').count(),
        'justificadas': IncidenciaOperativa.objects.filter(empresa=empresa, estado_revision='JUSTIFICADA').count(),
        'sancionadas': IncidenciaOperativa.objects.filter(empresa=empresa, estado_revision='SANCIONADA').count(),
        'hoy': IncidenciaOperativa.objects.filter(empresa=empresa, fecha_hora__date=hoy).count(),
    }
    
    # Agrupar por tipo
    por_tipo = IncidenciaOperativa.objects.filter(empresa=empresa).values('tipo_incidencia').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    return render(request, 'core/panel_auditoria_incidencias.html', {
        'titulo': 'Panel de Auditoría - Incidencias Operativas',
        'incidencias': incidencias,
        'estadisticas': estadisticas,
        'por_tipo': por_tipo,
        'filtro_estado': filtro_estado,
        'filtro_fecha': filtro_fecha,
        'fecha_hoy': hoy.strftime('%d/%m/%Y')
    })


@login_required
@require_http_methods(["POST"])
def marcar_incidencia_revisada(request, incidencia_id):
    """
    API para marcar una incidencia como revisada por el Director.
    """
    if not request.user.is_superuser:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Solo el Director puede marcar incidencias como revisadas.'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        estado = data.get('estado', 'JUSTIFICADA')  # JUSTIFICADA o SANCIONADA
        comentario = data.get('comentario', '').strip()
        
        incidencia = get_object_or_404(IncidenciaOperativa, id=incidencia_id)
        
        if estado not in ['JUSTIFICADA', 'SANCIONADA']:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Estado inválido. Debe ser JUSTIFICADA o SANCIONADA.'
            }, status=400)
        
        # Actualizar incidencia
        incidencia.estado_revision = estado
        incidencia.revisado_por = request.user
        incidencia.fecha_revision = timezone.now()
        if comentario:
            incidencia.comentario_revision = comentario
        incidencia.save()
        
        return JsonResponse({
            'status': 'success',
            'mensaje': f'Incidencia marcada como {incidencia.get_estado_revision_display()}.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Error al procesar los datos JSON.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=500)
