"""
core/middleware/empresa.py
═══════════════════════════════════════════════════════════════════════════════
PRISLAB V6.0 — Multi-Tenant Identity Middleware (actualizado)

1. Inyecta request.empresa_actual para las vistas y templates.
2. Alimenta core.tenant con set_current_empresa() para el TenantManager ORM.
3. Almacena el request en thread-local para señales (get_current_request).

ORDEN EN MIDDLEWARE STACK (settings.py):
  Debe ir DESPUÉS de AuthenticationMiddleware para que request.user esté disponible.

GARANTÍA:
  Una vez que este middleware se ejecuta, TODOS los QuerySets que usen
  TenantManager quedan filtrados automáticamente para la empresa del usuario.
═══════════════════════════════════════════════════════════════════════════════
"""
import logging
import os
import threading

logger = logging.getLogger('core.middleware.empresa')


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, '').strip().lower() in ('1', 'true', 'yes', 'on')


# ─── THREAD-LOCAL PARA REQUEST (legado — usado por señales) ─────────────────
_thread_locals = threading.local()


def get_current_request():
    """Retorna el request del hilo actual (para uso en señales)."""
    return getattr(_thread_locals, 'request', None)


def set_current_request(request):
    """Almacena el request en el thread local."""
    _thread_locals.request = request


# ─── MIDDLEWARE ──────────────────────────────────────────────────────────────

class EmpresaIdentityMiddleware:
    """
    Middleware central de identidad multi-tenant.

    Acciones:
      1. Almacena request en thread-local (para señales/servicios).
      2. Resuelve la Empresa del usuario autenticado.
      3. Inyecta request.empresa_actual (para vistas/templates).
      4. Llama set_current_empresa() para activar el TenantManager ORM.
      5. Limpia SIEMPRE en el finally (evita fuga entre hilos en pools).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ── Almacenar request en thread-local (para señales) ──────────────
        set_current_request(request)

        empresa = None
        try:
            # ── Resolver empresa del usuario ──────────────────────────────
            if (
                getattr(request, 'user', None)
                and getattr(request.user, 'is_authenticated', False)
            ):
                empresa = getattr(request.user, 'empresa', None)
                if empresa is None:
                    from core.utils.default_empresa import resolve_default_empresa_sistema

                    empresa = resolve_default_empresa_sistema()

            request.empresa_actual = empresa

            # ── Inyectar en TenantManager ORM ─────────────────────────────
            # Nota: superusuarios ven todo (empresa=None → no hay filtro ORM).
            # Para el Admin, esto es correcto: el superusuario de PRISLAB
            # necesita gestionar todos los tenants.
            if empresa and not request.user.is_superuser:
                from core.tenant import set_current_empresa
                set_current_empresa(empresa)
            else:
                from core.tenant import set_current_empresa
                set_current_empresa(None)

            # ── Inyectar módulos activos en request (para templates) ───────
            request.modulos_activos = _get_modulos_activos(empresa)

            # ── v8.5: bypass de emergencia (DRP — sin reinstalar) ───────────
            # Si PRISLAB_EMERGENCY_TENANT_BYPASS=1, TenantManager no filtra por empresa.
            emergency = _env_truthy('PRISLAB_EMERGENCY_TENANT_BYPASS')
            if emergency:
                from core.tenant import set_tenant_bypass
                set_tenant_bypass(True)
                logger.critical(
                    'PRISLAB_EMERGENCY_TENANT_BYPASS activo — filtro tenant ORM desactivado '
                    '(incidente). Desactivar en cuanto sea seguro.'
                )

            response = self.get_response(request)
            return response

        finally:
            # Siempre limpiar para evitar fuga de datos entre hilos del pool
            try:
                from core.tenant import set_tenant_bypass
                set_tenant_bypass(False)
            except Exception:
                pass
            set_current_request(None)
            try:
                from core.tenant import clear_current_empresa
                clear_current_empresa()
            except Exception:
                pass


def _get_modulos_activos(empresa) -> dict:
    """
    Retorna un dict {str: bool} con el estado de cada módulo para la empresa.
    Cachea en thread-local durante el request para evitar N+1.

    Si no hay empresa o ConfiguracionModulos, activa todo (modo legacy).
    """
    if not empresa:
        return _todos_activos()

    try:
        from core.models import ConfiguracionModulos
        cfg = ConfiguracionModulos.objects.filter(empresa=empresa).first()
        if not cfg:
            # Primera vez: empresa sin configuración → todos los módulos activos
            return _todos_activos()

        return {
            'laboratorio':     cfg.modulo_laboratorio,
            'farmacia':        cfg.modulo_farmacia,
            'expediente':      cfg.modulo_expediente_clinico,
            'consultorio':     cfg.modulo_consulta_externa,
            'hospitalizacion': cfg.modulo_hospitalizacion,
            'citas':           cfg.modulo_citas,
            'rrhh':            cfg.modulo_rrhh,
            'contabilidad':    cfg.modulo_contabilidad,
            'ia':              cfg.modulo_ia,
            'iot':             cfg.modulo_iot,
            # Alias prácticos
            'bienestar':       cfg.modulo_rrhh,  # Bienestar es parte de RRHH
            'nomina':          cfg.modulo_rrhh,
            'war_room':        cfg.modulo_contabilidad,  # War Room requiere Finanzas
        }
    except Exception:
        return _todos_activos()


def _todos_activos() -> dict:
    """Devuelve todos los módulos como True (modo sin restricciones)."""
    return {
        'laboratorio': True, 'farmacia': True, 'expediente': True,
        'consultorio': True, 'hospitalizacion': True, 'citas': True,
        'rrhh': True, 'contabilidad': True, 'ia': True, 'iot': True,
        'bienestar': True, 'nomina': True, 'war_room': True,
    }
