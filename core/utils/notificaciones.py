"""
Utilidades para Sistema de Notificaciones - PRISLAB
Genera notificaciones automáticas para eventos críticos.
"""
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# NOTA: Modelos Notificacion y ConfiguracionNotificaciones pendientes de migración. Descomentar cuando existan en DB.
from core.models import Empresa, Usuario, Producto, Lote
# from core.models import Notificacion, ConfiguracionNotificaciones


def crear_notificacion(
    tipo,
    titulo,
    mensaje,
    empresa,
    usuario_destino=None,
    sucursal=None,
    prioridad='MEDIA',
    referencia_tipo=None,
    referencia_id=None,
    accion_url=None,
    accion_texto=None
):
    """
    Crea una notificación en el sistema.
    
    Args:
        tipo: Tipo de notificación (STOCK_BAJO, CADUCIDAD_PROXIMA, etc.)
        titulo: Título de la notificación
        mensaje: Mensaje detallado
        empresa: Empresa
        usuario_destino: Usuario específico (None para notificación global)
        sucursal: Sucursal (opcional)
        prioridad: Prioridad (BAJA, MEDIA, ALTA, CRITICA)
        referencia_tipo: Tipo de objeto relacionado
        referencia_id: ID del objeto relacionado
        accion_url: URL para acción
        accion_texto: Texto del botón de acción
    """
    try:
        Notificacion.objects.create(
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            empresa=empresa,
            usuario_destino=usuario_destino,
            sucursal=sucursal,
            prioridad=prioridad,
            referencia_tipo=referencia_tipo,
            referencia_id=referencia_id,
            accion_url=accion_url,
            accion_texto=accion_texto,
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error al crear notificación: {str(e)}')


def obtener_o_crear_config(empresa):
    """Obtiene o crea la configuración de notificaciones para una empresa."""
    config, created = ConfiguracionNotificaciones.objects.get_or_create(
        empresa=empresa,
        defaults={
            'alerta_stock_bajo': True,
            'umbral_stock_bajo': 10,
            'alerta_caducidad_proxima': True,
            'dias_antes_caducidad': 30,
            'alerta_orden_pendiente': True,
            'alerta_resultado_listo': True,
            'alerta_cita_proxima': True,
            'horas_antes_cita': 24,
            'recordatorio_cita': True,
        }
    )
    return config


def verificar_stock_bajo(empresa):
    """Verifica productos con stock bajo y crea notificaciones."""
    config = obtener_o_crear_config(empresa)
    
    if not config.alerta_stock_bajo:
        return
    
    productos_bajo_stock = Producto.objects.filter(
        empresa=empresa,
        stock__gt=0,
        stock__lte=config.umbral_stock_bajo
    )
    
    for producto in productos_bajo_stock:
        # Verificar si ya existe una notificación reciente para este producto
        notificacion_reciente = Notificacion.objects.filter(
            empresa=empresa,
            tipo='STOCK_BAJO',
            referencia_tipo='Producto',
            referencia_id=producto.id,
            leida=False,
            fecha_creacion__gte=timezone.now() - timedelta(hours=24)
        ).exists()
        
        if not notificacion_reciente:
            crear_notificacion(
                tipo='STOCK_BAJO',
                titulo=f'Stock Bajo: {producto.nombre}',
                mensaje=f'El producto {producto.nombre} tiene solo {producto.stock} unidades en stock. Se recomienda realizar una compra.',
                empresa=empresa,
                sucursal=producto.sucursal,
                prioridad='ALTA' if producto.stock <= 5 else 'MEDIA',
                referencia_tipo='Producto',
                referencia_id=producto.id,
                accion_url=f'/farmacia/productos/{producto.id}/',
                accion_texto='Ver Producto'
            )


def verificar_caducidades(empresa):
    """Verifica productos próximos a caducar y crea notificaciones."""
    config = obtener_o_crear_config(empresa)
    
    if not config.alerta_caducidad_proxima:
        return
    
    fecha_limite = timezone.now().date() + timedelta(days=config.dias_antes_caducidad)
    
    lotes_proximos = Lote.objects.filter(
        producto__empresa=empresa,
        cantidad__gt=0,
        fecha_caducidad__lte=fecha_limite,
        fecha_caducidad__gte=timezone.now().date()
    ).select_related('producto', 'producto__sucursal')
    
    for lote in lotes_proximos:
        dias_restantes = (lote.fecha_caducidad - timezone.now().date()).days
        
        # Verificar si ya existe una notificación reciente
        notificacion_reciente = Notificacion.objects.filter(
            empresa=empresa,
            tipo='CADUCIDAD_PROXIMA',
            referencia_tipo='Lote',
            referencia_id=lote.id,
            leida=False,
            fecha_creacion__gte=timezone.now() - timedelta(hours=24)
        ).exists()
        
        if not notificacion_reciente:
            prioridad = 'CRITICA' if dias_restantes <= 7 else 'ALTA' if dias_restantes <= 15 else 'MEDIA'
            
            crear_notificacion(
                tipo='CADUCIDAD_PROXIMA',
                titulo=f'Caducidad Próxima: {lote.producto.nombre}',
                mensaje=f'El lote {lote.numero_lote} del producto {lote.producto.nombre} caduca en {dias_restantes} días ({lote.fecha_caducidad.strftime("%d/%m/%Y")}). Stock: {lote.cantidad} unidades.',
                empresa=empresa,
                sucursal=lote.producto.sucursal,
                prioridad=prioridad,
                referencia_tipo='Lote',
                referencia_id=lote.id,
                accion_url=f'/farmacia/productos/{lote.producto.id}/',
                accion_texto='Ver Producto'
            )
    
    # Verificar lotes vencidos
    lotes_vencidos = Lote.objects.filter(
        producto__empresa=empresa,
        cantidad__gt=0,
        fecha_caducidad__lt=timezone.now().date()
    ).select_related('producto', 'producto__sucursal')
    
    for lote in lotes_vencidos:
        notificacion_reciente = Notificacion.objects.filter(
            empresa=empresa,
            type='CADUCIDAD_VENCIDA',
            referencia_tipo='Lote',
            referencia_id=lote.id,
            leida=False,
            fecha_creacion__gte=timezone.now() - timedelta(hours=24)
        ).exists()
        
        if not notificacion_reciente:
            crear_notificacion(
                tipo='CADUCIDAD_VENCIDA',
                titulo=f'⚠️ PRODUCTO VENCIDO: {lote.producto.nombre}',
                mensaje=f'El lote {lote.numero_lote} del producto {lote.producto.nombre} está VENCIDO desde {lote.fecha_caducidad.strftime("%d/%m/%Y")}. Stock: {lote.cantidad} unidades. ACCIÓN INMEDIATA REQUERIDA.',
                empresa=empresa,
                sucursal=lote.producto.sucursal,
                prioridad='CRITICA',
                referencia_tipo='Lote',
                referencia_id=lote.id,
                accion_url=f'/farmacia/productos/{lote.producto.id}/',
                accion_texto='Ver Producto'
            )


def notificar_resultado_lab_listo(empresa, orden_id, paciente_nombre):
    """Crea notificación cuando un resultado de laboratorio está listo."""
    config = obtener_o_crear_config(empresa)
    
    if not config.alerta_resultado_listo:
        return
    
    try:
        from core.models import OrdenDeServicio
        orden = OrdenDeServicio.objects.get(id=orden_id, empresa=empresa)
        crear_notificacion(
            tipo='RESULTADO_LAB_LISTO',
            titulo=f'Resultado de Laboratorio Listo',
            mensaje=f'Los resultados de laboratorio para {paciente_nombre} están listos. Orden: {orden.folio_orden or orden.id}',
            empresa=empresa,
            prioridad='MEDIA',
            referencia_tipo='OrdenDeServicio',
            referencia_id=orden_id,
            accion_url=f'/laboratorio/captura/{orden_id}/',
            accion_texto='Ver Resultados'
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error al notificar resultado listo: {str(e)}')


def notificar_cita_proxima(empresa, cita_id, paciente_nombre, fecha_cita, usuario_destino=None):
    """Crea notificación para cita próxima."""
    config = obtener_o_crear_config(empresa)
    
    if not config.alerta_cita_proxima:
        return
    
    crear_notificacion(
        tipo='CITA_PROXIMA',
        titulo=f'Cita Próxima: {paciente_nombre}',
        mensaje=f'Tienes una cita programada con {paciente_nombre} el {fecha_cita.strftime("%d/%m/%Y a las %H:%M")}',
        empresa=empresa,
        usuario_destino=usuario_destino,
        prioridad='MEDIA',
        referencia_tipo='Cita',
        referencia_id=cita_id,
        accion_url=f'/consultorio/citas/{cita_id}/',
        accion_texto='Ver Cita'
    )


def ejecutar_verificaciones_automaticas(empresa):
    """Ejecuta todas las verificaciones automáticas de notificaciones."""
    verificar_stock_bajo(empresa)
    verificar_caducidades(empresa)
