"""Resolución consistente de empresa en vistas HTTP (middleware + FK usuario)."""


def empresa_efectiva_request(request):
    """
    Debe coincidir con la empresa usada por EmpresaIdentityMiddleware / TenantManager.
    No usar solo request.user.empresa en APIs de creación o búsqueda.
    """
    if request is None:
        return None
    return getattr(request, 'empresa_actual', None) or getattr(
        getattr(request, 'user', None), 'empresa', None
    )
