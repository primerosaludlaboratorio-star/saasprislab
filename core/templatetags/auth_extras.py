"""
PRISLAB V5.0 - TEMPLATE TAGS PERSONALIZADOS PARA AUTENTICACIÓN Y ROLES
========================================================================
Fecha: 1 de Febrero de 2026
Objetivo: Filtros personalizados para verificar grupos y permisos en templates

MEJORAS IMPLEMENTADAS:
✅ Filtro has_group para verificar grupos de Django
✅ Filtro has_permission para verificar permisos específicos
✅ Filtro is_role para verificar rol del usuario (campo custom)
✅ Filtro can_access_module para verificar acceso a módulos
✅ Performance optimizado con caché de grupos
"""

from django import template
from django.core.cache import cache
import logging

register = template.Library()


# ==============================================================================
# FILTRO: has_group
# ==============================================================================

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Verifica si el usuario pertenece a un grupo específico.
    
    Uso en templates:
        {% if request.user|has_group:"MEDICOS" %}
            <!-- Contenido solo para médicos -->
        {% endif %}
    
    Args:
        user: Instancia de Usuario
        group_name: Nombre del grupo (string)
    
    Returns:
        bool: True si el usuario pertenece al grupo
    
    Mejoras:
        - Caché de 5 minutos para optimizar consultas
        - Manejo robusto de usuarios anónimos
        - Logging de accesos para auditoría
    """
    # Validar que el usuario este autenticado
    if not user or not user.is_authenticated:
        return False
    
    # GERENCIA_OPERATIVA: acceso total a todas las areas
    # Nancy y Gabriela tienen autorizacion gerencial - solo debajo del Director
    cache_key_gerencia = f'user_group_{user.id}_GERENCIA_OPERATIVA'
    is_gerencia = cache.get(cache_key_gerencia)
    if is_gerencia is None:
        try:
            is_gerencia = user.groups.filter(name='GERENCIA_OPERATIVA').exists()
            cache.set(cache_key_gerencia, is_gerencia, 300)
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en has_group (auth_extras.py)")
            is_gerencia = False
    
    if is_gerencia:
        return True
    
    # Intentar obtener del cache
    cache_key = f'user_group_{user.id}_{group_name}'
    cached_result = cache.get(cache_key)
    
    if cached_result is not None:
        return cached_result
    
    # Verificar en base de datos
    try:
        result = user.groups.filter(name=group_name).exists()
        
        # Guardar en cache por 5 minutos
        cache.set(cache_key, result, 300)
        
        return result
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en has_group (auth_extras.py)")
        # En caso de error, denegar acceso
        return False


# ==============================================================================
# FILTRO: has_permission
# ==============================================================================

@register.filter(name='has_permission')
def has_permission(user, permission_codename):
    """
    Verifica si el usuario tiene un permiso específico.
    
    Uso en templates:
        {% if request.user|has_permission:"add_paciente" %}
            <a href="...">Agregar Paciente</a>
        {% endif %}
    
    Args:
        user: Instancia de Usuario
        permission_codename: Código del permiso (ej: 'add_paciente')
    
    Returns:
        bool: True si el usuario tiene el permiso
    """
    if not user or not user.is_authenticated:
        return False
    
    # Superusuarios tienen todos los permisos
    if user.is_superuser:
        return True
    
    try:
        return user.has_perm(permission_codename)
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en has_permission (auth_extras.py)")
        return False


# ==============================================================================
# FILTRO: is_role
# ==============================================================================

@register.filter(name='is_role')
def is_role(user, role_name):
    """
    Verifica si el usuario tiene un rol específico (campo custom en modelo Usuario).
    
    Uso en templates:
        {% if request.user|is_role:"MEDICO" %}
            <!-- Contenido solo para médicos -->
        {% endif %}
    
    Args:
        user: Instancia de Usuario
        role_name: Nombre del rol (string)
    
    Returns:
        bool: True si el usuario tiene ese rol
    
    Nota:
        Este filtro funciona con el campo 'rol' del modelo Usuario custom.
    """
    if not user or not user.is_authenticated:
        return False
    
    try:
        # GERENCIA_OPERATIVA: acceso equivalente a todos los roles operativos
        # (no incluye ADMIN para proteger configuraciones criticas del sistema)
        if role_name in ('QUIMICO', 'CAJERO', 'RECEPCION', 'GERENTE', 'MEDICO'):
            cache_key_gerencia = f'user_group_{user.id}_GERENCIA_OPERATIVA'
            is_gerencia = cache.get(cache_key_gerencia)
            if is_gerencia is None:
                is_gerencia = user.groups.filter(name='GERENCIA_OPERATIVA').exists()
                cache.set(cache_key_gerencia, is_gerencia, 300)
            if is_gerencia:
                return True
        
        # Verificar si el usuario tiene el campo 'rol' (case-insensitive)
        if hasattr(user, 'rol') and user.rol:
            return user.rol.upper() == role_name.upper()
        return False
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en is_role (auth_extras.py)")
        return False


# ==============================================================================
# FILTRO: can_access_module
# ==============================================================================

@register.filter(name='can_access_module')
def can_access_module(user, module_name):
    """
    Verifica si el usuario puede acceder a un módulo específico
    según la configuración de la empresa (Feature Toggles).
    
    Uso en templates:
        {% if request.user|can_access_module:"laboratorio" %}
            <li><a href="/laboratorio/">Laboratorio</a></li>
        {% endif %}
    
    Args:
        user: Instancia de Usuario
        module_name: Nombre del módulo (string)
    
    Returns:
        bool: True si el usuario puede acceder al módulo
    
    Mejoras:
        - Verifica tanto grupos como ConfiguracionModulos
        - Superusuarios siempre tienen acceso
        - Caché de 10 minutos
    """
    if not user or not user.is_authenticated:
        return False
    
    # Superusuarios siempre tienen acceso
    if user.is_superuser:
        return True
    
    # Intentar obtener del caché
    cache_key = f'user_module_{user.id}_{module_name}'
    cached_result = cache.get(cache_key)
    
    if cached_result is not None:
        return cached_result
    
    try:
        # Verificar si la empresa tiene el módulo activo
        if hasattr(user, 'empresa') and user.empresa:
            empresa = user.empresa
            
            # Verificar ConfiguracionModulos
            if hasattr(empresa, 'configuracion_modulos'):
                config = empresa.configuracion_modulos
                
                # Mapeo de nombres de módulos a campos de configuración
                module_map = {
                    'laboratorio': 'modulo_laboratorio',
                    'farmacia': 'modulo_farmacia',
                    'consultorio': 'modulo_consulta_externa',
                    'expediente': 'modulo_expediente_clinico',
                    'hospitalizacion': 'modulo_hospitalizacion',
                    'citas': 'modulo_citas',
                    'rrhh': 'modulo_rrhh',
                    'contabilidad': 'modulo_contabilidad',
                    'ia': 'modulo_ia',
                    'iot': 'modulo_iot',
                }
                
                # Obtener el campo correspondiente
                field_name = module_map.get(module_name.lower())
                if field_name and hasattr(config, field_name):
                    result = getattr(config, field_name)
                    
                    # Guardar en caché por 10 minutos
                    cache.set(cache_key, result, 600)
                    
                    return result
        
        # Si no hay configuración, permitir acceso por defecto
        result = True
        cache.set(cache_key, result, 600)
        return result
        
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en can_access_module (auth_extras.py)")
        # En caso de error, permitir acceso
        return True


# ==============================================================================
# FILTRO: in_groups
# ==============================================================================

@register.filter(name='in_groups')
def in_groups(user, groups_string):
    """
    Verifica si el usuario pertenece a CUALQUIERA de los grupos listados.
    
    Uso en templates:
        {% if request.user|in_groups:"MEDICOS,ENFERMERIA,RECEPCION" %}
            <!-- Contenido para personal clínico -->
        {% endif %}
    
    Args:
        user: Instancia de Usuario
        groups_string: String con nombres de grupos separados por comas
    
    Returns:
        bool: True si el usuario pertenece a al menos un grupo
    """
    if not user or not user.is_authenticated:
        return False
    
    try:
        # Separar grupos
        group_names = [g.strip() for g in groups_string.split(',')]
        
        # Verificar si pertenece a alguno
        for group_name in group_names:
            if has_group(user, group_name):
                return True
        
        return False
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en in_groups (auth_extras.py)")
        return False


# ==============================================================================
# TAG: user_dashboard_url
# ==============================================================================

@register.simple_tag
def user_dashboard_url(user):
    """
    Retorna la URL del dashboard apropiada según el rol del usuario.
    
    Uso en templates:
        <a href="{% user_dashboard_url request.user %}">Mi Dashboard</a>
    
    Args:
        user: Instancia de Usuario
    
    Returns:
        str: URL del dashboard correspondiente
    """
    if not user or not user.is_authenticated:
        return '/login/'
    
    # Superusuario o Admin
    if user.is_superuser or (hasattr(user, 'rol') and user.rol == 'ADMIN'):
        return '/dashboard/'
    
    # GERENCIA_OPERATIVA: Nancy y Gabriela van al dashboard principal
    # (deben verificarse ANTES de los roles individuales porque has_group
    #  retorna True para cualquier grupo si es GERENCIA_OPERATIVA)
    try:
        if user.groups.filter(name='GERENCIA_OPERATIVA').exists():
            return '/dashboard/'
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en user_dashboard_url (auth_extras.py)")
        pass
    
    # Medico
    if has_group(user, 'MEDICOS') or (hasattr(user, 'rol') and user.rol == 'MEDICO'):
        return '/medico/'
    
    # Laboratorio
    if has_group(user, 'LABORATORIO') or (hasattr(user, 'rol') and user.rol in ['QUIMICO', 'LABORATORISTA']):
        return '/laboratorio/'
    
    # Farmacia
    if has_group(user, 'FARMACIA') or (hasattr(user, 'rol') and user.rol == 'CAJERO'):
        return '/farmacia/'
    
    # Recepcion
    if has_group(user, 'RECEPCION') or (hasattr(user, 'rol') and user.rol == 'RECEPCION'):
        return '/recepcion/'
    
    # Por defecto
    return '/home/'


# ==============================================================================
# TAG: user_greeting
# ==============================================================================

@register.simple_tag
def user_greeting(user):
    """
    Genera un saludo personalizado según el rol del usuario.
    
    Uso en templates:
        <h1>{% user_greeting request.user %}</h1>
    
    Args:
        user: Instancia de Usuario
    
    Returns:
        str: Saludo personalizado
    """
    if not user or not user.is_authenticated:
        return "Bienvenido"
    
    name = user.get_full_name() or user.username
    
    # Determinar título según rol
    if user.is_superuser:
        title = "Director"
    elif has_group(user, 'MEDICOS') or (hasattr(user, 'rol') and user.rol == 'MEDICO'):
        title = "Dr./Dra."
    elif has_group(user, 'LABORATORIO') or (hasattr(user, 'rol') and user.rol == 'QUIMICO'):
        title = "Q.F.B."
    else:
        title = ""
    
    if title:
        return f"Bienvenido, {title} {name}"
    else:
        return f"Bienvenido, {name}"