# core/rbac/permissions.py
# ==============================================================================
# PRISLAB SaaS — RBAC: Roles, Permisos y Decoradores
# ==============================================================================
# Estructura de roles (inmutable por diseño):
#
#   SUPERADMIN       → acceso total, cross-tenant, solo is_superuser=True
#   ADMIN_EMPRESA    → administra su tenant: usuarios, configuración, reportes
#   DIRECTOR         → lectura total de su tenant + war room + finanzas
#   QUIMICO_MEDICO   → captura y valida resultados, consultorio, expediente
#   CAJA_RECEPCION   → PDV, recepción de pacientes, caja. SIN acceso a medical
#
# Criterio de Validación (Pasa/No Pasa):
#   - Si el rol no está en allowed_roles → HTTP 403, log de intento.
#   - Caja/Recepción nunca puede tocar endpoints de resultados o admin.
#   - Los permisos son inmutables: no se pueden delegar en runtime.
# ==============================================================================

from __future__ import annotations
import logging
from functools import wraps
from typing import Sequence

from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

logger = logging.getLogger("core.rbac")


# ── Constantes de roles ───────────────────────────────────────────────────────

class Rol:
    """Fuente única de verdad para los nombres de rol del sistema."""
    SUPERADMIN      = "SUPERADMIN"       # Solo Django is_superuser
    ADMIN           = "ADMIN"            # Admin_Empresa
    DIRECTOR        = "DIRECTOR"
    GERENTE         = "GERENTE"
    QUIMICO         = "QUIMICO"
    MEDICO          = "MEDICO"
    CAJA            = "CAJERO"
    RECEPCION       = "RECEPCION"

    # Grupos funcionales (para decoradores)
    MEDICOS         = {QUIMICO, MEDICO}
    ADMINISTRATIVOS = {ADMIN, DIRECTOR, GERENTE}
    OPERATIVOS      = {CAJA, RECEPCION}
    TODOS_TENANT    = {ADMIN, DIRECTOR, GERENTE, QUIMICO, MEDICO, CAJA, RECEPCION}


# ── Mapa de permisos por módulo ───────────────────────────────────────────────
# Cada entrada define qué roles pueden acceder.
# Política: whitelist estricta. Si el rol no está → denegado.

PERMISSION_MAP: dict[str, frozenset[str]] = {
    # Laboratorio — resultados y validación: solo personal clínico
    "lab:captura_resultados":    frozenset({Rol.QUIMICO}),
    "lab:validar_resultados":    frozenset({Rol.QUIMICO}),
    "lab:ver_ordenes":           frozenset({Rol.QUIMICO, Rol.MEDICO, Rol.ADMIN, Rol.DIRECTOR, Rol.GERENTE}),
    "lab:imprimir_resultados":   frozenset({Rol.QUIMICO, Rol.MEDICO, Rol.RECEPCION, Rol.CAJA, Rol.ADMIN}),

    # Consultorio — expediente clínico: solo médicos y quimicos
    "consultorio:nueva_consulta": frozenset({Rol.MEDICO}),
    "consultorio:ver_expediente": frozenset({Rol.MEDICO, Rol.QUIMICO, Rol.ADMIN, Rol.DIRECTOR}),
    "consultorio:modificar_dx":   frozenset({Rol.MEDICO}),

    # Caja / PDV — solo operativos y admin
    "caja:registrar_venta":      frozenset({Rol.CAJA, Rol.RECEPCION, Rol.ADMIN}),
    "caja:cancelar_venta":       frozenset({Rol.ADMIN, Rol.DIRECTOR}),
    "caja:ver_corte":            frozenset({Rol.CAJA, Rol.RECEPCION, Rol.ADMIN, Rol.DIRECTOR, Rol.GERENTE}),
    "caja:devolucion":           frozenset({Rol.ADMIN, Rol.DIRECTOR}),

    # Farmacia
    "farmacia:ver_inventario":   frozenset(Rol.TODOS_TENANT),
    "farmacia:ajustar_stock":    frozenset({Rol.ADMIN, Rol.DIRECTOR, Rol.GERENTE}),
    "farmacia:compras":          frozenset({Rol.ADMIN, Rol.DIRECTOR}),

    # Finanzas / War Room — solo dirección
    "finanzas:ver_reportes":     frozenset({Rol.ADMIN, Rol.DIRECTOR, Rol.GERENTE}),
    "finanzas:ver_costos":       frozenset({Rol.ADMIN, Rol.DIRECTOR}),
    "finanzas:exportar":         frozenset({Rol.ADMIN, Rol.DIRECTOR}),

    # Administración de usuarios — solo admin de la empresa
    "admin:gestionar_usuarios":  frozenset({Rol.ADMIN}),
    "admin:ver_config":          frozenset({Rol.ADMIN, Rol.DIRECTOR}),
    "admin:cambiar_plan":        frozenset({Rol.ADMIN}),

    # IA — nivel controlado por campo nivel_ia del usuario (ver decorador)
    "ia:usar_basica":            frozenset(Rol.TODOS_TENANT),
    "ia:usar_negocios":          frozenset({Rol.ADMIN, Rol.DIRECTOR, Rol.GERENTE}),

    # CAJA/RECEPCIÓN — explícitamente denegado de endpoints críticos
    # (definición negativa para documentación; el whitelist ya lo excluye)
    # "lab:validar_resultados"  → CAJA y RECEPCION NO aparecen → denegado automático
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user_rol(user) -> str:
    """Extrae el rol del usuario normalizado a mayúsculas."""
    return (getattr(user, "rol", "") or "").upper().strip()


def _is_superadmin(user) -> bool:
    return bool(getattr(user, "is_superuser", False))


def _has_permission(user, permission_key: str) -> bool:
    """
    Verifica si el usuario tiene el permiso dado.
    Superadmin tiene todos. El resto: whitelist estricta por rol.
    """
    if _is_superadmin(user):
        return True
    allowed = PERMISSION_MAP.get(permission_key)
    if allowed is None:
        logger.warning("RBAC: permiso desconocido '%s' — denegado por defecto.", permission_key)
        return False
    return _user_rol(user) in allowed


def check_permission(user, permission_key: str) -> None:
    """
    Verifica permiso o lanza PermissionDenied.
    Registra el intento fallido en el log.

    Uso en vistas funcionales:
        check_permission(request.user, "lab:validar_resultados")
    """
    if not _has_permission(user, permission_key):
        logger.warning(
            "RBAC_DENIED user=%s rol=%s permission=%s",
            getattr(user, "username", "?"),
            _user_rol(user),
            permission_key,
        )
        raise PermissionDenied(f"Acceso denegado: se requiere permiso '{permission_key}'.")


# ── Decoradores de vista ──────────────────────────────────────────────────────

def require_permission(permission_key: str):
    """
    Decorador: verifica permiso RBAC antes de ejecutar la vista.

    Uso:
        @login_required
        @require_permission("lab:validar_resultados")
        def validar_orden(request, orden_id):
            ...

    Responde JSON si la request es AJAX, renderiza 403 en caso contrario.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("No autenticado.")
            if not _has_permission(request.user, permission_key):
                logger.warning(
                    "RBAC_DENIED view=%s user=%s rol=%s permission=%s path=%s",
                    view_func.__name__,
                    getattr(request.user, "username", "?"),
                    _user_rol(request.user),
                    permission_key,
                    request.path,
                )
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse(
                        {"status": "error", "mensaje": "Sin permiso para esta operación."},
                        status=403,
                    )
                raise PermissionDenied(
                    f"Rol '{_user_rol(request.user)}' no tiene acceso a esta función."
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_roles(*roles: str):
    """
    Decorador: restringe por rol directamente (sin mapa de permisos).
    Útil para proteger secciones enteras de la app.

    Uso:
        @login_required
        @require_roles(Rol.ADMIN, Rol.DIRECTOR)
        def configuracion_empresa(request):
            ...
    """
    allowed_upper = frozenset(r.upper() for r in roles)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                raise PermissionDenied("No autenticado.")
            if _is_superadmin(user):
                return view_func(request, *args, **kwargs)
            if _user_rol(user) not in allowed_upper:
                logger.warning(
                    "RBAC_ROLE_DENIED view=%s user=%s rol=%s allowed=%s",
                    view_func.__name__,
                    getattr(user, "username", "?"),
                    _user_rol(user),
                    allowed_upper,
                )
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse(
                        {"status": "error", "mensaje": "Rol insuficiente."},
                        status=403,
                    )
                raise PermissionDenied(
                    f"Se requiere uno de los roles: {', '.join(sorted(allowed_upper))}."
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def deny_roles(*roles: str):
    """
    Decorador: bloquea roles específicos. Complemento de require_roles.
    Implementa la regla: CAJA/RECEPCION nunca accede a endpoints médicos.

    Uso:
        @login_required
        @deny_roles(Rol.CAJA, Rol.RECEPCION)
        def captura_resultados(request, orden_id):
            ...
    """
    blocked_upper = frozenset(r.upper() for r in roles)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                raise PermissionDenied("No autenticado.")
            if not _is_superadmin(user) and _user_rol(user) in blocked_upper:
                logger.warning(
                    "RBAC_DENIED_EXPLICIT view=%s user=%s rol=%s blocked=%s",
                    view_func.__name__,
                    getattr(user, "username", "?"),
                    _user_rol(user),
                    blocked_upper,
                )
                raise PermissionDenied(
                    f"Rol '{_user_rol(user)}' no puede acceder a esta función."
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ── Utilidad para templates y vistas ─────────────────────────────────────────

def user_permissions(user) -> dict[str, bool]:
    """
    Devuelve un dict completo de permisos para el usuario.
    Útil para inyectar en el contexto del template o en el JWT payload.

    Uso en vista:
        ctx["permisos"] = user_permissions(request.user)

    En template:
        {% if permisos.lab_validar_resultados %}
    """
    return {
        key.replace(":", "_"): _has_permission(user, key)
        for key in PERMISSION_MAP
    }
