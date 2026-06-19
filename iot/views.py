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


@login_required
def dashboard_kioscos(request):
    """Dashboard de gestion de kioscos IoT."""
    kioscos = Kiosco.objects.all()
    ahora = timezone.now()
    for k in kioscos:
        k.online = k.ultima_conexion and (ahora - k.ultima_conexion).seconds < 60
    verificaciones_hoy = VerificacionKiosco.objects.filter(
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
    try:
        data = json.loads(request.body)
        kiosco = Kiosco.objects.create(
            nombre=data.get('nombre', ''),
            ubicacion=data.get('ubicacion', ''),
            ip_address=data.get('ip_address') or None,
        )
        return JsonResponse({'status': 'success', 'id': kiosco.id, 'mensaje': f'Kiosco "{kiosco.nombre}" creado'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@login_required
@require_POST
def api_toggle_kiosco(request, kiosco_id):
    """Activa/desactiva un kiosco."""
    kiosco = get_object_or_404(Kiosco, id=kiosco_id)
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
        verificacion.rechazar()
        return JsonResponse({'status': 'success', 'mensaje': 'Verificacion rechazada'})
    except VerificacionKiosco.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Verificacion no encontrada o expirada'}, status=404)


@login_required
@require_POST
def api_enviar_a_kiosco(request):
    """Envia una verificacion al kiosco desde recepcion."""
    try:
        data = json.loads(request.body)
        from core.models import OrdenDeServicio
        empresa = getattr(request.user, 'empresa', None)
        orden = OrdenDeServicio.objects.get(id=data.get('orden_id'), empresa=empresa)
        kiosco = Kiosco.objects.get(id=data.get('kiosco_id'), activo=True)

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
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)
