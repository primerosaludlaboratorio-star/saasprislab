# ADR 0002: Métricas Prometheus sin dependencia de cliente oficial

**Estado:** Aceptado  
**Fecha:** 2026-07-09

## Contexto

Necesitamos exponer métricas en formato Prometheus (`/metrics/`) para salud del sistema y SLOs. Las opciones eran:

1. Usar la librería oficial `prometheus-client`.
2. Implementar un middleware y vista propia sin dependencias externas.

## Decisión

Implementar métricas con un middleware propio (`core/middleware/sre_metrics.py`) y una vista (`core/views/monitoring.py`) que genera el formato de texto Prometheus manualmente.

## Motivación

- Reduce superficie de ataque y dependencias.
- Mantiene el control total sobre qué métricas exponer y cómo se etiquetan.
- Evita conflictos de versiones con `prometheus-client`.
- Suficiente para el SLO/SLI acordado: uptime, salud de DB/cache, latencia p95 y contadores HTTP.

## Consecuencias

- No tenemos histogramas automáticos ni colecciones de métricas de proceso (CPU, memoria). Se agregan explícitamente si se necesitan.
- El formato debe respetar la especificación de text exposition de Prometheus.
- Scrape sigue siendo posible con Prometheus estándar.

## Alternativas consideradas

- `prometheus-client`: más features, pero añade dependencia y posible incompatibilidad con versiones futuras.
- `django-prometheus`: más fácil, pero requiere cambios en URLs y modelos.
