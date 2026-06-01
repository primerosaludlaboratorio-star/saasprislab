"""
PRIS SENTINEL API — Endpoints para Shield Telemetry y Mantenimiento
====================================================================
"""
import json
import logging

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

logger = logging.getLogger('sentinel.shield')


def _is_cloud_runtime():
    import os

    return bool(
        os.environ.get('GOOGLE_CLOUD_PROJECT')
        or os.environ.get('GAE_ENV', '').startswith('standard')
    )


def _sentinel_remote_token_valid(admin_token):
    """
    Token fuerte para operaciones Sentinel remotas (cloud obligatorio).
    Acepta PRISLAB_SENTINEL_RESET_TOKEN o, si no existe, PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN.
    En desarrollo local permite prefijo débil de SECRET_KEY (solo compatibilidad).
    """
    import os

    if not (admin_token or '').strip():
        return False
    ops = (
        (os.environ.get('PRISLAB_SENTINEL_RESET_TOKEN') or '').strip()
        or (os.environ.get('PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN') or '').strip()
    )
    if ops:
        return admin_token == ops
    if _is_cloud_runtime():
        return False
    legacy = (os.environ.get('SECRET_KEY', '') or 'x')[:16]
    return admin_token == legacy


@csrf_exempt
@require_POST
def api_shield_telemetry(request):
    """
    Recibe telemetria del Sentinel Shield (frontend).
    Eventos: rage_click, form_validation, etc.
    Endpoint fire-and-forget, no bloquea al usuario.
    """
    try:
        body = json.loads(request.body.decode('utf-8', errors='replace'))
        event_type = body.get('event', 'unknown')
        data = body.get('data', {})
        timestamp = body.get('timestamp', '')

        user_info = 'anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_info = f'{request.user.id}:{getattr(request.user, "username", "?")}'

        logger.info(
            f'SENTINEL-SHIELD [{event_type}] user={user_info} '
            f'data={json.dumps(data, ensure_ascii=False)[:300]} ts={timestamp}'
        )

        return JsonResponse({'status': 'ok', 'logged': True})

    except Exception as e:
        logger.debug(f'SENTINEL-SHIELD: Error procesando telemetria: {e}')
        return JsonResponse({'status': 'ok', 'logged': False})  # 200 best-effort beacon


@csrf_exempt
@require_http_methods(["POST", "GET"])
def api_sentinel_reset(request):
    """
    Reset del dashboard de Sentinel: marca todas las incidencias como SOLUCIONADO
    o las elimina. Accesible por superusuarios o con token de operaciones.

    GET/POST params:
        action: 'resolve' (default) o 'delete'
        admin_token: en cloud → PRISLAB_SENTINEL_RESET_TOKEN (o PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN);
                     en local puede usarse el prefijo legacy de SECRET_KEY si no hay token configurado.
    """
    admin_token = request.GET.get('admin_token', request.POST.get('admin_token', ''))

    is_superuser = hasattr(request, 'user') and request.user.is_authenticated and request.user.is_superuser
    is_token_valid = _sentinel_remote_token_valid(admin_token)

    if not is_superuser and not is_token_valid:
        if _is_cloud_runtime():
            logger.warning(
                'api_sentinel_reset: acceso denegado (use PRISLAB_SENTINEL_RESET_TOKEN o superusuario)'
            )
        return JsonResponse({'status': 'error', 'mensaje': 'Acceso denegado'}, status=403)

    try:
        from consultorio.models import IncidenciaSentinel
        from django.utils import timezone

        action = request.GET.get('action', request.POST.get('action', 'resolve'))
        total = IncidenciaSentinel.objects.count()
        pendientes = IncidenciaSentinel.objects.exclude(estado='SOLUCIONADO').count()

        # Recopilar resumen antes de limpiar
        resumen = {}
        for sev in ['CRITICA', 'ALTA', 'MEDIA', 'BAJA']:
            count = IncidenciaSentinel.objects.filter(severidad=sev).count()
            if count > 0:
                resumen[sev] = count

        if action == 'delete':
            IncidenciaSentinel.objects.all().delete()
            msg = f'{total} incidencias eliminadas. Dashboard limpio al 100%.'
        else:
            updated = IncidenciaSentinel.objects.exclude(estado='SOLUCIONADO').update(
                estado='SOLUCIONADO',
                fecha_resolucion=timezone.now(),
                notas_resolucion='Reset por el Director via API.',
            )
            msg = f'{updated} incidencias marcadas como SOLUCIONADO.'

        return JsonResponse({
            'status': 'success',
            'mensaje': msg,
            'resumen_antes': resumen,
            'total_antes': total,
            'pendientes_antes': pendientes,
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_sentinel_diagnostico(request):
    """Diagnostico rapido del estado del sistema. Requiere admin_token."""
    import os

    _is_cloud = _is_cloud_runtime()
    admin_token = request.GET.get('admin_token', '')
    diag_secret = (os.environ.get('PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN') or '').strip()
    if diag_secret:
        expected_token = diag_secret
    elif _is_cloud:
        logger.warning('api_sentinel_diagnostico rechazado: falta PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN en cloud')
        return JsonResponse(
            {
                'status': 'error',
                'mensaje': 'Configure PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN (no usar prefijo de SECRET_KEY en producción).',
            },
            status=503,
        )
    else:
        # Solo desarrollo local: compatibilidad legacy (débil); migrar a PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN
        expected_token = (os.environ.get('SECRET_KEY', '') or 'x')[:16]

    if admin_token != expected_token:
        return JsonResponse({'status': 'error', 'mensaje': 'Token invalido'}, status=403)

    try:
        from django.db import connection
        cursor = connection.cursor()
        info = {}

        # Check tables with 'estudio' or 'examen'
        cursor.execute(
            "SELECT tablename FROM pg_tables "
            "WHERE tablename LIKE '%%estudio%%' OR tablename LIKE '%%examen%%'"
        )
        tables = [r[0] for r in cursor.fetchall()]
        info['tables_encontradas'] = tables

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM \"{table}\"")
                cnt = cursor.fetchone()[0]
                info[f'count_{table}'] = cnt
                if cnt > 0:
                    cursor.execute(f"SELECT id, nombre, codigo FROM \"{table}\" LIMIT 3")
                    info[f'sample_{table}'] = [
                        {'id': r[0], 'nombre': r[1], 'codigo': r[2]}
                        for r in cursor.fetchall()
                    ]
            except Exception as e:
                info[f'error_{table}'] = str(e)

        return JsonResponse({'status': 'success', 'diagnostico': info})
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)
