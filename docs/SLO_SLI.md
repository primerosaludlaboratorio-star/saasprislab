# PRISLAB SaaS — SLO / SLI

**Versión:** 1.0  
**Fecha:** 2026-07-09  
**Ventana de medición:** 30 días naturales

---

## 1. Definiciones

| Término | Definición |
|---------|------------|
| **SLI** | Indicador cuantitativo de nivel de servicio. Se mide con `/metrics/` y logs. |
| **SLO** | Objetivo de nivel de servicio. Umbral de aceptación del SLI. |
| **Error budget** | 100 % − SLO. Cuánto tiempo de infracción está permitido en la ventana. |

---

## 2. SLIs y SLOs acordados

### 2.1 Disponibilidad de la plataforma

| SLI | Cálculo | SLO | Error budget (30 días) |
|-----|---------|-----|------------------------|
| Porcentaje de requests HTTP exitosos (`2xx` y `3xx`) sobre el total | `prislab_request_total{status!~"5.."} / prislab_request_total` | **99.5 %** | ~3.6 h |

### 2.2 Latencia de endpoints críticos

| SLI | Cálculo | SLO |
|-----|---------|-----|
| % de requests con latencia p95 < 800 ms | histograma `prislab_request_duration_seconds_bucket` | **95 %** |
| % de requests con latencia p99 < 2000 ms | histograma `prislab_request_duration_seconds_bucket` | **99 %** |

### 2.3 Salud de dependencias

| SLI | Cálculo | SLO |
|-----|---------|-----|
| % de tiempo que `/ready/` retorna 200 | `prislab_health_status` = 1 para DB y cache | **99.9 %** |

### 2.4 Backup / recuperación

| SLI | Cálculo | SLO |
|-----|---------|-----|
| % de backups diarios exitosos | workflows + logs de cron | **100 %** |
| % de restore tests semanales exitosos | workflow `backup-restore-test` | **100 %** |

---

## 3. Alertas recomendadas

| Condición | Severidad | Acción |
|-----------|-----------|--------|
| `/ready/` 503 por > 2 minutos | P1 | Página al on-call, revisar runbook DB/cache |
| Disponibilidad < 99.5 % en ventana de 1h | P1 | Página al on-call |
| p95 latencia > 800 ms por > 10 min | P2 | Revisar query logs y escalar workers |
| Backup falla 1 vez | P2 | Ticket y reintento manual |
| Restore test falla | P1 | Congelar releases hasta cerrar incidente |
| Uso disco > 85 % | P3 | Limpiar backups/logs |

---

## 4. Instrumentación

- Métricas expuestas en `/metrics/`.
- Health checks: `/health/`, `/ready/`, `/live/`.
- Logs estructurados en `config/settings/logging_conf.py`.
- Alertas iniciales se pueden implementar con Prometheus + Alertmanager o con un cron que consulte `/metrics/` y envíe alertas vía Telegram/email (`CISO_EMAIL`).

---

## 5. Revisión

Este documento se revisa trimestralmente o después de cualquier incidente mayor.
