"""
Utilidades para Trazabilidad Automática - PRISLAB
Registra automáticamente todas las operaciones críticas del sistema.
"""
from django.utils import timezone
# TrazabilidadOperacion no existe en core/models.py, usando AuditLog en su lugar
try:
    from core.models import AuditLog, Empresa, Usuario, Sucursal
    TRAZABILIDAD_DISPONIBLE = True
except ImportError:
    TRAZABILIDAD_DISPONIBLE = False


def registrar_trazabilidad(
    tipo_operacion,
    modulo,
    referencia_id,
    referencia_tipo,
    accion,
    descripcion,
    usuario,
    empresa,
    sucursal=None,
    datos_anteriores=None,
    datos_nuevos=None,
    request=None
):
    """
    Registra una operación en el sistema de trazabilidad.
    
    Args:
        tipo_operacion: Tipo de operación (VENTA, COMPRA, etc.)
        modulo: Módulo del sistema (FARMACIA, LABORATORIO, etc.)
        referencia_id: ID del registro relacionado
        referencia_tipo: Tipo de modelo (ej: 'Venta', 'Compra')
        accion: Acción realizada (CREAR, MODIFICAR, etc.)
        descripcion: Descripción de la operación
        usuario: Usuario que realizó la operación
        empresa: Empresa
        sucursal: Sucursal (opcional)
        datos_anteriores: Estado anterior (JSON) - para modificaciones
        datos_nuevos: Estado nuevo (JSON) - para modificaciones
        request: Request HTTP (opcional, para obtener IP y User Agent)
    """
    if not TRAZABILIDAD_DISPONIBLE:
        return  # No hacer nada si no está disponible
    
    try:
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        # Usar AuditLog en lugar de TrazabilidadOperacion
        AuditLog.objects.create(
            empresa=empresa,
            sucursal=sucursal,
            usuario=usuario,
            accion=accion,
            modelo_afectado=referencia_tipo,
            objeto_id=str(referencia_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception as e:
        # No fallar la operación principal si hay error en trazabilidad
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error al registrar trazabilidad: {str(e)}')


def get_client_ip(request):
    """Obtiene la IP real del cliente."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def serializar_modelo(instancia):
    """
    Serializa un modelo a JSON para trazabilidad.
    Solo incluye campos relevantes.
    """
    if not instancia:
        return None
    
    datos = {}
    campos_relevantes = [
        'id', 'nombre', 'total', 'estado', 'fecha', 'fecha_creacion',
        'cantidad', 'precio', 'stock', 'folio', 'folio_operacion',
    ]
    
    for campo in campos_relevantes:
        if hasattr(instancia, campo):
            valor = getattr(instancia, campo)
            # Convertir tipos no serializables
            if hasattr(valor, 'isoformat'):  # datetime, date
                datos[campo] = valor.isoformat()
            elif hasattr(valor, '__float__'):  # Decimal
                datos[campo] = float(valor)
            else:
                datos[campo] = str(valor)
    
    return datos
