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

from django.conf import settings
from django.core.exceptions import PermissionDenied

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
      1. Almacena request en thread-local (para senales/servicios).
      2. Resuelve la Empresa del usuario autenticado.
      3. Resuelve la Sucursal del usuario (user.sucursal o header X-Sucursal-ID).
      4. Inyecta request.empresa_actual y request.sucursal_actual.
      5. Llama set_current_empresa() y set_current_sucursal() para el ORM.
      6. Limpia SIEMPRE en el finally (evita fuga entre hilos en pools).
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
                if (
                    empresa is None
                    and not request.user.is_superuser
                    and getattr(settings, 'PRISLAB_TENANT_STRICT_MODE', False)
                ):
                    logger.critical(
                        'TENANT_STRICT_MODE_BLOCK middleware user=%s path=%s '
                        'sin empresa asignada ni empresa por defecto resolvible.',
                        getattr(request.user, 'username', '?'),
                        getattr(request, 'path', ''),
                    )
                    raise PermissionDenied(
                        'Usuario autenticado sin empresa asignada. '
                        'Acceso bloqueado por PRISLAB_TENANT_STRICT_MODE.'
                    )

            request.empresa_actual = empresa

            # ── Resolver sucursal del usuario ───────────────────────────────
            sucursal = None
            if empresa and getattr(request, 'user', None) and getattr(request.user, 'is_authenticated', False):
                user = request.user

                # 1. Override explícito por header (APIs, mobile, Postman)
                #    X-Sucursal-ID: <pk>  — solo si la sucursal pertenece al mismo tenant Y usuario tiene acceso
                header_suc_id = request.META.get('HTTP_X_SUCURSAL_ID', '').strip()
                if header_suc_id and header_suc_id.isdigit():
                    try:
                        from core.models import Sucursal as SucursalModel
                        from core.rbac.permissions import check_sucursal_assignment
                        header_suc_id_int = int(header_suc_id)
                        suc_from_header = SucursalModel.objects.filter(
                            pk=header_suc_id_int,
                            empresa=empresa,
                            activa=True,
                        ).first()
                        if suc_from_header:
                            # Validar que el usuario tiene acceso a esta sucursal
                            if check_sucursal_assignment(user, header_suc_id_int):
                                sucursal = suc_from_header
                                logger.debug(
                                    'SUCURSAL_HEADER: user=%s sucursal_id=%s empresa=%s',
                                    getattr(user, 'username', '?'),
                                    header_suc_id, empresa.pk,
                                )
                            else:
                                logger.warning(
                                    'SUCURSAL_HEADER_DENIED: user=%s sucursal_id=%s — usuario no tiene acceso asignado.',
                                    getattr(user, 'username', '?'),
                                    header_suc_id,
                                )
                        else:
                            logger.warning(
                                'SUCURSAL_HEADER_INVALID: user=%s sucursal_id=%s '
                                'no pertenece al tenant empresa=%s o esta inactiva.',
                                getattr(user, 'username', '?'),
                                header_suc_id, empresa.pk,
                            )
                    except Exception as exc:
                        logger.error('SUCURSAL_HEADER error: %s', exc)

                # 2. Si no hay header: intentar obtener la primera sucursal asignada del usuario
                #    (relación M2M Usuario_Sucursal)
                if sucursal is None:
                    try:
                        from core.rbac.permissions import _has_permission
                        # Si el usuario tiene permiso de ver todas las sucursales,
                        # se usa un criterio por defecto (primera de la empresa)
                        if _has_permission(user, "tenant:all_branches_view"):
                            # Usar la primera sucursal activa de la empresa
                            sucursal = empresa.sucursales.filter(activa=True).first()
                        else:
                            # Obtener la primera sucursal asignada al usuario vía M2M
                            sucursal = user.sucursales.filter(
                                asignaciones_usuario__activa=True,
                                activa=True,
                            ).order_by('asignaciones_usuario__fecha_asignacion').first()
                    except Exception:
                        logger.exception(
                            'Error inesperado resolviendo sucursal M2M para user=%s',
                            getattr(user, 'username', '?')
                        )

            request.sucursal_actual = sucursal

            # ── Inyectar en TenantManager ORM ───────────────────────────────
            # Nota: superusuarios ven todo (empresa=None → no hay filtro ORM).
            # Para el Admin, esto es correcto: el superusuario de PRISLAB
            # necesita gestionar todos los tenants.
            if empresa and not request.user.is_superuser:
                from core.tenant import set_current_empresa, set_current_sucursal
                set_current_empresa(empresa)
                set_current_sucursal(sucursal)  # None si usuario sin sucursal asignada
            else:
                from core.tenant import set_current_empresa, set_current_sucursal
                set_current_empresa(None)
                set_current_sucursal(None)

            # ── Inyectar modulos activos en request (para templates) ────────
            request.modulos_activos = _get_modulos_activos(empresa)

            # ── v8.5: bypass de emergencia (DRP — sin reinstalar) ───────────
            # Si PRISLAB_EMERGENCY_TENANT_BYPASS=1, TenantManager no filtra por empresa.
            emergency = _env_truthy('PRISLAB_EMERGENCY_TENANT_BYPASS')
            if emergency and getattr(settings, 'DEBUG', False):
                from core.tenant import set_tenant_bypass
                set_tenant_bypass(True)
                logger.critical(
                    'PRISLAB_EMERGENCY_TENANT_BYPASS activo — filtro tenant ORM desactivado '
                    '(solo DEBUG). Desactivar en cuanto sea seguro.'
                )
            elif emergency:
                logger.error(
                    'PRISLAB_EMERGENCY_TENANT_BYPASS ignorado fuera de DEBUG '
                    '(protección de producción).'
                )

            response = self.get_response(request)
            return response

        finally:
            # Siempre limpiar para evitar fuga de datos entre hilos del pool
            try:
                from core.tenant import set_tenant_bypass
                set_tenant_bypass(False)
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en __call__ (empresa.py)")
                pass
            set_current_request(None)
            try:
                from core.tenant import clear_current_empresa, clear_current_sucursal
                clear_current_empresa()
                clear_current_sucursal()
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en __call__ (empresa.py)")
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
        logging.getLogger(__name__).exception("Error inesperado en _get_modulos_activos (empresa.py)")
        return _todos_activos()


def _todos_activos() -> dict:
    """Devuelve todos los módulos como True (modo sin restricciones)."""
    return {
        'laboratorio': True, 'farmacia': True, 'expediente': True,
        'consultorio': True, 'hospitalizacion': True, 'citas': True,
        'rrhh': True, 'contabilidad': True, 'ia': True, 'iot': True,
        'bienestar': True, 'nomina': True, 'war_room': True,
    }