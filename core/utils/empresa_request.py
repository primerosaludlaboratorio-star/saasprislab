"""Resolución consistente de empresa en vistas HTTP (middleware + FK usuario)."""


def get_empresa_usuario(user):
    """Obtiene empresa de un objeto usuario. Uso: se pasa el objeto user directamente."""
    if user is None:
        return None
    return getattr(user, 'empresa', None)


def empresa_efectiva_request(request):
    """
    Debe coincidir con la empresa usada por EmpresaIdentityMiddleware / TenantManager.
    No usar solo request.user.empresa en APIs de creación o búsqueda.
    """
    if request is None:
        return None
    return getattr(request, 'empresa_actual', None) or get_empresa_usuario(
        getattr(request, 'user', None)
    )
