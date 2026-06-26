"""
core/context_processors.py
═══════════════════════════════════════════════════════════════════════════════
PRISLAB V6.0 — Context Processors Multi-Tenant

Inyecta en TODOS los templates:
  - empresa_actual       → Instancia de Empresa del usuario en sesión
  - configuracion_modulos → ConfiguracionModulos del tenant
  - modulos_activos      → Dict {str: bool} de módulos activos
  - empresa_color_primario, empresa_color_secundario → Para CSS inline
  - tenant_logo_url      → URL del logo del tenant
  - is_sandbox_mode      → True si PRISLAB_DEPLOYMENT_MODE=training_sandbox (Punto 23)
═══════════════════════════════════════════════════════════════════════════════
"""
from django.conf import settings
import logging


def empresa_actual(request):
    """
    Context processor principal — inyecta identidad y módulos del tenant.
    """
    empresa = getattr(request, 'empresa_actual', None)
    modulos = getattr(request, 'modulos_activos', {})

    configuracion_modulos = None
    if empresa:
        configuracion_modulos = getattr(empresa, 'configuracion_modulos', None)

    # Variables CSS del tenant
    color_primario   = getattr(empresa, 'color_primario',   '#003366') if empresa else '#003366'
    color_secundario = getattr(empresa, 'color_secundario', '#FFD700') if empresa else '#FFD700'
    color_fondo      = getattr(empresa, 'color_fondo',      '#F8F9FA') if empresa else '#F8F9FA'

    # URL logo
    logo_url = ''
    if empresa:
        logo = getattr(empresa, 'logo', None)
        if logo and hasattr(logo, 'url'):
            try:
                logo_url = logo.url
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en empresa_actual (context_processors.py)")
                pass

    return {
        'empresa_actual':         empresa,
        'configuracion_modulos':  configuracion_modulos,
        'modulos_activos':        modulos,

        # Identidad visual
        'empresa_color_primario':   color_primario,
        'empresa_color_secundario': color_secundario,
        'empresa_color_fondo':      color_fondo,
        'empresa_css':              getattr(empresa, 'css_personalizado', '') if empresa else '',
        'tenant_logo_url':          logo_url,
        'tenant_nombre':            getattr(empresa, 'nombre', 'PRISLAB') if empresa else 'PRISLAB',
        'is_sandbox_mode':          getattr(settings, 'IS_SANDBOX', False),
    }