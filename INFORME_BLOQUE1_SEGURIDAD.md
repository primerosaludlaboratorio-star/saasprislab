# Bloque 1 - Inventario de Riesgos de Seguridad
## PRISLAB SaaS v5.0 - Auditoría de Seguridad

**Fecha:** Mayo 2026  
**Auditor:** Cascade (Auditor Programador Nivel 5)  
**Estado:** ✅ Completado

---

## 1. Configuración CORS

### Valor Actual de CORS_ALLOW_ALL_ORIGINS

**Archivo:** `config/settings.py:29-35`

```python
_cors_allow_raw = (os.environ.get('CORS_ALLOW_ALL_ORIGINS') or '').strip().lower()
if _cors_allow_raw:
    CORS_ALLOW_ALL_ORIGINS = _cors_allow_raw in ('true', '1', 'yes', 'on')
else:
    CORS_ALLOW_ALL_ORIGINS = not _is_cloud_env  # True en local, False en cloud
```

**Comportamiento:**
| Entorno | Valor por Defecto | Riesgo |
|---------|-------------------|--------|
| Desarrollo local (sin GOOGLE_CLOUD_PROJECT) | `True` (permissivo) | 🟡 Medio - Solo para dev |
| Producción Cloud (Cloud Run/GAE) | `False` (restrictivo) | 🟢 Bajo |

**Riesgo evaluado:** 🟡 **MEDIO** en desarrollo, 🟢 **BAJO** en producción

**Recomendación:** Para desarrollo local seguro, establecer:
```bash
CORS_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
CORS_ALLOW_ALL_ORIGINS=false
```

---

## 2. Endpoints @csrf_exempt - Inventario Completo

### Resumen General
- **Total de endpoints:** 14
- **Con autenticación alternativa:** 13 (92.8%)
- **Sin autenticación:** 1 (7.2%)

### Tabla Detallada de Endpoints

| # | Archivo | Línea | Función | URL Pattern | Auth Alternativa | Tipo Auth | Variable Entorno |
|---|---------|-------|---------|-------------|------------------|-----------|------------------|
| 1 | `core/views/cron_tasks.py` | 31 | `cron_check_metrologia` | `/cron/check-metrologia/` | ✅ Sí | Header + Secret | `CRON_SECRET` |
| 2 | `core/views/cron_tasks.py` | 65 | `cron_check_stock_critico` | `/cron/check-stock/` | ✅ Sí | Header + Secret | `CRON_SECRET` |
| 3 | `core/views/cron_tasks.py` | 100+ | `cron_backup_nocturno` | `/cron/backup/` | ✅ Sí | Header + Secret | `CRON_SECRET` |
| 4 | `core/views/sentinel_api.py` | 47 | `api_shield_telemetry` | `/api/sentinel/shield/` | ✅ Sí | Token o Superuser | `PRISLAB_SENTINEL_*_TOKEN` |
| 5 | `core/views/sentinel_api.py` | 77 | `api_sentinel_reset` | `/api/sentinel/reset/` | ✅ Sí | Token o Superuser | `PRISLAB_SENTINEL_*_TOKEN` |
| 6 | `core/views/sentinel_api.py` | 125+ | `api_sentinel_status` | `/api/sentinel/status/` | ✅ Sí | Token o Superuser | `PRISLAB_SENTINEL_*_TOKEN` |
| 7 | `iot/views.py` | 63 | `api_kiosco_heartbeat` | `/api/iot/kiosco/<id>/heartbeat/` | ✅ Sí | kiosco_id | N/A - API pública |
| 8 | `iot/views.py` | 90 | `api_kiosco_confirmar` | `/api/iot/kiosco/confirmar/<id>/` | ✅ Sí | kiosco_id | N/A - API pública |
| 9 | `iot/views.py` | 103 | `api_kiosco_rechazar` | `/api/iot/kiosco/rechazar/<id>/` | ✅ Sí | kiosco_id | N/A - API pública |
| 10 | `consultorio/api_views.py` | 19 | `procesar_audio_consulta` | `/consultorio/api/procesar-audio-consulta/` | ✅ Sí | @login_required | Sesión Django |
| 11 | `consultorio/api_views.py` | 63 | `procesar_audio_laboratorio` | `/consultorio/api/procesar-audio-lab/` | ✅ Sí | @login_required | Sesión Django |
| 12 | `core/views/general.py` | 159 | `log_frontend_error` | `/api/log-frontend-error/` | ❌ **NO** | Ninguna | N/A |
| 13 | `core/views/voice.py` | 182 | `verificar_webauthn` | `/api/voice/verify-auth/` | ✅ Sí | @login_required | Sesión Django |
| 14 | `core/services/lims/interfaces_lims_service.py` | 155 | `receptor_hl7` | `/api/iot/hl7/` | ✅ Sí | API Key | `HL7_API_KEY` |

### Análisis de Endpoints sin Protección Adecuada

#### ⚠️ Endpoint 12: `log_frontend_error` (RIESGO BAJO)

**Ubicación:** `core/views/general.py:159-206`

**Problema:** No tiene autenticación alternativa explícita

**Justificación de riesgo bajo:**
- Solo recibe errores de JavaScript del frontend
- No expone datos sensibles
- No modifica estado del servidor
- Silencioso: fallos no afectan operación principal

**Recomendación:** Añadir rate limiting o validación de origen:
```python
# Opcional: validar que venga de origen conocido
origin = request.META.get('HTTP_ORIGIN', '')
if origin and origin not in CORS_ALLOWED_ORIGINS:
    return JsonResponse({'status': 'ignored'}, status=200)
```

---

## 3. Tokens Derivados de SECRET_KEY

### Hallazgos Críticos

#### 1. `_sentinel_remote_token_valid` (sentinel_api.py:25-44)

```python
def _sentinel_remote_token_valid(admin_token):
    # ...
    if _is_cloud_runtime():
        return False
    legacy = (os.environ.get('SECRET_KEY', '') or 'x')[:16]
    return admin_token == legacy
```

**Comportamiento:**
- En **cloud**: Requiere `PRISLAB_SENTINEL_*_TOKEN` explícito
- En **local**: Acepta primeros 16 caracteres de SECRET_KEY como fallback

**Riesgo:** 🟡 **MEDIO** - Solo afecta entorno local

#### 2. `_get_fernet` (core/fields.py:31-42)

```python
def _get_fernet():
    raw = getattr(settings, 'FERNET_KEY', None)
    if raw:
        key = raw.encode() if isinstance(raw, str) else raw
    else:
        # Derivar clave de 32 bytes desde SECRET_KEY
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)
```

**Comportamiento:**
- Si `FERNET_KEY` existe: la usa directamente
- Si no existe: **deriva de SECRET_KEY** vía SHA256

**Riesgo:** 🟢 **BAJO** - Compatibilidad legacy, FERNET_KEY debería estar en prod

### Tokens Requeridos Documentados

| Variable | Usada en | Requerida en Prod | Estado en .env.example |
|----------|----------|-------------------|------------------------|
| `PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN` | sentinel_api.py | No | ❌ No documentada |
| `PRISLAB_SENTINEL_RESET_TOKEN` | sentinel_api.py | No | ❌ No documentada |
| `HL7_API_KEY` | interfaces_lims_service.py | No | ❌ No documentada |
| `CRON_SECRET` | cron_tasks.py | No | ❌ No documentada |
| `FERNET_KEY` | core/fields.py | ✅ **Sí** | ❌ No documentada |

**⚠️ GAP:** 4 tokens de servicio no están documentados en `.env.example`

---

## 4. Verificación de PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN

### Estado en settings.py

```python
# NO está definido explícitamente en settings.py
# Se lee directamente de os.environ.get('PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN')
```

**Uso encontrado:**
- `core/views/sentinel_api.py:37`: `(os.environ.get('PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN') or '').strip()`

**Conclusión:**
- ✅ Variable existe en código
- ❌ No está documentada en `.env.example`
- ❌ No hay validación de que esté configurada en producción

---

## 5. Resumen de Riesgos de Seguridad

| ID | Riesgo | Severidad | Ubicación | Acción Requerida |
|----|--------|-----------|-----------|------------------|
| R1 | Tokens de servicio no documentados | 🟡 Medio | `.env.example` | Añadir 4 tokens faltantes |
| R2 | `log_frontend_error` sin auth | 🟢 Bajo | `general.py:159` | Añadir rate limiting opcional |
| R3 | SECRET_KEY[:16] como fallback local | 🟡 Medio | `sentinel_api.py:43` | Documentar comportamiento |
| R4 | FERNET_KEY deriva de SECRET_KEY | 🟡 Medio | `fields.py:39` | Forzar FERNET_KEY en prod |
| R5 | CORS_ALLOW_ALL_ORIGINS en local | 🟡 Medio | `settings.py:35` | Restringir a localhost |

---

## 6. Archivos Generados

- ✅ `INFORME_BLOQUE1_SEGURIDAD.md` (este documento)
- ✅ `CSRF_EXEMPT_ENDPOINTS.txt` (lista de endpoints)
- ✅ `CSRF_EXEMPT_AUTH_STATUS.md` (tabla de autenticación)

---

## 7. Recomendaciones para Bloque 2

1. **Documentar tokens faltantes** en `.env.example`:
   - `PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN`
   - `PRISLAB_SENTINEL_RESET_TOKEN`
   - `HL7_API_KEY`
   - `CRON_SECRET`

2. **Crear decorador `@require_api_token`** para estandarizar protección

3. **Restringir CORS en desarrollo** a orígenes explícitos

4. **Añadir rate limiting** a `log_frontend_error`

5. **Forzar FERNET_KEY** en producción (no derivar de SECRET_KEY)

---

## Checklist Bloque 1

- [x] Revisar configuración CORS
- [x] Listar todos los @csrf_exempt
- [x] Analizar autenticación alternativa de cada uno
- [x] Detectar tokens derivados de SECRET_KEY
- [x] Verificar PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN
- [x] Crear tabla resumen de autenticación
- [x] Generar archivos de documentación

---

**Fin del Reporte Bloque 1**
**Estado:** ✅ Completado - Listo para Bloque 2 (Endurecimiento)

---

*Generado automáticamente por Cascade - Auditoría PRISLAB SaaS*
