"""
Modulo IoT - Gestion de Kioscos y Check-in de Pacientes
"""
import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from core.decorators import rate_limit, require_api_token
from .models import Kiosco, VerificacionKiosco
import logging


def _get_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def dashboard_kioscos(request):
    """Dashboard de gestion de kioscos IoT."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        from django.shortcuts import redirect
        return redirect('home')
    kioscos = Kiosco.objects.filter(empresa=empresa)
    ahora = timezone.now()
    for k in kioscos:
        k.online = k.ultima_conexion and (ahora - k.ultima_conexion).seconds < 60
    verificaciones_hoy = VerificacionKiosco.objects.filter(
        kiosco__empresa=empresa,
        fecha_creacion__date=ahora.date()
    ).count()
    return render(request, 'iot/dashboard_kioscos.html', {
        'kioscos': kioscos,
        'verificaciones_hoy': verificaciones_hoy,
    })


@login_required
@require_POST
def api_crear_kiosco(request):
    """Crea un nuevo kiosco."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada.'}, status=403)
    try:
        data = json.loads(request.body)
        kiosco = Kiosco.objects.create(
            empresa=empresa,
            nombre=data.get('nombre', ''),
            ubicacion=data.get('ubicacion', ''),
            ip_address=data.get('ip_address') or None,
        )
        return JsonResponse({'status': 'success', 'id': kiosco.id, 'mensaje': f'Kiosco "{kiosco.nombre}" creado'})
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_crear_kiosco (views.py)")
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@login_required
@require_POST
def api_toggle_kiosco(request, kiosco_id):
    """Activa/desactiva un kiosco."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada.'}, status=403)
    kiosco = get_object_or_404(Kiosco, id=kiosco_id, empresa=empresa)
    kiosco.activo = not kiosco.activo
    kiosco.save(update_fields=['activo'])
    return JsonResponse({'status': 'success', 'activo': kiosco.activo})


# ======================================================================
# APIs PUBLICAS PARA EL KIOSCO (sin login - el kiosco usa su IP/MAC)
# ======================================================================

@csrf_exempt
@require_http_methods(["GET", "POST"])
@rate_limit('kiosco_heartbeat', limit=180, window_seconds=60)
@require_api_token('PRISLAB_KIOSCO_API_TOKEN')
def api_kiosco_heartbeat(request, kiosco_id):
    """Heartbeat del kiosco - actualiza conexion y retorna verificaciones pendientes."""
    try:
        kiosco = Kiosco.objects.get(id=kiosco_id, activo=True)
        if kiosco.ip_address:
            client_ip = _get_ip(request)
            if client_ip != kiosco.ip_address:
                return JsonResponse({'status': 'error', 'mensaje': 'Acceso denegado (IP no permitida)'}, status=403)

        kiosco.actualizar_conexion()

        # Expirar verificaciones viejas
        VerificacionKiosco.objects.filter(
            kiosco=kiosco, estado='PENDIENTE',
            fecha_expiracion__lt=timezone.now()
        ).update(estado='EXPIRADO')

        # Retornar pendientes
        pendientes = VerificacionKiosco.objects.filter(
            kiosco=kiosco, estado='PENDIENTE'
        ).values('id', 'datos_mostrar', 'fecha_creacion')[:5]

        return JsonResponse({
            'status': 'ok',
            'pendientes': list(pendientes),
            'intervalo': kiosco.intervalo_polling,
        })
    except Kiosco.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Kiosco no encontrado'}, status=404)


@csrf_exempt
@require_POST
@rate_limit('kiosco_confirmar', limit=60, window_seconds=60)
@require_api_token('PRISLAB_KIOSCO_API_TOKEN')
def api_kiosco_confirmar(request, verificacion_id):
    """El paciente confirma sus datos desde el kiosco."""
    try:
        verificacion = VerificacionKiosco.objects.get(
            id=verificacion_id,
            estado='PENDIENTE',
            fecha_expiracion__gt=timezone.now(),
        )
        if verificacion.kiosco and verificacion.kiosco.ip_address:
            client_ip = _get_ip(request)
            if client_ip != verificacion.kiosco.ip_address:
                return JsonResponse({'status': 'error', 'mensaje': 'Acceso denegado (IP no permitida)'}, status=403)

        try:
            data = json.loads(request.body) if request.body else {}
        except (json.JSONDecodeError, ValueError):
            data = {}
        verificacion.confirmar(datos_confirmados=data.get('datos', None))
        return JsonResponse({'status': 'success', 'mensaje': 'Datos confirmados'})
    except VerificacionKiosco.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Verificacion no encontrada o expirada'}, status=404)


@csrf_exempt
@require_POST
@rate_limit('kiosco_rechazar', limit=60, window_seconds=60)
@require_api_token('PRISLAB_KIOSCO_API_TOKEN')
def api_kiosco_rechazar(request, verificacion_id):
    """El paciente rechaza sus datos desde el kiosco."""
    try:
        verificacion = VerificacionKiosco.objects.get(
            id=verificacion_id,
            estado='PENDIENTE',
            fecha_expiracion__gt=timezone.now(),
        )
        if verificacion.kiosco and verificacion.kiosco.ip_address:
            client_ip = _get_ip(request)
            if client_ip != verificacion.kiosco.ip_address:
                return JsonResponse({'status': 'error', 'mensaje': 'Acceso denegado (IP no permitida)'}, status=403)

        verificacion.rechazar()
        return JsonResponse({'status': 'success', 'mensaje': 'Verificacion rechazada'})
    except VerificacionKiosco.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Verificacion no encontrada o expirada'}, status=404)


@login_required
@require_POST
def api_enviar_a_kiosco(request):
    """Envia una verificacion al kiosco desde recepcion."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada.'}, status=403)
    try:
        data = json.loads(request.body)
        from core.models import OrdenDeServicio
        orden = OrdenDeServicio.objects.get(id=data.get('orden_id'), empresa=empresa)
        kiosco = Kiosco.objects.get(id=data.get('kiosco_id'), empresa=empresa, activo=True)

        verificacion = VerificacionKiosco.objects.create(
            orden=orden,
            kiosco=kiosco,
            datos_mostrar={
                'paciente': str(orden.paciente) if orden.paciente_id else 'N/A',
                'estudios': data.get('estudios', []),
            },
            fecha_expiracion=timezone.now() + timedelta(minutes=10),
            usuario_creador=request.user,
        )
        return JsonResponse({'status': 'success', 'verificacion_id': verificacion.id})
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_enviar_a_kiosco (views.py)")
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)