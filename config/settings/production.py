"""
config/settings/production.py

Overrides y validaciones de seguridad para entorno de producción.
Solo se activa cuando DEPLOYMENT_ENV == 'production'.
"""
import logging
import os

_log_prod = logging.getLogger('config')

# ── SSL y cookies seguras ─────────────────────────────────────────────────────
# Sobrescribe los valores por defecto de base.py / security.py
_e2e_disable_ssl = os.environ.get('E2E_DISABLE_SSL', '') == '1'
_testing = 'test' in __import__('sys').argv or os.environ.get('DJANGO_TESTING', '') == 'True'

if not _e2e_disable_ssl and not _testing:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# En producción el Admin requiere el grupo explícito de administración.
# Los superusuarios conservan acceso para las tareas de plataforma.
ADMIN_GROUP_RESTRICTION_ENABLED = os.environ.get(
    'ADMIN_GROUP_RESTRICTION_ENABLED', 'True'
).lower() in ('true', '1', 'yes')

_admin_ip_restriction = os.environ.get(
    'ADMIN_IP_RESTRICTION_ENABLED', 'False'
).lower() in ('true', '1', 'yes')
_allowed_admin_ips = [
    value.strip()
    for value in os.environ.get('ALLOWED_ADMIN_IPS', '').split(',')
    if value.strip()
]
if _admin_ip_restriction and not _allowed_admin_ips:
    raise RuntimeError(
        'ADMIN_IP_RESTRICTION_ENABLED requiere ALLOWED_ADMIN_IPS en producción.'
    )
ADMIN_IP_RESTRICTION_ENABLED = _admin_ip_restriction
ALLOWED_ADMIN_IPS = _allowed_admin_ips

# ── ALLOWED_HOSTS ─────────────────────────────────────────────────────────────
_server_name = (os.environ.get('SERVER_NAME') or os.environ.get('DOMAIN_NAME') or '').strip()
if not _server_name:
    raise RuntimeError('SERVER_NAME/DOMAIN_NAME es obligatorio en producción.')
ALLOWED_HOSTS = [_server_name]

# ── Validaciones de arranque ──────────────────────────────────────────────────
_log_sec = logging.getLogger('core.seguridad.startup')

# HC-1: PRISLAB_EMERGENCY_TENANT_BYPASS no debe estar activo en producción.
if os.environ.get('PRISLAB_EMERGENCY_TENANT_BYPASS', '').strip().lower() in ('1', 'true', 'yes', 'on'):
    raise RuntimeError(
        'PRISLAB_EMERGENCY_TENANT_BYPASS no puede estar activo en producción.'
    )

# HC-2: PRISLAB_DEFAULT_EMPRESA_ID debe estar configurado.
if not os.environ.get('PRISLAB_DEFAULT_EMPRESA_ID', '').strip():
    _log_sec.warning(
        'PRISLAB_DEFAULT_EMPRESA_ID no está configurado. '
        'En entornos con múltiples empresas, usuarios sin empresa asignada serán bloqueados '
        'si PRISLAB_TENANT_STRICT_MODE está activo.'
    )
