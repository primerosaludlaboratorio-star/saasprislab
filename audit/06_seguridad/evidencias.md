# Evidencias de Seguridad — PRISLAB SaaS

**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## EV-SEC-001 — Validación de SECRET_KEY en producción

**Criticidad:** ALTA  
**Archivo:** `config/settings.py`  
**Línea:** 50-186  
**Clase/Función:** Módulo de configuración global  
**Fragmento:**
```python
_SECRET_KEY_ENV = os.environ.get('SECRET_KEY', '').strip()
if not _SECRET_KEY_ENV:
    # Fallback solo en desarrollo local — NUNCA usar en produccion
    _SECRET_KEY_ENV = 'dev-only-fallback-key-not-for-production-prislab-2026-local'
SECRET_KEY = _SECRET_KEY_ENV

_CLAVES_INSEGURAS = {
    'django-insecure-prislab-saas-key-2025',
    'dev-only-fallback-key-not-for-production-prislab-2026-local',
    'generate-a-random-key-here-min-50-chars',
    '4k*0c0z8gacu(%_)ug*y*t9xp*u55(u*$rv+pou#b=#o!4p4eo',
}
if IS_PRODUCTION:
    if not os.environ.get('SECRET_KEY') or SECRET_KEY in _CLAVES_INSEGURAS:
        raise RuntimeError(
            '🔴 PRISLAB SEGURIDAD: SECRET_KEY no está configurada o usa un valor inseguro en producción.\n'
            'Defina la variable de entorno SECRET_KEY con una clave segura de al menos 50 caracteres.\n'
            'Genere una con: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
        )
    if len(SECRET_KEY) < 50:
        raise RuntimeError(
            '🔴 PRISLAB SEGURIDAD: SECRET_KEY en producción debe tener al menos 50 caracteres.'
        )
```
**Explicación:** Existe un fallback hardcodeado para desarrollo, pero el sistema lanza excepción en producción si SECRET_KEY no está configurada, si usa un valor inseguro conocido o si tiene menos de 50 caracteres. Es una buena práctica defensiva, aunque la clave de fallback está visible en el repositorio.
**Confianza:** ★★★★☆ (código)
**Riesgos:** La clave de desarrollo hardcodeada podría usarse accidentalmente en producción si se desactivan las validaciones o se usa `DEBUG=True`.
**Estado:** FUNCIONAL PARCIAL

---

## EV-SEC-002 — Tokens de servicio requeridos en producción

**Criticidad:** ALTA  
**Archivo:** `config/settings.py`  
**Línea:** 192-204  
**Fragmento:**
```python
    _TOKENS_REQUERIDOS = {
        'PRISLAB_API_TOKEN': os.environ.get('PRISLAB_API_TOKEN', ''),
        'PRISLAB_FRONTEND_LOG_TOKEN': os.environ.get('PRISLAB_FRONTEND_LOG_TOKEN', ''),
        'CRON_SECRET': os.environ.get('CRON_SECRET', ''),
    }
    _tokens_faltantes = [k for k, v in _TOKENS_REQUERIDOS.items() if not v or v.startswith('replace-with')]
    if _tokens_faltantes:
        import logging as _log_tok
        _log_tok.getLogger('core').warning(
            f'🔴 PRISLAB SEGURIDAD: Tokens de servicio no configurados en produccion: {_tokens_faltantes}. '
            'Los endpoints protegidos por estos tokens retornarán 503.'
        )
```
**Explicación:** Se validan tokens de servicio en producción, pero solo se emiten warnings (no se bloquea el arranque). Los endpoints protegidos retornarán 503 si faltan.
**Confianza:** ★★★★☆ (código)
**Riesgos:** Si un administrador no revisa logs, el sistema puede arrancar con endpoints no funcionales.
**Estado:** FUNCIONAL PARCIAL

---

## EV-SEC-003 — Configuración CORS restrictiva por defecto

**Criticidad:** MEDIA  
**Archivo:** `config/settings.py`  
**Línea:** 125-148  
**Fragmento:**
```python
if _cors_allow_raw:
    CORS_ALLOW_ALL_ORIGINS = _cors_allow_raw in ('true', '1', 'yes', 'on')
else:
    CORS_ALLOW_ALL_ORIGINS = False

_default_local_cors_origins = (
    'http://127.0.0.1:8000,http://localhost:8000,'
    'http://127.0.0.1:3000,http://localhost:3000'
)
_cors_origins_raw = os.environ.get('CORS_ALLOWED_ORIGINS')
if _cors_origins_raw is None and not IS_PRODUCTION:
    _cors_origins_raw = _default_local_cors_origins
CORS_ALLOWED_ORIGINS = [
    x.strip() for x in (_cors_origins_raw or '').split(',') if x.strip()
]
if IS_PRODUCTION and not CORS_ALLOW_ALL_ORIGINS and not CORS_ALLOWED_ORIGINS:
    logging.getLogger('config').warning(
        'CORS: en producción CORS_ALLOW_ALL_ORIGINS está en False y CORS_ALLOWED_ORIGINS está vacío. '
        'Las peticiones desde otros orígenes pueden fallar. '
        'Defina CORS_ALLOWED_ORIGINS o, temporalmente, CORS_ALLOW_ALL_ORIGINS=true.'
    )
```
**Explicación:** CORS está desactivado por defecto (`CORS_ALLOW_ALL_ORIGINS=False`). En desarrollo se permite localhost. En producción se requiere configuración explícita. Se advierte si falta configuración.
**Confianza:** ★★★★☆ (código)
**Riesgos:** Ninguno crítico si se configura correctamente en producción.
**Estado:** IMPLEMENTADO

---

## EV-SEC-004 — Middleware de seguridad presentes

**Criticidad:** ALTA  
**Archivo:** `config/settings.py`  
**Línea:** 252-285  
**Fragmento:**
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'core.middleware.sre_metrics.SreMetricsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.canonical_host.CanonicalHostMiddleware',
    'core.api_contracts.middleware.ApiRequestIdMiddleware',
    'core.middleware.read_only.ReadOnlyMiddleware',
    'core.middleware.admin_access.AdminAccessMiddleware',
    'core.middleware.rate_limit.RateLimitMiddleware',
    'core.middleware.tenant_subdomain.TenantSubdomainMiddleware',
    'core.middleware.EmpresaIdentityMiddleware',
    'core.middleware.feature_flags.FeatureFlagMiddleware',
    'core.middleware.json_response.JSONResponseMiddleware',
    'core.middleware.actividad_usuario.ActividadUsuarioMiddleware',
    'core.middleware.sentinel.SentinelTelemetryMiddleware',
    'core.middleware.performance.PerformanceMiddleware',
    'core.middleware.pris_context.PrisContextMiddleware',
    'core.middleware.mantenimiento.MaintenanceModeMiddleware',
    'core.middleware.seguridad.SessionTimeoutMiddleware',
    'core.middleware.seguridad.TenantStorageMiddleware',
    'core.middleware.blindaje_expediente.BlindajeExpedienteMiddleware',
    'core.middleware.blindaje_expediente.SnapshotMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```
**Explicación:** El stack incluye múltiples capas de seguridad: CSRF, autenticación, rate limiting, control de acceso a /admin, timeout de sesión, blindaje de expedientes, canonical host, y tenant isolation.
**Confianza:** ★★★☆☆ (código, no se verificó ejecución de cada middleware)
**Riesgos:** Gran cantidad de middlewares custom puede aumentar latencia e introducir efectos secundarios difíciles de depurar. Cada middleware es un punto de falla.
**Estado:** IMPLEMENTADO

---

## EV-SEC-005 — Cookies y headers de seguridad

**Criticidad:** MEDIA  
**Archivo:** `config/settings.py`  
**Línea:** 809-840  
**Fragmento:**
```python
if IS_PRODUCTION:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', IS_PRODUCTION)
CSRF_COOKIE_SECURE = _env_bool('CSRF_COOKIE_SECURE', IS_PRODUCTION)
SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

PERMISSIONS_POLICY = {
    'geolocation': [],
    'camera': [],
    'microphone': [],
    'payment': [],
    'usb': [],
    'fullscreen': ['self'],
}

SECURE_HSTS_SECONDS = int(os.environ.get(
    'SECURE_HSTS_SECONDS',
    '31536000' if IS_PRODUCTION else '0',
))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', IS_PRODUCTION)
SECURE_HSTS_PRELOAD = _env_bool('SECURE_HSTS_PRELOAD', IS_PRODUCTION)
```
**Explicación:** Headers de seguridad configurados: HSTS, X-Frame-Options DENY, cookies seguras en producción, referrer policy, permissions policy. `SECURE_SSL_REDIRECT` es `False` por defecto, requiere activación explícita.
**Confianza:** ★★★★☆ (código)
**Riesgos:** `SECURE_SSL_REDIRECT=False` por defecto puede permitir tráfico HTTP si Nginx no fuerza HTTPS.
**Estado:** IMPLEMENTADO

---

## EV-SEC-006 — Branch protection bypass visible

**Criticidad:** CRÍTICA  
**Archivo:** N/A (configuración de GitHub)  
**Línea:** N/A  
**Explicación:** En múltiples operaciones de push a `release/v1.0-local`, GitHub reportó:
```
remote: Bypassed rule violations for refs/heads/release/v1.0-local:
remote: - Changes must be made through a pull request.
```
Esto indica que la regla de branch protection existe pero está siendo bypassada (probablemente por permisos de administrador en el token usado).
**Confianza:** ★★★★★ (output real de git push)
**Riesgos:** Push directo a branch crítica sin PR permite introducir errores sin revisión. También evita los status checks obligatorios.
**Estado:** FUNCIONAL PARCIAL
**Evidencia de push:** Varios commits en `release/v1.0-local` mostraron este mensaje durante la sesión de auditoría.

---

## EV-SEC-007 — Secret scanning con gitleaks

**Criticidad:** ALTA  
**Archivo:** `.github/workflows/secret-scan.yml`  
**Línea:** 1-40  
**Fragmento:**
```yaml
name: Secret Scan
on:
  push:
    branches: [main, release/*]
  pull_request:
    branches: [main, release/*]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: '0'
      - name: gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}
```
**Explicación:** Existe workflow de secret scanning con gitleaks en push/PR a ramas main y release/*.
**Confianza:** ★★★★☆ (código)
**Riesgos:** Requiere que `GITLEAKS_LICENSE` esté configurado. Sin él, el workflow fallará.
**Estado:** IMPLEMENTADO

---

## EV-SEC-008 — Variables de entorno documentadas

**Criticidad:** INFORMATIVA  
**Archivo:** `.env.example`, `.env.staging.example`, `.env.production.example`  
**Explicación:** Existen archivos de ejemplo documentando variables requeridas: DB_*, SECRET_KEY, FERNET_KEY, API keys, Redis, email, etc. No contienen valores secretos reales.
**Confianza:** ★★★★☆ (código)
**Riesgos:** Ninguno si se configuran correctamente en el entorno de producción.
**Estado:** IMPLEMENTADO

---

## EV-SEC-009 — Dependencias con actualizaciones pendientes

**Criticidad:** MEDIA  
**Archivo:** `requirements.txt` / PRs dependabot  
**Explicación:** Existen PRs de dependabot pendientes:
- `#13` — Pillow update
- `#35` — google-genai update
- `gitleaks-action` 2 → 3
- `actions/upload-artifact` 4 → 7
**Confianza:** ★★★★☆ (observado en branches remotos)
**Riesgos:** Mantener dependencias desactualizadas puede exponer vulnerabilidades conocidas. Pillow y google-genai son usados para generación de PDFs e integraciones IA.
**Estado:** FUNCIONAL PARCIAL

---

## EV-SEC-011 — Correcciones aplicadas a `config/settings.py`

**Criticidad:** ALTA  
**Archivo:** `config/settings.py`  
**Estado:** CORREGIDO  
**Cambios realizados:**

1. **H-002 — SECRET_KEY hardcodeado**: se eliminó el fallback literal. Ahora:
   - En producción (`IS_PRODUCTION=True`), si `SECRET_KEY` no está configurada → `RuntimeError`.
   - En dev/test, si no está configurada, se genera una clave aleatoria efímera con `secrets.token_urlsafe(64)` y se advierte.

2. **H-003 — DB_HOST obligatorio en producción**: se agregó validación que lanza `RuntimeError` si `DB_HOST` no está configurado en producción, evitando el fallback silencioso a SQLite.

3. **H-004 — Tokens de servicio como error**: los tokens `PRISLAB_API_TOKEN`, `PRISLAB_FRONTEND_LOG_TOKEN`, `CRON_SECRET` ahora lanzan `RuntimeError` si faltan en producción.

4. **H-006 — `SECURE_SSL_REDIRECT` por defecto en producción**: el default pasó de `False` a `IS_PRODUCTION`.

5. **H-011 — CORS en producción**: ahora se lanza `RuntimeError` si `CORS_ALLOW_ALL_ORIGINS=False` y `CORS_ALLOWED_ORIGINS` está vacío en producción.

**Validación:** `python manage.py check` se ejecutó sin errores después de los cambios.

---

## EV-SEC-010 — Auth: uso de AUTH_USER_MODEL custom

**Criticidad:** MEDIA  
**Archivo:** `config/settings.py`  
**Línea:** 368  
**Fragmento:**
```python
AUTH_USER_MODEL = 'core.Usuario'
```
**Explicación:** El sistema usa un modelo de usuario custom (`core.Usuario`), lo cual es correcto para un sistema multi-tenant, pero requiere que todas las referencias a User usen `get_user_model()` o `settings.AUTH_USER_MODEL`.
**Confianza:** ★★★★☆ (código)
**Riesgos:** Referencias directas a `User` de Django en lugar de `Usuario` pueden causar inconsistencias. Debe verificarse en el codebase.
**Estado:** IMPLEMENTADO
