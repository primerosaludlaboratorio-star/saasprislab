"""
Utilidades para verificación de permisos granulares (REGLA 5).
"""
from core.models.seguridad_perfiles import PerfilUsuario, PermisoModulo, PermisoRecurso
import logging


def tiene_permiso(usuario, modulo, accion, recurso=None):
    """
    Verifica si un usuario tiene un permiso específico.
    
    Args:
        usuario: Instancia de Usuario
        modulo: Nombre del módulo (ej: 'LABORATORIO')
        accion: Acción a verificar (ej: 'EDITAR', 'VALIDAR')
        recurso: Recurso específico (opcional, ej: 'Resultados de Laboratorio')
    
    Returns:
        bool: True si tiene permiso, False si no
    """
    # Si es superusuario, tiene todos los permisos
    if usuario.is_superuser:
        return True
    
    # Obtener perfil del usuario
    try:
        perfil = usuario.perfil_usuario
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en tiene_permiso (permisos.py)")
        # Si no tiene perfil asignado, verificar permisos por defecto
        return verificar_permisos_por_defecto(usuario, modulo, accion)
    
    # Buscar permiso de módulo
    try:
        permiso_modulo = PermisoModulo.objects.get(
            perfil=perfil,
            modulo=modulo,
            accion=accion
        )
        
        # Si el permiso de módulo está denegado, no tiene permiso
        if not permiso_modulo.permitido:
            return False
        
        # Si hay recurso específico, verificar permiso de recurso
        if recurso:
            try:
                permiso_recurso = PermisoRecurso.objects.get(
                    permiso_modulo=permiso_modulo,
                    recurso=recurso,
                    accion=accion
                )
                return permiso_recurso.permitido
            except PermisoRecurso.DoesNotExist:
                # Si no hay permiso específico de recurso, usar el del módulo
                return permiso_modulo.permitido
        
        return permiso_modulo.permitido
        
    except PermisoModulo.DoesNotExist:
        # Si no existe el permiso, usar permisos por defecto
        return verificar_permisos_por_defecto(usuario, modulo, accion)


def verificar_permisos_por_defecto(usuario, modulo, accion):
    """
    Verifica permisos por defecto basados en el rol del usuario.
    """
    # Mapeo de roles a permisos por defecto
    permisos_por_defecto = {
        'ADMIN': {
            'LABORATORIO': ['VER', 'CREAR', 'EDITAR', 'VALIDAR', 'BORRAR', 'IMPRIMIR', 'EXPORTAR'],
            'FARMACIA': ['VER', 'CREAR', 'EDITAR', 'VALIDAR', 'BORRAR', 'IMPRIMIR', 'EXPORTAR'],
            'MEDICO': ['VER', 'CREAR', 'EDITAR', 'VALIDAR', 'BORRAR', 'IMPRIMIR', 'EXPORTAR'],
        },
        'QUIMICO': {
            'LABORATORIO': ['VER', 'CREAR', 'EDITAR', 'VALIDAR', 'IMPRIMIR'],
            'FARMACIA': ['VER'],
        },
        'MEDICO': {
            'MEDICO': ['VER', 'CREAR', 'EDITAR', 'IMPRIMIR'],
            'LABORATORIO': ['VER', 'CREAR'],  # Puede crear órdenes
        },
        'FARMACIA': {
            'FARMACIA': ['VER', 'CREAR', 'EDITAR', 'IMPRIMIR'],
            'LABORATORIO': ['VER'],
        },
    }
    
    rol = getattr(usuario, 'rol', 'USUARIO')
    permisos_rol = permisos_por_defecto.get(rol, {})
    permisos_modulo = permisos_rol.get(modulo, [])
    
    return accion in permisos_modulo


def decorador_permiso_requerido(modulo, accion, recurso=None):
    """
    Decorador para verificar permisos en vistas.
    
    Uso:
        @decorador_permiso_requerido('LABORATORIO', 'VALIDAR')
        def validar_resultados(request, orden_id):
            ...
    """
    from django.contrib.auth.decorators import login_required
    from django.http import HttpResponseForbidden
    from functools import wraps
    
    def decorador(func):
        @wraps(func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if tiene_permiso(request.user, modulo, accion, recurso):
                return func(request, *args, **kwargs)
            else:
                return HttpResponseForbidden('No tiene permiso para realizar esta acción')
        return wrapper
    return decorador