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
    """Detecta entorno de producción (VPS, Cloud, cualquier servidor no-local)."""
    import os
    from django.conf import settings as _s
    return bool(
        getattr(_s, 'IS_PRODUCTION', False)
        or os.environ.get('PRISLAB_ENV', '').lower() == 'production'
        or os.environ.get('DJANGO_ENV', '').lower() == 'production'
    )


def _sentinel_remote_token_valid(admin_token):
    """
    Token fuerte para operaciones Sentinel remotas (cloud obligatorio).
    Acepta PRISLAB_SENTINEL_RESET_TOKEN o, si no existe, PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN.
    NO usa SECRET_KEY como fallback en ningún entorno.
    """
    import os

    if not (admin_token or '').strip():
        return False
    ops = (
        (os.environ.get('PRISLAB_SENTINEL_RESET_TOKEN') or '').strip()
        or (os.environ.get('PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN') or '').strip()
    )
    if not ops:
        return False
    return admin_token == ops


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
@require_POST
def api_sentinel_reset(request):
    """
    Reset del dashboard de Sentinel: marca todas las incidencias como SOLUCIONADO
    o las elimina. Accesible por superusuarios o con token de operaciones.

    POST params:
        action: 'resolve' (default) o 'delete'
    Header:
        X-Admin-Token: PRISLAB_SENTINEL_RESET_TOKEN (o PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN)
    """
    admin_token = request.headers.get('X-Admin-Token', request.POST.get('admin_token', ''))

    is_superuser = hasattr(request, 'user') and request.user.is_authenticated and request.user.is_superuser
    is_token_valid = _sentinel_remote_token_valid(admin_token)

    if not is_superuser and not is_token_valid:
        logger.warning(
            'api_sentinel_reset: acceso denegado (use PRISLAB_SENTINEL_RESET_TOKEN o superusuario)'
        )
        return JsonResponse({'status': 'error', 'mensaje': 'Acceso denegado'}, status=403)

    try:
        from consultorio.models import IncidenciaSentinel
        from django.utils import timezone

        action = request.POST.get('action', 'resolve')
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
@require_POST
def api_sentinel_diagnostico(request):
    """Diagnostico rapido del estado del sistema. Requiere admin_token."""
    import os

    admin_token = request.headers.get('X-Admin-Token', request.POST.get('admin_token', ''))
    diag_secret = (os.environ.get('PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN') or '').strip()
    if not diag_secret:
        logger.warning('api_sentinel_diagnostico rechazado: falta PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN')
        return JsonResponse(
            {
                'status': 'error',
                'mensaje': 'Configure PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN.',
            },
            status=503,
        )

    if admin_token != diag_secret:
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
