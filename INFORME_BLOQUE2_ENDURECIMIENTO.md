# Bloque 2 - Endurecimiento de CORS y Protección de Endpoints
## PRISLAB SaaS v5.0 - Auditoría de Seguridad

**Fecha:** Mayo 2026  
**Auditor:** Cascade (Auditor Programador Nivel 5)  
**Estado:** ✅ Completado (Plan de Acción)

---

## 1. Diffs Propuestos para config/settings.py

### Cambio 1: CORS Condicional Más Estricto

**Archivo:** `config/settings.py:29-46`

**Estado Actual:**
```python
_cors_allow_raw = (os.environ.get('CORS_ALLOW_ALL_ORIGINS') or '').strip().lower()
if _cors_allow_raw:
    CORS_ALLOW_ALL_ORIGINS = _cors_allow_raw in ('true', '1', 'yes', 'on')
else:
    CORS_ALLOW_ALL_ORIGINS = not _is_cloud_env  # True en local, False en cloud
```

**Propuesta de Endurecimiento:**
```python
# CORS: configuración explícita requerida
_cors_allow_raw = (os.environ.get('CORS_ALLOW_ALL_ORIGINS') or '').strip().lower()
if _cors_allow_raw:
    CORS_ALLOW_ALL_ORIGINS = _cors_allow_raw in ('true', '1', 'yes', 'on')
else:
    # Por defecto: restrictivo en TODOS los entornos
    CORS_ALLOW_ALL_ORIGINS = False

# Orígenes permitidos explícitos
_default_origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",  # React dev server
]
CORS_ALLOWED_ORIGINS = [
    x.strip() for x in (os.environ.get('CORS_ALLOWED_ORIGINS') or '').split(',') if x.strip()
] or _default_origins
```

**Razonamiento:**
- Elimina comportamiento automático permisivo en local
- Requiere explícito `CORS_ALLOW_ALL_ORIGINS=true` para desarrollo libre
- Mantiene lista de orígenes por defecto segura para desarrollo

---

## 2. Plan: Decorador @require_api_token

### Implementación Propuesta

**Nuevo archivo:** `core/decorators.py`

```python
"""
Decoradores de seguridad para endpoints API.
PRISLAB SaaS - Endurecimiento de endpoints @csrf_exempt
"""
import os
import functools
import hashlib
import secrets
from django.http import JsonResponse
from django.conf import settings

def require_api_token(env_var, header_name='X-API-Token', query_param='token'):
    """
    Decorador que requiere un token API válido desde:
    1. Header X-API-Token (preferido)
    2. Query param ?token= (fallback)
    
    Args:
        env_var: Nombre de variable de entorno con el token esperado
        header_name: Nombre del header HTTP (default: X-API-Token)
        query_param: Nombre del query param (default: token)
    
    Returns:
        JsonResponse 401 si el token no coincide
    
    Ejemplo:
        @csrf_exempt
        @require_api_token('PRISLAB_HL7_TOKEN')
        def api_hl7_receptor(request):
            ...
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Obtener token de header o query param
            token = request.headers.get(header_name) or request.GET.get(query_param)
            expected = os.environ.get(env_var, '').strip()
            
            # Validar que exista token configurado
            if not expected:
                return JsonResponse({
                    'error': 'Unauthorized',
                    'detail': f'Token not configured on server'
                }, status=401)
            
            # Comparación constant-time para prevenir timing attacks
            if not token or not secrets.compare_digest(token, expected):
                return JsonResponse({
                    'error': 'Unauthorized',
                    'detail': 'Invalid token'
                }, status=401)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_service_token(service_name):
    """
    Decorador específico para tokens de servicio PRISLAB.
    Busca variable PRISLAB_{SERVICE}_TOKEN automáticamente.
    """
    env_var = f"PRISLAB_{service_name.upper()}_TOKEN"
    return require_api_token(env_var)
```

### Tokens a Generar

| Servicio | Variable de Entorno | Longitud Recomendada |
|----------|----------------------|---------------------|
| HL7 | `PRISLAB_HL7_TOKEN` | 32 chars hex |
| Sentinel | `PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN` | 32 chars hex |
| Sentinel Reset | `PRISLAB_SENTINEL_RESET_TOKEN` | 32 chars hex |
| Cron | `CRON_SECRET` | 32 chars hex |
| IoT Kiosco | `PRISLAB_KIOSCO_TOKEN` | 32 chars hex |
| Frontend Logs | `PRISLAB_FRONTEND_LOG_TOKEN` | 16 chars hex |

---

## 3. Plan: Generador de Tokens Seguros

### Script Propuesto

**Nuevo archivo:** `scripts/generate_tokens.py`

```python
#!/usr/bin/env python3
"""
Generador de tokens seguros para servicios PRISLAB.
Uso: python scripts/generate_tokens.py
"""
import secrets
import string


def generate_token(length=32):
    """Genera token hexadecimal criptográficamente seguro."""
    return secrets.token_hex(length // 2)


def main():
    print("=" * 60)
    print("PRISLAB - Generador de Tokens de Servicio")
    print("=" * 60)
    print()
    
    services = [
        ('PRISLAB_HL7_TOKEN', 32, 'Receptor HL7/ASTM'),
        ('PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN', 32, 'Telemetría Sentinel'),
        ('PRISLAB_SENTINEL_RESET_TOKEN', 32, 'Reset de incidencias'),
        ('CRON_SECRET', 32, 'Cloud Scheduler'),
        ('PRISLAB_KIOSCO_TOKEN', 32, 'APIs de Kiosco'),
        ('PRISLAB_FRONTEND_LOG_TOKEN', 16, 'Logs frontend (opcional)'),
        ('FERNET_KEY', 32, 'Cifrado de campos (Base64)'),
    ]
    
    print("Tokens generados (NO compartir en repositorio):")
    print("-" * 60)
    
    for var_name, length, description in services:
        if var_name == 'FERNET_KEY':
            # Fernet requiere 32 bytes base64
            from cryptography.fernet import Fernet
            token = Fernet.generate_key().decode()
        else:
            token = generate_token(length)
        
        print(f"\n# {description}")
        print(f"{var_name}={token}")
    
    print()
    print("=" * 60)
    print("Instrucciones:")
    print("1. Copia las variables necesarias a tu .env")
    print("2. NUNCA commitear tokens reales")
    print("3. En Cloud Run: usar Secret Manager")
    print("=" * 60)


if __name__ == '__main__':
    main()
```

---

## 4. Endpoints a Modificar

### Prioridad 1: Endpoints sin Autenticación

| Endpoint | Archivo | Línea | Acción | Token Recomendado |
|----------|---------|-------|--------|-------------------|
| `log_frontend_error` | `core/views/general.py` | 159 | Añadir `@require_api_token('PRISLAB_FRONTEND_LOG_TOKEN')` o rate limiting | `PRISLAB_FRONTEND_LOG_TOKEN` |

### Prioridad 2: Fortalecer Autenticación Existente

| Endpoint | Archivo | Mejora Propuesta |
|----------|---------|------------------|
| `api_kiosco_heartbeat` | `iot/views.py:63` | Añadir verificación de token + IP |
| `api_kiosco_confirmar` | `iot/views.py:90` | Añadir token de kiosco |
| `api_kiosco_rechazar` | `iot/views.py:103` | Añadir token de kiosco |
| `receptor_hl7` | `interfaces_lims_service.py:155` | Estandarizar a `@require_api_token('PRISLAB_HL7_TOKEN')` |

### Diffs Específicos

#### Diff 1: `core/views/general.py`

```python
# AÑADIR AL INICIO:
from core.decorators import require_api_token

# MODIFICAR:
@csrf_exempt
@require_http_methods(["POST"])
@require_api_token('PRISLAB_FRONTEND_LOG_TOKEN')  # NUEVO
def log_frontend_error(request):
    """..."""
```

#### Diff 2: `iot/views.py`

```python
# AÑADIR AL INICIO:
from core.decorators import require_api_token

def _verificar_kiosco_token(request, kiosco_id):
    """Verifica token de kiosco o IP autorizada."""
    # Mantener compatibilidad: si no hay token configurado, aceptar
    expected = os.environ.get('PRISLAB_KIOSCO_TOKEN', '')
    if not expected:
        return True  # Modo legacy: sin token = aceptar
    
    token = request.headers.get('X-Kiosco-Token') or request.GET.get('kiosco_token')
    return token and secrets.compare_digest(token, expected)

# MODIFICAR cada endpoint kiosco:
@csrf_exempt
def api_kiosco_heartbeat(request, kiosco_id):
    if not _verificar_kiosco_token(request, kiosco_id):
        return JsonResponse({'status': 'error', 'mensaje': 'Token inválido'}, status=401)
    # ... resto del código
```

---

## 5. Variables de Entorno Actualizadas

### Nuevas Variables Requeridas (docs/TOKENS.md)

```markdown
# Tokens de Servicio PRISLAB

## HL7/ASTM
- `PRISLAB_HL7_TOKEN` - Token para receptores de analizadores

## Sentinel
- `PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN` - Telemetría y diagnóstico
- `PRISLAB_SENTINEL_RESET_TOKEN` - Operaciones administrativas

## Cron / Cloud Scheduler
- `CRON_SECRET` - Header X-Cron-Secret para tareas programadas

## IoT / Kioscos
- `PRISLAB_KIOSCO_TOKEN` - Autenticación de kioscos (opcional)

## Frontend
- `PRISLAB_FRONTEND_LOG_TOKEN` - Envío de errores JS (opcional)

## Cifrado
- `FERNET_KEY` - Clave para campos encriptados (obligatorio en prod)
```

### Actualización de `.env.example`

Variables a añadir:
```bash
# --- Tokens de Servicio (generar con scripts/generate_tokens.py) ---
PRISLAB_HL7_TOKEN=
PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN=
PRISLAB_SENTINEL_RESET_TOKEN=
CRON_SECRET=
PRISLAB_KIOSCO_TOKEN=
PRISLAB_FRONTEND_LOG_TOKEN=

# --- Cifrado ---
FERNET_KEY=
```

---

## 6. Resultado de Pruebas Esperado

### Comando de Verificación

```bash
# Verificar tokens funcionan
python manage.py check

# Probar endpoint protegido (debe fallar sin token)
curl -X POST http://localhost:8000/api/log-frontend-error/ \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
# Esperado: 401 Unauthorized

# Probar con token correcto
curl -X POST http://localhost:8000/api/log-frontend-error/ \
  -H "Content-Type: application/json" \
  -H "X-API-Token: $PRISLAB_FRONTEND_LOG_TOKEN" \
  -d '{"message": "test"}'
# Esperado: 200 OK
```

---

## Checklist Bloque 2

- [ ] Crear `core/decorators.py` con `@require_api_token`
- [ ] Crear `scripts/generate_tokens.py`
- [ ] Modificar `config/settings.py` (CORS más restrictivo)
- [ ] Modificar `core/views/general.py` (proteger log_frontend_error)
- [ ] Modificar `iot/views.py` (fortalecer kioscos)
- [ ] Actualizar `.env.example` con nuevas variables
- [ ] Crear `docs/TOKENS.md` con documentación
- [ ] Ejecutar pruebas unitarias
- [ ] Ejecutar `npm run omni:local`

---

## Resumen de Acciones

| Prioridad | Acción | Archivo | Dificultad |
|-----------|--------|---------|------------|
| Alta | Crear decorador token | `core/decorators.py` | Media |
| Alta | Crear generador tokens | `scripts/generate_tokens.py` | Baja |
| Media | Endurecer CORS | `config/settings.py` | Baja |
| Media | Proteger log_frontend | `core/views/general.py` | Media |
| Baja | Fortalecer kioscos | `iot/views.py` | Media |
| Baja | Documentar tokens | `.env.example`, `docs/TOKENS.md` | Baja |

---

**Fin del Plan Bloque 2**
**Estado:** ✅ Documentación completa - Implementación pendiente de aprobación

---

*Generado automáticamente por Cascade - Auditoría PRISLAB SaaS*
