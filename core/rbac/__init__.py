# core/rbac/__init__.py
from .permissions import (
    Rol,
    PERMISSION_MAP,
    SUCURSAL_SCOPED_RESOURCES,
    check_permission,
    require_permission,
    require_roles,
    deny_roles,
    user_permissions,
    # Sucursal-level RBAC
    check_sucursal_access,
    require_sucursal_access,
    user_sucursal_permissions,
)

__all__ = [
    "Rol",
    "PERMISSION_MAP",
    "SUCURSAL_SCOPED_RESOURCES",
    "check_permission",
    "require_permission",
    "require_roles",
    "deny_roles",
    "user_permissions",
    "check_sucursal_access",
    "require_sucursal_access",
    "user_sucursal_permissions",
]
