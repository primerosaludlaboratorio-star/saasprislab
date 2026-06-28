"""
Utilidad para crear logs de auditoría forense con SHA-256.
"""
import hashlib
import json
from django.utils import timezone
from core.models import AuditLog, Empresa


def calcular_hash_auditoria(datos):
    """
    Calcula hash SHA-256 de los datos de auditoría para prevenir alteraciones.
    """
    datos_str = json.dumps(datos, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(datos_str.encode('utf-8')).hexdigest()


def crear_log_auditoria(empresa, usuario, accion, modelo, objeto_id, datos_anterior=None, datos_nuevo=None, sucursal=None, request=None):
    """
    Crea un log de auditoría inalterable para cualquier acción crítica.
    
    Args:
        empresa: Instancia de Empresa
        usuario: Usuario que realiza la acción
        accion: Una de AuditLog.ACCION_*
        modelo: Nombre del modelo Django (ej: 'DetalleOrden', 'Venta')
        objeto_id: ID del objeto afectado
        datos_anterior: Dict con valores anteriores (opcional)
        datos_nuevo: Dict con valores nuevos (opcional)
        sucursal: Instancia de Sucursal (opcional)
        request: Objeto request de Django para obtener IP y User Agent (opcional)
    
    Returns:
        AuditLog: Instancia del log creado
    """
    datos_auditoria = {
        'accion': accion,
        'modelo': modelo,
        'objeto_id': str(objeto_id),
        'fecha': timezone.now().isoformat(),
        'datos_anterior': datos_anterior or {},
        'datos_nuevo': datos_nuevo or {},
    }
    
    hash_verificacion = calcular_hash_auditoria(datos_auditoria)
    
    # Obtener IP y User Agent si está disponible
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    
    return AuditLog.objects.create(
        empresa=empresa,
        sucursal=sucursal,
        usuario=usuario,
        accion=accion,
        modelo_afectado=modelo,
        objeto_id=str(objeto_id),
        datos_anteriores=datos_anterior or {},
        datos_nuevos=datos_nuevo or {},
        hash_verificacion=hash_verificacion,
        ip_address=ip_address,
        user_agent=user_agent
    )
