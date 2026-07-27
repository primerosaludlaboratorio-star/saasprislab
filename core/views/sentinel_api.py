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
from core.decorators import rate_limit

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
@rate_limit('sentinel_telemetry', limit=120, window_seconds=60)
def api_shield_telemetry(request):
    """
    Recibe telemetria del Sentinel Shield (frontend).
    Eventos: rage_click, form_validation, etc.
    Endpoint fire-and-forget, no bloquea al usuario.
    """
    try:
        if len(request.body) > 16 * 1024:
            return JsonResponse({'status': 'error', 'mensaje': 'Payload demasiado grande'}, status=413)
        body = json.loads(request.body.decode('utf-8', errors='replace'))
        if not isinstance(body, dict):
            return JsonResponse({'status': 'error', 'mensaje': 'Payload invalido'}, status=400)
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
        logging.getLogger(__name__).exception("Error inesperado en api_shield_telemetry (sentinel_api.py)")
        logger.debug(f'SENTINEL-SHIELD: Error procesando telemetria: {e}')
        return JsonResponse({'status': 'ok', 'logged': False})  # 200 best-effort beacon


@csrf_exempt
@require_POST
@rate_limit('sentinel_reset', limit=10, window_seconds=60)
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
        logging.getLogger(__name__).exception("Error inesperado en api_sentinel_reset (sentinel_api.py)")
        return JsonResponse({'status': 'error', 'mensaje': 'No fue posible reiniciar Sentinel'}, status=500)


@csrf_exempt
@require_POST
@rate_limit('sentinel_diagnostico', limit=10, window_seconds=60)
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
        info = {}

        # Use Django introspection so the diagnostic works with the configured
        # backend (PostgreSQL in production and SQLite in local verification).
        tables = [
            table
            for table in connection.introspection.table_names()
            if 'estudio' in table.lower() or 'examen' in table.lower()
        ]
        info['tables_encontradas'] = tables

        with connection.cursor() as cursor:
            for table in tables:
                try:
                    # quote_name handles the identifier for the active backend.
                    quoted_table = connection.ops.quote_name(table)
                    cursor.execute(f'SELECT COUNT(*) FROM {quoted_table}')
                    cnt = cursor.fetchone()[0]
                    info[f'count_{table}'] = cnt

                    columns = {
                        column.name.lower()
                        for column in connection.introspection.get_table_description(cursor, table)
                    }
                    sample_columns = [
                        column for column in ('id', 'nombre', 'codigo') if column in columns
                    ]
                    if cnt > 0 and sample_columns:
                        selected = ', '.join(connection.ops.quote_name(column) for column in sample_columns)
                        cursor.execute(
                            f'SELECT {selected} FROM {quoted_table} LIMIT 3'
                        )
                        info[f'sample_{table}'] = [
                            dict(zip(sample_columns, row)) for row in cursor.fetchall()
                        ]
                except Exception:
                    logging.getLogger(__name__).exception(
                        "Error inesperado en api_sentinel_diagnostico (sentinel_api.py)"
                    )
                    info[f'error_{table}'] = 'No disponible'

        return JsonResponse({'status': 'success', 'diagnostico': info})
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_sentinel_diagnostico (sentinel_api.py)")
        return JsonResponse({'status': 'error', 'mensaje': 'No fue posible ejecutar diagnóstico Sentinel'}, status=500)
