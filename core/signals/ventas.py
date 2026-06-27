"""
PRISLAB V5.0 - SIGNALS: VENTAS
Receta → orden, descuento de inventario PEPS y registro de caja (Bankguard).
"""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver


logger = logging.getLogger('signals')


# ==============================================================================
# SIGNAL: RECETA → ORDEN DE VENTA (FARMACIA)
# ==============================================================================

@receiver(post_save, sender='core.Receta', dispatch_uid='receta_crear_orden_venta_unico')
def crear_orden_venta_desde_receta(sender, instance, created, **kwargs):
    """
    Cuando se crea una RECETA MÉDICA, automáticamente crea una ORDEN DE VENTA
    en farmacia con los medicamentos prescritos.

    DESHABILITADO (Ciclo 3): core.Venta usa usuario/paciente/receta/total, no
    usuario_vendedor/cliente/receta_origen/tipo_venta/calcular_total. Rehabilitar
    cuando se alinee el flujo Receta→Venta con los campos reales del modelo.
    """
    return  # Deshabilitado hasta alinear con core.Venta (usuario obligatorio, total, etc.)


# ==============================================================================
# SIGNAL: ACTUALIZAR STOCK AL COMPLETAR VENTA
# ==============================================================================

@receiver(post_save, sender='core.Venta', dispatch_uid='venta_descontar_inventario_unico')
def descontar_inventario_al_completar_venta(sender, instance, created, **kwargs):
    """
    Cuando una VENTA cambia de estado a 'PAGADO' o 'COMPLETADO', descuenta
    automáticamente el stock de los productos vendidos.
    
    LÓGICA DE NEGOCIO (PEPS - Primero En Entrar, Primero En Salir):
    - Busca el lote más antiguo con stock disponible
    - Descuenta la cantidad del lote
    - Si un lote se queda sin stock, pasa al siguiente lote
    
    IDEMPOTENCIA GARANTIZADA (v1.13):
    - Usa select_for_update() para bloquear la fila Venta
    - Verifica campo inventario_descontado en BD (no flag en memoria)
    - Si ya fue descontado, retorna sin error
    
    dispatch_uid: Previene ejecución doble
    """
    from core.models import Venta, Lote
    
    # Solo ejecutar si cambió a estado pagado/completado (Venta usa COMPLETADA)
    if instance.estado not in ['PAGADO', 'COMPLETADO', 'COMPLETADA']:
        return
    
    try:
        with transaction.atomic():
            # IDEMPOTENCIA: Bloquear fila Venta y verificar estado actual en BD
            venta_bloqueada = Venta.objects.select_for_update().get(pk=instance.pk)
            
            # Si ya se descontó (campo persistente en BD), no hacer nada
            if venta_bloqueada.inventario_descontado:
                logger.info(f"Signal: Venta #{instance.id} ya tiene inventario descontado (idempotencia).")
                return
            
            logger.info(f"Signal: Descontando inventario para venta #{instance.id}")
            
            for detalle in instance.detalles.all():
                producto = detalle.producto
                cantidad_a_descontar = detalle.cantidad
                
                # Si ya tiene lote asignado (vendido de un lote específico)
                if detalle.lote_vendido:
                    lote = detalle.lote_vendido
                    # Bloquear lote para evitar race conditions
                    lote_bloqueado = Lote.objects.select_for_update().get(pk=lote.pk)
                    if lote_bloqueado.cantidad >= cantidad_a_descontar:
                        lote_bloqueado.cantidad -= cantidad_a_descontar
                        lote_bloqueado.save()
                        logger.info(f"  ✓ Descontado {cantidad_a_descontar} de lote {lote_bloqueado.numero_lote}")
                    else:
                        logger.error(
                            f"  ❌ Stock insuficiente en lote {lote_bloqueado.numero_lote}. "
                            f"Requerido: {cantidad_a_descontar}, Disponible: {lote_bloqueado.cantidad}"
                        )
                
                # Si no tiene lote asignado, usar PEPS (Primero En Entrar, Primero En Salir)
                else:
                    lotes_disponibles = Lote.objects.filter(
                        producto=producto,
                        cantidad__gt=0
                    ).order_by('fecha_caducidad', 'fecha_registro')  # PEPS
                    
                    cantidad_restante = cantidad_a_descontar
                    
                    for lote in lotes_disponibles:
                        if cantidad_restante == 0:
                            break
                        
                        # Bloquear cada lote para evitar race conditions
                        lote_bloqueado = Lote.objects.select_for_update().get(pk=lote.pk)
                        
                        if lote_bloqueado.cantidad >= cantidad_restante:
                            # Este lote tiene suficiente stock
                            lote_bloqueado.cantidad -= cantidad_restante
                            lote_bloqueado.save()
                            logger.info(
                                f"  ✓ Descontado {cantidad_restante} de lote {lote_bloqueado.numero_lote} (PEPS)"
                            )
                            cantidad_restante = 0
                        else:
                            # Este lote no es suficiente, usar todo y pasar al siguiente
                            cantidad_restante -= lote_bloqueado.cantidad
                            logger.info(
                                f"  ✓ Descontado {lote_bloqueado.cantidad} de lote {lote_bloqueado.numero_lote} (completo, PEPS)"
                            )
                            lote_bloqueado.cantidad = 0
                            lote_bloqueado.save()
                    
                    if cantidad_restante > 0:
                        logger.error(
                            f"  ❌ Stock insuficiente para producto {producto.nombre}. "
                            f"Faltaron {cantidad_restante} unidades."
                        )
                
                # Actualizar stock total del producto
                producto.stock = sum(l.cantidad for l in producto.lotes.all())
                producto.save()
            
            # IDEMPOTENCIA: Marcar en BD que ya se descontó (persistente)
            # FIX v1.13: Usar .update() en lugar de .save() para evitar re-disparar post_save
            Venta.objects.filter(pk=venta_bloqueada.pk).update(inventario_descontado=True)
            logger.info(f"✓ Signal completado: Inventario descontado para venta #{instance.id}")
    
    except Exception as e:
        logger.error(
            f"❌ Error en signal descontar_inventario_al_completar_venta. "
            f"Venta: {instance.id}, Error: {str(e)}",
            exc_info=True
        )


# ==============================================================================
# SIGNAL: REGISTRAR MOVIMIENTO DE CAJA AL COMPLETAR VENTA (SENTINEL 2.0)
# ==============================================================================

@receiver(post_save, sender='core.Venta', dispatch_uid='registrar_movimiento_caja_venta_v114')
def registrar_movimiento_caja_al_vender(sender, instance, created, **kwargs):
    """
    Bankguard v1.14 — Signal idempotente para MovimientoCaja.
    
    Al completar una venta (estado PAGADO/COMPLETADO), registra automáticamente
    un MovimientoCaja de tipo INGRESO con protección contra:
    - Reintentos HTTP
    - Doble click
    - Workers paralelos (Celery)
    - Deadlocks (select_for_update + retry)
    
    Mecanismos:
    1. idempotency_key determinista: venta_{id}_ingreso_{empresa_id}
    2. select_for_update() en orden correcto (Venta → MovimientoCaja)
    3. get_or_create con idempotency_key
    4. Retry loop con exponential backoff (3 intentos)
    5. Notificación a Director si falla persistente
    """
    from core.models import Venta, MovimientoCaja
    from django.db import transaction, OperationalError
    from decimal import Decimal
    import time

    _bg = logging.getLogger('bankguard')

    if instance.estado not in ['PAGADO', 'COMPLETADO', 'COMPLETADA']:
        return

    # Ventas de cortesía tienen total $0; no se registra movimiento
    total_venta = instance.total or Decimal('0')
    if total_venta <= 0:
        logger.info(f"[CAJA-v1.14] Venta #{instance.id} cortesía (${total_venta}); skip")
        return
    
    # IDEMPOTENCY_KEY determinista (mismo resultado para misma venta)
    idempotency_key = f"venta_{instance.id}_ingreso_{instance.empresa_id}"
    
    # RETRY LOOP con exponential backoff
    max_retries = 3
    for intento in range(max_retries):
        try:
            with transaction.atomic():
                # BLOQUEO 1: Venta (padre) - orden correcto para evitar deadlock
                venta_bloqueada = Venta.objects.select_for_update(nowait=False).get(pk=instance.pk)
                sucursal_caja = getattr(venta_bloqueada, 'sucursal', None)
                if sucursal_caja is None:
                    sucursal_caja = venta_bloqueada.empresa.sucursales.filter(
                        activa=True
                    ).order_by('pk').first()
                if sucursal_caja is None:
                    sucursal_caja = venta_bloqueada.empresa.sucursales.order_by('pk').first()
                if sucursal_caja is None:
                    logger.warning(
                        f"[CAJA-v1.14] Venta #{instance.id}: empresa sin sucursales; "
                        "no se puede crear MovimientoCaja (sucursal_id NOT NULL)."
                    )
                    _bg.warning(
                        'MovimientoCaja omitido: empresa sin sucursal venta_id=%s empresa_id=%s',
                        instance.id,
                        venta_bloqueada.empresa_id,
                    )
                    return

                # BLOQUEO 2: Buscar movimiento existente con idempotency_key
                # Usamos get_or_create para atomicidad
                movimiento, creado = MovimientoCaja.objects.select_for_update(nowait=False).get_or_create(
                    idempotency_key=idempotency_key,
                    defaults={
                        'empresa': venta_bloqueada.empresa,
                        'sucursal': sucursal_caja,
                        'caja_nombre': f"Caja {sucursal_caja.nombre}",
                        'usuario_responsable': getattr(venta_bloqueada, 'usuario', None),
                        'tipo_movimiento': 'INGRESO',
                        'concepto': 'VENTA',
                        'monto': total_venta,
                        'referencia': f'Venta #{venta_bloqueada.id}',
                        'venta': venta_bloqueada,
                    }
                )
                
                if creado:
                    logger.info(
                        f"[CAJA-v1.14] ✓ MovimientoCaja #{movimiento.id} creado "
                        f"para Venta #{instance.id}: ${total_venta}"
                    )
                    _bg.info(
                        'MovimientoCaja creado venta_id=%s movimiento_id=%s monto=%s',
                        instance.id,
                        movimiento.id,
                        total_venta,
                    )
                else:
                    logger.info(
                        f"[CAJA-v1.14] ↻ MovimientoCaja #{movimiento.id} ya existía "
                        f"(idempotencia) para Venta #{instance.id}"
                    )
                    _bg.info(
                        'MovimientoCaja idempotencia venta_id=%s movimiento_id=%s',
                        instance.id,
                        movimiento.id,
                    )
                
                return  # ÉXITO - salir del loop
        
        except OperationalError as e:
            # Deadlock o lock timeout
            if intento < max_retries - 1:
                wait_time = 2 ** intento  # 1s, 2s, 4s
                logger.warning(
                    f"[CAJA-v1.14] Deadlock intento {intento+1}/{max_retries} "
                    f"para Venta #{instance.id}, reintentando en {wait_time}s..."
                )
                _bg.warning(
                    'OperationalError caja reintento venta_id=%s intento=%s/%s espera_s=%s err=%s',
                    instance.id,
                    intento + 1,
                    max_retries,
                    wait_time,
                    e,
                )
                time.sleep(wait_time)
                continue
            else:
                logger.critical(
                    f"[CAJA-v1.14] ❌ Deadlock persistente tras {max_retries} intentos "
                    f"para Venta #{instance.id}: {e}"
                )
                _bg.error(
                    'OperationalError caja AGOTADO venta_id=%s intentos=%s err=%s',
                    instance.id,
                    max_retries,
                    e,
                )
                # NOTIFICAR A DIRECTOR (no bloquear la venta)
                _notificar_error_caja(
                    titulo="🚨 CRÍTICO: Deadlock en MovimientoCaja",
                    mensaje=f"No se pudo registrar MovimientoCaja para Venta #{instance.id} "
                            f"tras {max_retries} intentos. Error: {e}",
                    venta_id=instance.id,
                    monto=float(total_venta),
                )
                raise  # Re-lanzar para que Django lo maneje
        
        except Exception as e:
            logger.error(
                f"[CAJA-v1.14] Error inesperado en intento {intento+1} "
                f"para Venta #{instance.id}: {e}",
                exc_info=True
            )
            _bg.exception(
                'Error inesperado MovimientoCaja venta_id=%s intento=%s/%s',
                instance.id,
                intento + 1,
                max_retries,
            )
            if intento == max_retries - 1:
                _notificar_error_caja(
                    titulo="🚨 CRÍTICO: Error en MovimientoCaja",
                    mensaje=f"Error inesperado registrando caja para Venta #{instance.id}: {e}",
                    venta_id=instance.id,
                    monto=float(total_venta),
                )
                raise
            time.sleep(1)


def _notificar_error_caja(titulo, mensaje, venta_id, monto):
    """Notifica error crítico de caja al director vía email/Telegram."""
    from django.conf import settings
    
    # Email
    director_email = getattr(settings, 'DIRECTOR_EMAIL', None)
    if director_email:
        try:
            from django.core.mail import send_mail
            send_mail(
                subject=titulo,
                message=f"{mensaje}\n\nVenta: #{venta_id}\nMonto: ${monto:.2f}",
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@prislab.app'),
                recipient_list=[director_email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"[CAJA-v1.14] Falló notificación email: {e}")
    
    # Telegram (si está configurado)
    from core.services.telegram_outbound import send_telegram_message

    telegram_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    telegram_chat = getattr(settings, 'TELEGRAM_CISO_CHAT_ID', None)
    if telegram_token and telegram_chat:
        body = f"{titulo}\n\n{mensaje}\nVenta: #{venta_id}\nMonto: ${monto:.2f}"
        if not send_telegram_message(
            telegram_token, telegram_chat, body, parse_mode='HTML'
        ):
            logger.error('[CAJA-v1.14] Falló notificación Telegram (o credenciales ausentes)')
