"""
Sistema de Auditoría Nativa para PRISLAB v5.0
Registra automáticamente todos los cambios en campos críticos.
"""
from django.utils import timezone
from django.contrib.auth import get_user_model
from core.models import AuditLog, Empresa
from core.utils.auditoria_helper import crear_log_auditoria
import json

Usuario = get_user_model()


def registrar_cambio_campo(
    usuario,
    modelo,
    objeto_id,
    campo_nombre,
    valor_anterior,
    valor_nuevo,
    modulo='GENERAL',
    empresa=None,
    referencia_id=None,
    referencia_tipo=None,
    request=None
):
    """
    Registra automáticamente un cambio en un campo crítico.
    
    Args:
        usuario: Usuario que realizó el cambio
        modelo: Nombre del modelo (ej: 'DetalleOrden')
        objeto_id: ID del objeto modificado
        campo_nombre: Nombre del campo modificado (ej: 'resultado')
        valor_anterior: Valor antes del cambio
        valor_nuevo: Valor después del cambio
        modulo: Módulo donde ocurrió (ej: 'LABORATORIO')
        empresa: Empresa (si no se proporciona, se toma de usuario)
        referencia_id: ID del registro principal (ej: orden_id)
        referencia_tipo: Tipo de referencia (ej: 'OrdenDeServicio')
        request: Request object (opcional, para extraer IP)
    
    Returns:
        AuditLog: Objeto de log creado
    """
    if not empresa:
        empresa = usuario.empresa if hasattr(usuario, 'empresa') else None
    
    if not empresa:
        return None
    
    # Preparar datos para el log
    datos_anterior = {campo_nombre: valor_anterior}
    datos_nuevo = {campo_nombre: valor_nuevo}
    
    # Obtener IP del request si está disponible
    ip_address = None
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
    
    # Crear log de auditoría usando la función helper existente
    # La función crear_log_auditoria usa modelo_afectado, datos_anteriores, datos_nuevos
    log = crear_log_auditoria(
        empresa=empresa,
        usuario=usuario,
        accion=AuditLog.ACCION_UPDATE,
        modelo=modelo,
        objeto_id=objeto_id,
        datos_anterior=datos_anterior,
        datos_nuevo=datos_nuevo,
        request=request
    )
    
    return log


def registrar_cambio_multiples_campos(
    usuario,
    modelo,
    objeto_id,
    cambios_dict,
    modulo='GENERAL',
    empresa=None,
    request=None
):
    """
    Registra múltiples cambios en un mismo objeto.
    
    Args:
        usuario: Usuario que realizó los cambios
        modelo: Nombre del modelo
        objeto_id: ID del objeto modificado
        cambios_dict: Diccionario con formato {campo: {'anterior': valor, 'nuevo': valor}}
        modulo: Módulo donde ocurrió
        empresa: Empresa
        request: Request object
    
    Returns:
        AuditLog: Objeto de log creado
    """
    if not empresa:
        empresa = usuario.empresa if hasattr(usuario, 'empresa') else None
    
    if not empresa:
        return None
    
    # Preparar datos
    datos_anterior = {}
    datos_nuevo = {}
    descripcion_campos = []
    
    for campo, valores in cambios_dict.items():
        datos_anterior[campo] = valores.get('anterior', '')
        datos_nuevo[campo] = valores.get('nuevo', '')
        descripcion_campos.append(f"{campo}: {valores.get('anterior', '')} → {valores.get('nuevo', '')}")
    
    # Obtener IP
    ip_address = None
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
    
    # Crear log
    log = AuditLog.objects.create(
        empresa=empresa,
        usuario=usuario,
        accion=AuditLog.ACCION_UPDATE,
        modelo=modelo,
        objeto_id=objeto_id,
        datos_anterior=datos_anterior,
        datos_nuevo=datos_nuevo,
        descripcion=f'Cambios en {len(cambios_dict)} campos: {", ".join(descripcion_campos)}',
        modulo=modulo,
        ip_address=ip_address
    )
    
    return log


def obtener_historial_cambios(
    modelo,
    objeto_id,
    campo_nombre=None,
    limite=50
):
    """
    Obtiene el historial de cambios para un objeto específico.
    
    Args:
        modelo: Nombre del modelo
        objeto_id: ID del objeto
        campo_nombre: Campo específico (opcional)
        limite: Número máximo de registros a retornar
    
    Returns:
        QuerySet: Lista de logs de auditoría
    """
    logs = AuditLog.objects.filter(
        modelo=modelo,
        objeto_id=objeto_id
    ).order_by('-fecha_creacion')
    
    if campo_nombre:
        # Filtrar logs que contengan el campo específico
        logs = logs.filter(
            datos_nuevos__has_key=campo_nombre
        )
    
    return logs[:limite]


def obtener_ultimo_valor_campo(
    modelo,
    objeto_id,
    campo_nombre
):
    """
    Obtiene el último valor registrado de un campo específico.
    
    Args:
        modelo: Nombre del modelo
        objeto_id: ID del objeto
        campo_nombre: Nombre del campo
    
    Returns:
        Valor del campo o None si no existe
    """
    log = AuditLog.objects.filter(
        modelo_afectado=modelo,
        objeto_id=objeto_id,
        datos_nuevos__has_key=campo_nombre
    ).order_by('-fecha_creacion').first()
    
    if log and log.datos_nuevos:
        return log.datos_nuevos.get(campo_nombre)
    
    return None
