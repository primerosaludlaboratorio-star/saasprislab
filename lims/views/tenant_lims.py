"""Resolución de tenant para vistas LIMS (defensa en profundidad)."""


def empresa_lims(request):
    """
    Empresa canónica para LIMS:
    solo acepta la FK explícita del usuario autenticado.

    No usa request.empresa_actual porque el middleware puede poblar una empresa
    de respaldo para compatibilidad operativa, y LIMS debe bloquear a usuarios
    sin empresa explícita para evitar cruces cross-tenant.
    """
    return getattr(getattr(request, 'user', None), 'empresa', None)
