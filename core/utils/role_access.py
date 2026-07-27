"""Sincronizacion de grupos Django con el rol operativo del usuario."""

from django.contrib.auth.models import Group, Permission


ROLE_GROUPS = {
    'ADMIN': 'Administrador',
    'DIRECTOR': 'DIRECTOR',
    'GERENTE': 'GERENCIA',
    'MEDICO': 'MEDICOS',
    'QUIMICO': 'LABORATORIO',
    'LABORATORIO': 'LABORATORIO',
    'CAJERO': 'CAJERO',
    'FARMACIA': 'FARMACIA',
    'RECEPCION': 'RECEPCION',
}

MANAGED_GROUPS = frozenset(ROLE_GROUPS.values())


def sincronizar_acceso_por_rol(usuario):
    """Asigna el grupo y permisos funcionales correspondientes al rol.

    Solo administra los grupos definidos por ROLE_GROUPS; los grupos
    personalizados de la empresa no se eliminan.
    """
    rol = (getattr(usuario, 'rol', '') or '').strip().upper()
    grupo_nombre = ROLE_GROUPS.get(rol)
    if not grupo_nombre or not getattr(usuario, 'pk', None):
        return None

    grupos = Group.objects.filter(name__in=MANAGED_GROUPS)
    usuario.groups.remove(*grupos)
    grupo, _ = Group.objects.get_or_create(name=grupo_nombre)

    if rol == 'FARMACIA':
        permisos = Permission.objects.filter(content_type__app_label='farmacia')
        grupo.permissions.add(*permisos)

    usuario.groups.add(grupo)
    return grupo
