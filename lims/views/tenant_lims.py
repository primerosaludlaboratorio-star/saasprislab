"""Resolución de tenant para vistas LIMS (defensa en profundidad)."""


def empresa_lims(request):
    # FIX V8.2 LIMS TENANT: middleware inyecta empresa_actual; superusuario no activa TenantManager ORM
    return getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)
