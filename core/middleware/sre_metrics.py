# core/middleware/sre_metrics.py
# Middleware lightweight para recolectar métricas HTTP básicas sin dependencias.
# Los contadores son globales por proceso; en despliegues multi-proceso cada worker
# expone sus propias métricas, lo cual es aceptable para scraping con Prometheus.

import time
import threading
from collections import defaultdict


_BOUNDS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf"))

_lock = threading.Lock()
_request_total = defaultdict(int)
_request_count = defaultdict(int)
_request_sum = defaultdict(float)
_request_buckets = defaultdict(lambda: defaultdict(int))


def _le_value(value):
    if value == float("inf"):
        return "+Inf"
    return str(value)


def _record(method, status_code, duration):
    key = f"{method.upper()}|{status_code}"
    with _lock:
        _request_total[key] += 1
        _request_count[key] += 1
        _request_sum[key] += duration
        for bound in _BOUNDS:
            if duration <= bound:
                _request_buckets[key][_le_value(bound)] += 1


def get_request_metrics():
    with _lock:
        return {
            "total": dict(_request_total),
            "count": dict(_request_count),
            "sum": dict(_request_sum),
            "buckets": {k: dict(v) for k, v in _request_buckets.items()},
        }


class SreMetricsMiddleware:
    """
    Mide latencia y contabiliza requests HTTP para el endpoint /metrics/.
    Debe colocarse lo más arriba posible en MIDDLEWARE (después de SecurityMiddleware
    y WhiteNoise) para capturar la mayor cantidad de requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration = time.time() - start
        _record(request.method, response.status_code, duration)
        return response
