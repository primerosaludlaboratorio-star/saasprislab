"""
core/utils/sucursal_helpers.py
Helper centralizado para trabajar con sucursales de usuarios.
Abstrae la complejidad de la migración FK → M2M.
"""
from typing import Optional
from django.db.models import QuerySet

from core.models import Usuario, Sucursal, Usuario_Sucursal


def get_user_primary_sucursal(user: Usuario) -> Optional[Sucursal]:
    """
    Obtiene la sucursal "primaria" del usuario (primera asignada).
    Compatible con código legacy que usa user.sucursal.

    Retorna:
        Sucursal o None si el usuario no tiene sucursal asignada.
    """
    if not user or not hasattr(user, 'get_primary_sucursal'):
        return None
    return user.get_primary_sucursal()


def get_user_sucursales(user: Usuario, activas_only: bool = True) -> QuerySet:
    """
    Obtiene todas las sucursales asignadas al usuario.

    Args:
        user: Usuario para consultar
        activas_only: Si True, solo retorna asignaciones vigentes

    Retorna:
        QuerySet de Sucursal
    """
    if not user or not hasattr(user, 'sucursales'):
        return Sucursal.objects.none()

    qs = user.sucursales.filter(activa=True)
    if activas_only:
        qs = qs.filter(usuario_sucursal__activa=True)
    return qs


def assign_sucursal_to_user(user: Usuario, sucursal: Sucursal, vencimiento=None) -> Usuario_Sucursal:
    """
    Asigna una sucursal a un usuario con fecha de vencimiento opcional.
    Reemplaza el código legacy: user.sucursal = sucursal; user.save()

    Args:
        user: Usuario a asignar
        sucursal: Sucursal a asignar
        vencimiento: datetime opcional para expiración

    Retorna:
        Objeto Usuario_Sucursal creado/actualizado
    """
    if hasattr(user, 'add_sucursal'):
        user.add_sucursal(sucursal, vencimiento)
        return Usuario_Sucursal.objects.get(usuario=user, sucursal=sucursal)
    else:
        # Fallback legacy
        user.sucursal = sucursal
        user.save()
        return Usuario_Sucursal.objects.get(usuario=user, sucursal=sucursal)


def remove_sucursal_from_user(user: Usuario, sucursal: Sucursal) -> bool:
    """
    Remueve la asignación de una sucursal a un usuario.

    Retorna:
        True si fue removida, False si no existía
    """
    try:
        asignacion = Usuario_Sucursal.objects.get(usuario=user, sucursal=sucursal)
        asignacion.delete()
        return True
    except Usuario_Sucursal.DoesNotExist:
        return False


def user_has_sucursal(user: Usuario, sucursal_id: int) -> bool:
    """
    Verifica si un usuario tiene acceso a una sucursal específica.

    Args:
        user: Usuario a verificar
        sucursal_id: ID de la sucursal

    Retorna:
        True si el usuario tiene acceso vigente a esa sucursal
    """
    if not user or not hasattr(user, 'has_sucursal'):
        return False
    return user.has_sucursal(sucursal_id)


def get_request_sucursal(request) -> Optional[Sucursal]:
    """
    Obtiene la sucursal del request (desde middleware).
    Compatible con request.sucursal_actual (legacy) o desde contexto M2M.

    Args:
        request: HttpRequest

    Retorna:
        Sucursal o None
    """
    # Preferir sucursal del request si el middleware la estableció
    if hasattr(request, 'sucursal_actual') and request.sucursal_actual:
        return request.sucursal_actual

    # Fallback: obtener del usuario
    if hasattr(request, 'user') and request.user.is_authenticated:
        return get_user_primary_sucursal(request.user)

    return None


def filter_queryset_by_user_sucursal(qs: QuerySet, user: Usuario, sucursal_field: str = 'sucursal') -> QuerySet:
    """
    Filtra un QuerySet por las sucursales asignadas al usuario.
    Si el usuario tiene permiso global, no filtra.

    Args:
        qs: QuerySet a filtrar
        user: Usuario para determinar sucursales
        sucursal_field: Nombre del campo FK a sucursal (default: 'sucursal')

    Retorna:
        QuerySet filtrado o sin cambios si permiso global
    """
    from core.rbac.permissions import _has_permission

    if not user or user.is_superuser:
        return qs

    # Si tiene permiso de ver todas las sucursales, no filtrar
    if _has_permission(user, "tenant:all_branches_view"):
        return qs

    # Obtener sucursales del usuario
    sucursal_ids = get_user_sucursales(user, activas_only=True).values_list('pk', flat=True)

    if not sucursal_ids:
        # Usuario sin sucursales asignadas → vacío
        return qs.none()

    # Filtrar por campo
    filter_kwarg = {f'{sucursal_field}__in': sucursal_ids}
    return qs.filter(**filter_kwarg)
