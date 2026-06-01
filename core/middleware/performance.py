"""
PRISLAB SENTINEL 2.0 - Middleware de Performance y Latencia
============================================================
- Cuenta consultas SQL con connection.execute_wrapper (válido con DEBUG=False).
- Umbrales Punto 19: >50 queries o >800ms → WARNING estructurado (GCP / consola).
- Umbral legado: >SENTINEL_SLOW_THRESHOLD_MS → [SLOW] + IncidenciaSentinel >5s.

Configuración en settings.py:
    SENTINEL_WARN_QUERY_COUNT (default 50)
    SENTINEL_WARN_LATENCY_MS (default 800)
    SENTINEL_SLOW_THRESHOLD_MS (default 2000)
"""

import json
import logging
import time

from django.conf import settings
from django.db import connection

logger = logging.getLogger('sentinel.performance')

SLOW_THRESHOLD_MS = getattr(settings, 'SENTINEL_SLOW_THRESHOLD_MS', 2000)
WARN_QUERY_COUNT = getattr(settings, 'SENTINEL_WARN_QUERY_COUNT', 50)
WARN_LATENCY_MS = getattr(settings, 'SENTINEL_WARN_LATENCY_MS', 800)

IGNORE_PREFIXES = ('/static/', '/media/', '/__debug__/', '/favicon.ico', '/sw.js')


class PerformanceMiddleware:
    """
    Mide latencia y número de round-trips a la base de datos por request.
    No almacena texto SQL; solo incrementa un contador vía execute_wrapper.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if any(path.startswith(p) for p in IGNORE_PREFIXES):
            return self.get_response(request)

        query_count = [0]

        def _count_execute(execute, sql, params, many, context):
            query_count[0] += 1
            return execute(sql, params, many, context)

        t_start = time.time()
        with connection.execute_wrapper(_count_execute):
            response = self.get_response(request)
        elapsed_ms = (time.time() - t_start) * 1000

        status = response.status_code
        method = request.method
        user = getattr(request, 'user', None)
        user_str = ''
        if user and hasattr(user, 'get_full_name') and user.is_authenticated:
            user_str = user.get_full_name() or user.username or ''

        nq = query_count[0]

        if nq > WARN_QUERY_COUNT or elapsed_ms > WARN_LATENCY_MS:
            payload = {
                'event': 'PRISLAB_PERF_THRESHOLD',
                'http_method': method,
                'http_path': path[:512],
                'http_status': status,
                'elapsed_ms': round(elapsed_ms, 2),
                'query_count': nq,
                'threshold_queries': WARN_QUERY_COUNT,
                'threshold_latency_ms': WARN_LATENCY_MS,
                'user': (user_str[:200] if user_str else ''),
            }
            logger.warning(
                '%s',
                json.dumps(payload, ensure_ascii=False),
                extra={
                    'prislab_perf_event': payload['event'],
                    'prislab_perf_path': path[:500],
                    'prislab_perf_method': method,
                    'prislab_perf_status': status,
                    'prislab_perf_elapsed_ms': round(elapsed_ms, 2),
                    'prislab_perf_query_count': nq,
                },
            )

        if elapsed_ms > SLOW_THRESHOLD_MS:
            logger.warning(
                f'[SLOW] {method} {path} → {status} | '
                f'{elapsed_ms:.0f}ms | queries={nq} | User: {user_str}'
            )

            if elapsed_ms > 5000:
                self._registrar_latencia_critica(
                    request, path, method, status,
                    elapsed_ms, user_str, nq,
                )
        else:
            logger.debug(
                f'{method} {path} → {status} | {elapsed_ms:.0f}ms | queries={nq}'
            )

        if settings.DEBUG:
            response['X-PRISLAB-Latency-ms'] = f'{elapsed_ms:.0f}'
            response['X-PRISLAB-Query-Count'] = str(nq)

        return response

    @staticmethod
    def _registrar_latencia_critica(request, path, method, status, elapsed_ms, user_str, query_count):
        """Registra en IncidenciaSentinel cuando una request tarda >5s."""
        try:
            import threading

            def _crear():
                try:
                    from django.db import connection as db_conn
                    db_conn.ensure_connection()

                    from consultorio.models import IncidenciaSentinel
                    from core.utils.tenant_strict import empresa_desde_request

                    empresa = empresa_desde_request(request)
                    if not empresa:
                        return

                    IncidenciaSentinel.objects.create(
                        empresa=empresa,
                        origen='MIDDLEWARE',
                        url_afectada=path[:500],
                        metodo_http=method,
                        namespace='performance',
                        codigo_http=status,
                        tipo_excepcion='SlowRequest',
                        traceback_completo=(
                            f'Request extremadamente lenta: {elapsed_ms:.0f}ms\n'
                            f'{method} {path} → HTTP {status}\n'
                            f'Usuario: {user_str}\n'
                            f'Queries (execute_wrapper): {query_count}\n'
                            f'Umbral slow: {SLOW_THRESHOLD_MS}ms'
                        ),
                        tag='#PERFORMANCE',
                        analisis_ia=(
                            f'Cuello de botella detectado: {path} tardo '
                            f'{elapsed_ms:.0f}ms (umbral: {SLOW_THRESHOLD_MS}ms). '
                            f'Queries observadas: {query_count}. '
                            f'Revisar N+1, índices o I/O externo.'
                        ),
                        estado='PENDIENTE',
                        severidad='MEDIA',
                    )

                    db_conn.close()
                except Exception as e:
                    logger.error(f'[PERF] Error registrando latencia: {e}')

            threading.Thread(target=_crear, daemon=True).start()

        except Exception:
            pass
