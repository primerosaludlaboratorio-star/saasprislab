"""
PRISLAB V5.0 - SIGNALS: DEVOLUCIONES DE VENTA
Seguridad financiera: reintegración de inventario + reembolso en caja.
"""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from farmacia.models import MovimientoInventario


logger = logging.getLogger('signals')


# ==============================================================================
# SIGNAL: SEGURIDAD FINANCIERA - DEVOLUCIONES DE VENTA (PASO 2B)
# ==============================================================================

@receiver(post_save, sender='core.DevolucionVenta', dispatch_uid='devolucion_venta_movimiento_inventario_unico')
def procesar_devolucion_venta_automatico(sender, instance, created, **kwargs):
    """
    SEGURIDAD FINANCIERA: Cuando se CREA una devolución de venta:
    1. Crea automáticamente MovimientoInventario (entrada de retorno) en farmacia/models
    2. Actualiza el stock del producto
    3. Registra el reembolso en MovimientoCaja
    
    LÓGICA DE NEGOCIO:
    - Solo se ejecuta al CREAR (created=True), no al actualizar
    - Verifica que no se haya reintegrado antes (evitar duplicados)
    - Crea movimiento de inventario con tipo 'ENTRADA_DEVOLUCION'
    - Registra el reembolso en MovimientoCaja
    
    PROPÓSITO LEGAL:
    - Cuadre automático de inventario (NOM-072-SSA1-2012)
    - Trazabilidad de reembolsos
    - Prevención de fraude (doble reembolso)
    
    post_save: Se ejecuta DESPUÉS de guardar (para tener el ID de la devolución)
    
    Args:
        sender: Modelo DevolucionVenta
        instance: Instancia de la devolución
        created: True si es nuevo registro, False si es actualización
        **kwargs: Argumentos adicionales
    """
    from core.models import DevolucionVenta, MovimientoCaja, Lote
    from decimal import Decimal
    
    # Solo ejecutar al crear (no al actualizar)
    if not created:
        return
    
    # Verificar que no se haya procesado antes (evitar duplicados)
    if instance.reintegrado_inventario:
        logger.info(f"Devolución {instance.id} ya fue reintegrada. Saltando signal.")
        return
    
    try:
        with transaction.atomic():
            logger.info(f"🔄 Signal: Procesando devolución de venta #{instance.id}")
            
            # ==============================================================
            # PASO 1: CREAR MOVIMIENTO DE INVENTARIO (ENTRADA DE RETORNO)
            # ==============================================================
            
            producto = instance.detalle_venta.producto
            cantidad_devuelta = instance.cantidad_devuelta
            
            # Buscar el lote del que se vendió (si se registró)
            lote_devolucion = instance.lote_reintegrado
            
            if not lote_devolucion:
                # Buscar lotes disponibles del producto (Lote no tiene empresa; producto.empresa scopes)
                lotes_producto = Lote.objects.filter(
                    producto=producto
                ).order_by('-fecha_registro').first()
                
                if lotes_producto:
                    lote_devolucion = lotes_producto
                else:
                    # Crear lote de devolución (Lote requiere fecha_caducidad; usar fecha lejana si no hay)
                    from datetime import date, timedelta
                    logger.warning(
                        f"Devolución {instance.id}: No se encontró lote. "
                        f"Creando nuevo lote para devolución."
                    )
                    fecha_caducidad_def = date.today() + timedelta(days=365)
                    lote_devolucion = Lote.objects.create(
                        producto=producto,
                        numero_lote=f"DEV-{instance.id}",
                        cantidad=0,  # Se incrementará con el movimiento
                        fecha_caducidad=fecha_caducidad_def,
                    )
            
            # Crear movimiento de inventario (ENTRADA); farmacia usa ENTRADA_DEVOLUCION y requiere costo_unitario y usuario_responsable
            from decimal import Decimal as Dec
            costo_unit = getattr(instance.detalle_venta, 'precio_unitario', None) or getattr(producto, 'precio_compra', None) or 0
            costo_unit = Dec(str(costo_unit)) if costo_unit is not None else Dec('0')
            cantidad_dec = Dec(str(cantidad_devuelta))
            usuario_resp = instance.autorizado_por or instance.solicitado_por
            if not usuario_resp and instance.empresa_id:
                usuario_resp = instance.empresa.usuarios.filter(is_active=True).first()
            if not usuario_resp:
                logger.warning(f"Devolución #{instance.id}: sin usuario para MovimientoInventario; saltando signal.")
                return
            movimiento_inventario = MovimientoInventario.objects.create(
                empresa=instance.empresa,
                sucursal=instance.sucursal,
                tipo_movimiento='ENTRADA_DEVOLUCION',
                producto=producto,
                lote=lote_devolucion,
                cantidad=cantidad_dec,
                costo_unitario=costo_unit,
                usuario_responsable=usuario_resp,
                observaciones=f"Devolución #{instance.id} - Razón: {instance.get_razon_display()}",
            )
            # MovimientoInventario.save() ya actualizó lote y producto.stock; no duplicar actualización.
            
            # Marcar el lote en la devolución
            instance.lote_reintegrado = lote_devolucion
            instance.reintegrado_inventario = True
            instance.fecha_reintegracion = timezone.now()
            instance.save(update_fields=['lote_reintegrado', 'reintegrado_inventario', 'fecha_reintegracion'])
            
            logger.info(
                f"  ✅ MovimientoInventario #{movimiento_inventario.id} creado: "
                f"+{cantidad_devuelta} unidades de {producto.nombre}"
            )
            
            # ==============================================================
            # PASO 2: REGISTRAR REEMBOLSO EN CAJA
            # ==============================================================
            
            monto_reembolso = instance.monto_devuelto
            
            if monto_reembolso > 0:
                sucursal_caja = instance.sucursal
                if not sucursal_caja and instance.empresa_id:
                    sucursal_caja = instance.empresa.sucursales.filter(activa=True).first()
                if not sucursal_caja:
                    logger.warning(f"Devolución #{instance.id}: sin sucursal; no se crea MovimientoCaja de reembolso.")
                else:
                    movimiento_caja = MovimientoCaja.objects.create(
                        caja_nombre=f"Caja {sucursal_caja.nombre}" if sucursal_caja else "Caja Principal",
                        empresa=instance.empresa,
                        sucursal=sucursal_caja,
                        tipo_movimiento='EGRESO',
                        concepto='REEMBOLSO_DEVOLUCION',
                        monto=monto_reembolso,
                        usuario_responsable=usuario_resp,
                        referencia=f"Reembolso devolución #{instance.id} - {instance.get_razon_display()}",
                        devolucion_venta=instance,
                    )
                    logger.info(
                        f"  ✅ MovimientoCaja #{movimiento_caja.id} creado: "
                        f"Reembolso de ${monto_reembolso:.2f}"
                    )
            else:
                logger.warning(
                    f"  ⚠️  Devolución {instance.id}: Monto devuelto es 0. "
                    f"No se crea MovimientoCaja."
                )
            
            logger.info(
                f"✅ Signal completado: Devolución #{instance.id} procesada. "
                f"Inventario actualizado (+{cantidad_devuelta}) y reembolso registrado (${monto_reembolso:.2f})"
            )
            
            # Opcional: Enviar notificación a gerencia
            # enviar_notificacion_devolucion(instance)
    
    except Exception as e:
        logger.error(
            f"❌ Error en signal procesar_devolucion_venta_automatico. "
            f"DevolucionVenta: {instance.id}, Error: {str(e)}",
            exc_info=True
        )
        # No lanzar excepción para no bloquear el guardado de la devolución
