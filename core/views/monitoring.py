# core/views/monitoring.py
# Endpoint /metrics/ en formato Prometheus text exposition.
# No requiere dependencias externas: métricas básicas de salud, uptime y
# contadores recolectados por SreMetricsMiddleware.

import logging
import secrets
import time
from datetime import datetime, timezone

from django.conf import settings
from django.db import connection, OperationalError
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('prislab.metrics')


STARTUP_TIME = time.time()


def _check_database():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return 1
    except OperationalError:
        return 0


def _check_cache():
    try:
        cache.set("__prislab_metrics_probe__", "ok", timeout=5)
        value = cache.get("__prislab_metrics_probe__")
        return 1 if value == "ok" else 0
    except Exception:
        return 0


def _prometheus_lines():
    from core.middleware.sre_metrics import get_request_metrics

    metrics = get_request_metrics()
    uptime = time.time() - STARTUP_TIME
    db_ok = _check_database()
    cache_ok = _check_cache()

    lines = [
        "# HELP prislab_info Información estática de la aplicación.",
        "# TYPE prislab_info gauge",
        'prislab_info{version="5.0",product="prislab-saas"} 1',
        "",
        "# HELP prislab_uptime_seconds Tiempo transcurrido desde el arranque del proceso.",
        "# TYPE prislab_uptime_seconds counter",
        f"prislab_uptime_seconds {uptime:.3f}",
        "",
        "# HELP prislab_health_status Estado de los componentes críticos (1=ok, 0=fallo).",
        "# TYPE prislab_health_status gauge",
        f'prislab_health_status{{component="database"}} {db_ok}',
        f'prislab_health_status{{component="cache"}} {cache_ok}',
        "",
        "# HELP prislab_request_total Total de requests HTTP procesados.",
        "# TYPE prislab_request_total counter",
    ]

    for key, count in metrics.get("total", {}).items():
        method, status = key.split("|", 1)
        lines.append(
            f'prislab_request_total{{method="{method}",status="{status}"}} {count}'
        )

    lines.extend([
        "",
        "# HELP prislab_request_duration_seconds_bucket Histograma acumulado de latencia HTTP.",
        "# TYPE prislab_request_duration_seconds histogram",
    ])

    buckets = metrics.get("buckets", {})
    for key, counts in buckets.items():
        method, status = key.split("|", 1)
        for le, count in counts.items():
            lines.append(
                f'prislab_request_duration_seconds_bucket{{method="{method}",status="{status}",le="{le}"}} {count}'
            )
        lines.append(
            f'prislab_request_duration_seconds_count{{method="{method}",status="{status}"}} {metrics["count"].get(key, 0)}'
        )
        lines.append(
            f'prislab_request_duration_seconds_sum{{method="{method}",status="{status}"}} {metrics["sum"].get(key, 0.0):.6f}'
        )

    lines.append("")
    now = datetime.now(timezone.utc).isoformat()
    lines.append(f"# Generated at {now}")
    return "\n".join(lines)


@require_http_methods(["GET", "HEAD"])
def metrics_view(request):
    """
    Expone métricas en formato Prometheus text exposition.
    Por defecto permite scraping por Prometheus/Grafana. Si se configura
    PRISLAB_METRICS_TOKEN, se exige en header X-Prometheus-Token o query param token.
    """
    token = getattr(settings, 'PRISLAB_METRICS_TOKEN', '') or ''
    if token:
        provided = (
            request.headers.get('X-Prometheus-Token', '')
            or request.GET.get('token', '')
        )
        if not provided:
            logger.warning('metrics_view: acceso denegado: falta token de scraping')
            return HttpResponseForbidden('Forbidden: token de scraping requerido')
        if not secrets.compare_digest(provided.strip(), token.strip()):
            logger.warning('metrics_view: acceso denegado: token inválido')
            return HttpResponseForbidden('Forbidden: token inválido')
    else:
        logger.debug('metrics_view: acceso sin token (PRISLAB_METRICS_TOKEN no configurado)')

    body = _prometheus_lines()
    return HttpResponse(body, content_type="text/plain; version=0.0.4; charset=utf-8")
