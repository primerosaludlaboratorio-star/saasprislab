"""
Vistas para el Sistema de Autorizaciones en Tiempo Real.
"""
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from core.models import SolicitudAutorizacion, Usuario, MensajeInterno
import logging


@login_required
@require_http_methods(["POST"])
def crear_solicitud_autorizacion(request):
    """
    API para crear una nueva solicitud de autorización.
    Body JSON: {
        tipo_accion: str,
        descripcion: str,
        datos_contexto: dict (opcional)
    }
    """
    try:
        data = json.loads(request.body)
        tipo_accion = data.get('tipo_accion')
        descripcion = data.get('descripcion', '').strip()
        datos_contexto = data.get('datos_contexto', {})
        
        if not tipo_accion or not descripcion:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Tipo de acción y descripción son requeridos.'
            }, status=400)
        
        # Validar que el tipo de acción sea válido
        tipos_validos = [choice[0] for choice in SolicitudAutorizacion.TIPO_ACCION_CHOICES]
        if tipo_accion not in tipos_validos:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Tipo de acción inválido.'
            }, status=400)
        
        # Crear la solicitud
        solicitud = SolicitudAutorizacion.objects.create(
            usuario_solicita=request.user,
            tipo_accion=tipo_accion,
            descripcion=descripcion,
            datos_contexto=datos_contexto,
            estado='PENDIENTE'
        )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Solicitud creada exitosamente. Esperando aprobación del Director.',
            'solicitud_id': solicitud.id,
            'token_aprobacion': str(solicitud.token_aprobacion)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Error al procesar los datos JSON.'
        }, status=400)
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en crear_solicitud_autorizacion (autorizaciones.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def verificar_estado_solicitud(request, solicitud_id):
    """
    API para verificar el estado de una solicitud (usado para polling).
    """
    try:
        solicitud = get_object_or_404(
            SolicitudAutorizacion,
            id=solicitud_id,
            usuario_solicita=request.user
        )
        
        return JsonResponse({
            'status': 'success',
            'estado': solicitud.estado,
            'estado_display': solicitud.get_estado_display(),
            'fecha_resolucion': solicitud.fecha_resolucion.isoformat() if solicitud.fecha_resolucion else None,
            'comentario_rechazo': solicitud.comentario_rechazo or '',
            'resuelto_por': solicitud.resuelto_por.get_full_name() if solicitud.resuelto_por else None
        })
        
    except SolicitudAutorizacion.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Solicitud no encontrada.'
        }, status=404)
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en verificar_estado_solicitud (autorizaciones.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=500)


@login_required
def listar_autorizaciones_pendientes(request):
    """
    Vista para listar todas las autorizaciones pendientes (para el Director).
    """
    if not request.user.is_superuser:
        return redirect('dashboard_director')
    
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return redirect('dashboard_director')
    pendientes = SolicitudAutorizacion.objects.filter(
        usuario_solicita__empresa=empresa,
        estado='PENDIENTE'
    ).select_related('usuario_solicita').order_by('-fecha_solicitud')
    
    return render(request, 'core/autorizaciones_pendientes.html', {
        'titulo': 'Autorizaciones Pendientes',
        'solicitudes': pendientes
    })


@login_required
def autorizar_solicitud(request, uuid):
    """
    Vista para aprobar o rechazar una solicitud usando el token UUID.
    """
    if not request.user.is_superuser:
        return redirect('dashboard_director')
    
    solicitud = get_object_or_404(SolicitudAutorizacion, token_aprobacion=uuid)
    
    if solicitud.estado != 'PENDIENTE':
        return render(request, 'core/autorizacion_resuelta.html', {
            'solicitud': solicitud,
            'mensaje': 'Esta solicitud ya fue resuelta anteriormente.'
        })
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        comentario = request.POST.get('comentario', '').strip()
        
        with transaction.atomic():
            solicitud.estado = 'APROBADO' if accion == 'aprobar' else 'RECHAZADO'
            solicitud.fecha_resolucion = timezone.now()
            solicitud.resuelto_por = request.user
            if accion == 'rechazar' and comentario:
                solicitud.comentario_rechazo = comentario
            solicitud.save()
            
            # Notificar al usuario que solicitó
            mensaje_notificacion = f"""✅ Tu solicitud de {solicitud.get_tipo_accion_display()} ha sido {solicitud.get_estado_display().lower()}.

{'Motivo: ' + comentario if accion == 'rechazar' and comentario else 'Ya puedes continuar con la acción solicitada.'}"""
            
            MensajeInterno.objects.create(
                remitente=request.user,
                destinatario=solicitud.usuario_solicita,
                mensaje=mensaje_notificacion
            )
        
        return redirect('listar_autorizaciones_pendientes')
    
    return render(request, 'core/autorizar_solicitud.html', {
        'titulo': f'Autorizar: {solicitud.get_tipo_accion_display()}',
        'solicitud': solicitud
    })


@login_required
@require_http_methods(["POST"])
def api_aprobar_solicitud(request, solicitud_id):
    """
    API para aprobar una solicitud desde el dashboard (AJAX).
    """
    if not request.user.is_superuser:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'No tienes permisos para aprobar solicitudes.'
        }, status=403)
    
    try:
        solicitud = get_object_or_404(SolicitudAutorizacion, id=solicitud_id)
        
        if solicitud.estado != 'PENDIENTE':
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Esta solicitud ya fue resuelta.'
            }, status=400)
        
        with transaction.atomic():
            solicitud.estado = 'APROBADO'
            solicitud.fecha_resolucion = timezone.now()
            solicitud.resuelto_por = request.user
            solicitud.save()
            
            # Notificar al usuario
            MensajeInterno.objects.create(
                remitente=request.user,
                destinatario=solicitud.usuario_solicita,
                mensaje=f"✅ Tu solicitud de {solicitud.get_tipo_accion_display()} ha sido aprobada. Ya puedes continuar."
            )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Solicitud aprobada exitosamente.'
        })
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_aprobar_solicitud (autorizaciones.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_rechazar_solicitud(request, solicitud_id):
    """
    API para rechazar una solicitud desde el dashboard (AJAX).
    """
    if not request.user.is_superuser:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'No tienes permisos para rechazar solicitudes.'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        comentario = data.get('comentario', '').strip()
        
        if not comentario:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Debe proporcionar un motivo de rechazo.'
            }, status=400)
        
        solicitud = get_object_or_404(SolicitudAutorizacion, id=solicitud_id)
        
        if solicitud.estado != 'PENDIENTE':
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Esta solicitud ya fue resuelta.'
            }, status=400)
        
        with transaction.atomic():
            solicitud.estado = 'RECHAZADO'
            solicitud.fecha_resolucion = timezone.now()
            solicitud.resuelto_por = request.user
            solicitud.comentario_rechazo = comentario
            solicitud.save()
            
            # Notificar al usuario
            MensajeInterno.objects.create(
                remitente=request.user,
                destinatario=solicitud.usuario_solicita,
                mensaje=f"❌ Tu solicitud de {solicitud.get_tipo_accion_display()} ha sido rechazada.\n\nMotivo: {comentario}"
            )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Solicitud rechazada exitosamente.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Error al procesar los datos JSON.'
        }, status=400)
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_rechazar_solicitud (autorizaciones.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=500)