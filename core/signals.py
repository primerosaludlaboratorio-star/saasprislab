"""
PRISLAB V5.0 - SIGNALS (EVENTOS DEL SISTEMA)
=============================================
Fecha: 1 de Febrero de 2026
Objetivo: Automatizaciones y efectos secundarios de acciones del usuario

FILOSOFÍA:
- Separación de responsabilidades (no meter lógica compleja en views.py)
- Signals para efectos secundarios (enviar emails, actualizar inventarios, etc.)
- dispatch_uid para prevenir ejecución doble

REGLA DE ORO:
- Si una acción debe ejecutarse CADA VEZ que se guarda un modelo: usa signals
- Si es condicional o tiene lógica compleja: usa services.py
"""

from django.db.models.signals import post_save, pre_save, pre_delete, post_delete
from django.dispatch import receiver
from django.db import transaction
import logging

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
                    logger.error(
                        f"[CAJA-v1.14] Venta #{instance.id}: empresa sin sucursales; "
                        "no se puede crear MovimientoCaja (sucursal_id NOT NULL)."
                    )
                    _bg.error(
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


# ==============================================================================
# SIGNAL: GENERAR FOLIO AUTOMÁTICO PARA ÓRDEN DE LABORATORIO
# ==============================================================================

@receiver(pre_save, sender='core.OrdenDeServicio', dispatch_uid='generar_folio_orden_unico')
def generar_folio_orden_automatico(sender, instance, **kwargs):
    """
    Genera automáticamente el folio de una orden de laboratorio si no existe.
    
    Formato: LAB-SUCURSAL-AÑO-CONSECUTIVO
    Ejemplo: LAB-001-2026-00123
    
    pre_save: Se ejecuta ANTES de guardar (para asignar el folio antes de insertar en DB)
    """
    from datetime import datetime
    from core.models import OrdenDeServicio
    
    # Solo si no tiene folio asignado
    if not instance.folio_orden:
        año = datetime.now().year
        sucursal_codigo = instance.empresa.codigo_sucursal if hasattr(instance.empresa, 'codigo_sucursal') else '001'
        
        # Contar órdenes existentes este año
        ultimas_ordenes = OrdenDeServicio.objects.filter(
            empresa=instance.empresa,
            fecha_creacion__year=año
        ).count()
        
        consecutivo = str(ultimas_ordenes + 1).zfill(5)
        instance.folio_orden = f"LAB-{sucursal_codigo}-{año}-{consecutivo}"
        
        logger.info(f"✓ Folio generado automáticamente: {instance.folio_orden}")


# ==============================================================================
# CONFIGURACIÓN: REGISTRAR SIGNALS EN APPS
# ==============================================================================

"""
Para que los signals funcionen, deben registrarse en el archivo apps.py del módulo 'core':

# core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        import core.signals  # Importar signals al iniciar la app
"""


# ==============================================================================
# SIGNAL: AUDITORÍA FORENSE DE RESULTADOS DE LABORATORIO (PASO 2A)
# ==============================================================================

@receiver(pre_save, sender='core.ResultadoParametro', dispatch_uid='auditoria_resultado_parametro_unico')
def crear_historial_resultado_automatico(sender, instance, **kwargs):
    """
    AUDITORÍA FORENSE: Cuando se MODIFICA un resultado de laboratorio, 
    automáticamente crea un registro en HistorialResultados con:
    - Usuario que hizo el cambio
    - Fecha y hora exacta
    - Valor anterior y valor nuevo
    - IP del usuario (si está disponible)
    
    LÓGICA DE NEGOCIO:
    - Solo se ejecuta al EDITAR (instance.pk existe), no al crear
    - Compara valor anterior vs valor nuevo
    - Si son diferentes, registra el cambio en HistorialResultados
    
    PROPÓSITO LEGAL:
    - Trazabilidad completa de modificaciones (NOM-059-SSA1-2015)
    - Auditoría forense para casos legales
    - Detección de fraude o manipulación de resultados
    
    pre_save: Se ejecuta ANTES de guardar para capturar el valor anterior
    
    Args:
        sender: Modelo ResultadoParametro
        instance: Instancia del resultado que se está modificando
        **kwargs: Argumentos adicionales (update_fields, raw, using)
    """
    from core.models import ResultadoParametro, HistorialResultados
    
    # Solo ejecutar si es una EDICIÓN (no creación)
    if not instance.pk:
        return
    
    try:
        # Obtener el valor anterior de la base de datos
        valor_anterior_obj = ResultadoParametro.objects.filter(pk=instance.pk).first()
        
        if not valor_anterior_obj:
            logger.warning(f"No se encontró ResultadoParametro con pk={instance.pk} para auditoría")
            return
        
        valor_anterior = valor_anterior_obj.valor
        valor_nuevo = instance.valor
        
        # Solo registrar si el valor cambió
        if valor_anterior != valor_nuevo:
            logger.info(
                f"🔍 Signal: Cambio detectado en resultado {instance.pk}. "
                f"Anterior: '{valor_anterior}' → Nuevo: '{valor_nuevo}'"
            )
            
            # Obtener información del usuario (si está disponible en el contexto)
            usuario_modificador = None
            ip_address = None
            
            # Intentar obtener usuario del contexto (request)
            # Nota: El usuario debe pasarse desde la vista usando instance._modificado_por
            if hasattr(instance, '_modificado_por'):
                usuario_modificador = instance._modificado_por
            
            if hasattr(instance, '_ip_address'):
                ip_address = instance._ip_address
            
            # Crear registro de auditoría (modelo usa valor_*_texto/numero, modificado_por, razon_cambio, ip_address)
            modificado_por = usuario_modificador
            if not modificado_por and valor_anterior_obj.orden and valor_anterior_obj.orden.empresa_id:
                from core.models import Usuario
                modificado_por = Usuario.objects.filter(empresa_id=valor_anterior_obj.orden.empresa_id).first()
            if modificado_por:
                try:
                    val_ant_num = float(valor_anterior) if valor_anterior not in (None, '') else None
                    val_nue_num = float(valor_nuevo) if valor_nuevo not in (None, '') else None
                except (ValueError, TypeError):
                    val_ant_num = None
                    val_nue_num = None
                from decimal import Decimal
                historial = HistorialResultados.objects.create(
                    resultado_parametro=valor_anterior_obj,
                    modificado_por=modificado_por,
                    valor_anterior_texto=str(valor_anterior) if valor_anterior is not None else None,
                    valor_nuevo_texto=str(valor_nuevo) if valor_nuevo is not None else None,
                    valor_anterior_numerico=Decimal(str(valor_anterior)) if val_ant_num is not None else None,
                    valor_nuevo_numerico=Decimal(str(valor_nuevo)) if val_nue_num is not None else None,
                    razon_cambio=f"Cambio automático registrado: {valor_anterior} → {valor_nuevo}",
                    ip_address=ip_address or '0.0.0.0',
                )
                logger.info(
                    f"✅ Auditoría forense registrada: HistorialResultados #{historial.id} "
                    f"para ResultadoParametro #{instance.pk}"
                )
            
            # ── R107: Registrar en AuditLog global ──
            try:
                from core.services.audit_service import registrar_auditoria
                registrar_auditoria(
                    accion='UPDATE',
                    modelo='ResultadoParametro',
                    objeto_id=str(instance.pk),
                    datos_anteriores={'valor': valor_anterior},
                    datos_nuevos={'valor': valor_nuevo},
                    usuario=usuario_modificador,
                )
            except Exception:
                pass
            
            # Opcional: Enviar alerta si el cambio es sospechoso
            # Por ejemplo, si el valor cambia más de 50%
            try:
                valor_ant_num = float(valor_anterior)
                valor_new_num = float(valor_nuevo)
                cambio_porcentual = abs((valor_new_num - valor_ant_num) / valor_ant_num * 100)
                
                if cambio_porcentual > 50:
                    logger.warning(
                        f"⚠️  ALERTA FORENSE: Cambio significativo ({cambio_porcentual:.1f}%) en "
                        f"resultado {instance.pk}. Usuario: {usuario_modificador or 'DESCONOCIDO'}"
                    )
                    # Alerta forense registrada en logger. Notificación push al jefe de laboratorio
                    # se activará cuando el módulo de notificaciones esté migrado.
            except (ValueError, ZeroDivisionError, TypeError):
                # Valores no numéricos o división por cero, ignorar cálculo porcentual
                pass
    
    except Exception as e:
        logger.error(
            f"❌ Error en signal crear_historial_resultado_automatico. "
            f"ResultadoParametro: {instance.pk}, Error: {str(e)}",
            exc_info=True
        )
        # No lanzar excepción para no bloquear el guardado del resultado


# ==============================================================================
# SIGNAL: ALERTA DE PÁNICO - RESULTADO CRÍTICO DE LABORATORIO
# ==============================================================================

@receiver(post_save, sender='core.ResultadoParametro',
          dispatch_uid='alerta_panico_resultado_critico_unico')
def enviar_alerta_panico_resultado(sender, instance, created, **kwargs):
    """
    TRIGGER DE PÁNICO: Si un resultado de laboratorio tiene es_critico=True
    o cae fuera del rango de pánico del Estudio, envía un correo inmediato
    al Director indicando Paciente, Folio y el valor fuera de rango.

    Se ejecuta en create Y update (un resultado puede marcarse como crítico
    después de ser capturado).
    """
    from django.conf import settings as django_settings
    from django.core.mail import send_mail

    # Verificar si es crítico directamente
    es_critico = getattr(instance, 'es_critico', False)

    # Si no está marcado como crítico, verificar contra rangos de pánico del estudio
    if not es_critico and instance.valor:
        try:
            estudio = instance.parametro.estudio
            rango_min = getattr(estudio, 'rango_panico_min', None)
            rango_max = getattr(estudio, 'rango_panico_max', None)

            if rango_min is not None or rango_max is not None:
                val_num = float(instance.valor)
                if rango_min is not None and val_num < float(rango_min):
                    es_critico = True
                if rango_max is not None and val_num > float(rango_max):
                    es_critico = True

                # Actualizar el campo es_critico si detectamos pánico
                if es_critico and not instance.es_critico:
                    from core.models import ResultadoParametro as RP
                    RP.objects.filter(pk=instance.pk).update(es_critico=True)
        except (ValueError, TypeError, AttributeError):
            pass

    if not es_critico:
        return

    director_email = getattr(django_settings, 'DIRECTOR_EMAIL', '')
    if not director_email:
        logger.warning(
            f"[PANIC] ResultadoParametro {instance.pk} es CRÍTICO pero "
            f"DIRECTOR_EMAIL no está configurado."
        )
        return

    try:
        orden = instance.orden
        paciente = orden.paciente
        paciente_nombre = getattr(paciente, 'nombre_completo', None) or (paciente.get_full_name() if hasattr(paciente, 'get_full_name') else str(paciente))
        folio = orden.folio_orden or f"ORD-{orden.id}"
        parametro_nombre = instance.parametro.nombre if instance.parametro else 'Desconocido'
        valor = instance.valor
        unidad = instance.parametro.unidad or '' if instance.parametro else ''

        asunto = (
            f"🚨 VALOR DE PÁNICO - {parametro_nombre}: {valor} {unidad} | "
            f"Paciente: {paciente_nombre} | Folio: {folio}"
        )

        cuerpo = f"""
🚨 ALERTA DE VALOR DE PÁNICO - PRISLAB
{'='*55}

RESULTADO CRÍTICO DETECTADO
{'─'*55}

  Paciente:     {paciente_nombre}
  Folio Orden:  {folio}
  Parámetro:    {parametro_nombre}
  VALOR:        {valor} {unidad}
  Crítico:      SÍ - VALOR DE PÁNICO

{'─'*55}
ACCIÓN REQUERIDA:
  1. Verificar resultado con segunda muestra
  2. Contactar al médico tratante
  3. Documentar la notificación al paciente
{'='*55}

Este es un correo automático de PRISLAB.
Generado al detectar un valor fuera de rango de pánico.
"""

        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[director_email],
            fail_silently=True,
        )

        logger.info(
            f"🚨 [PANIC] Alerta enviada a {director_email}: "
            f"{parametro_nombre}={valor} para paciente {paciente_nombre} (Folio: {folio})"
        )

    except Exception as e:
        logger.error(
            f"❌ [PANIC] Error enviando alerta de pánico: {e}",
            exc_info=True
        )


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
    from farmacia.models import MovimientoInventario  # Importar desde farmacia
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
            from django.utils import timezone
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


# ==============================================================================
# CICLO 11: AUDITORÍA FORENSE EN BORRADO CRÍTICO (Paciente / Orden)
# ==============================================================================

@receiver(pre_delete, sender='core.Paciente', dispatch_uid='audit_log_paciente_delete')
def audit_log_paciente_delete(sender, instance, **kwargs):
    """Registra en AuditLog cuando se elimina un paciente (quién/cuándo desde vista; qué desde signal)."""
    try:
        from core.models import AuditLog
        empresa = getattr(instance, 'empresa', None)
        if not empresa:
            return  # Multi-tenant: no usar Empresa.objects.first(); solo auditar cuando hay empresa
        snapshot = {
            'id': instance.id,
            'nombre_completo': getattr(instance, 'nombre_completo', None) or getattr(instance, 'nombre', ''),
            'curp': getattr(instance, 'curp', None),
            'folio_expediente': getattr(instance, 'numero_expediente', None),
        }
        AuditLog.objects.create(
            empresa=empresa,
            usuario=None,
            accion='DELETE',
            modelo_afectado='Paciente',
            objeto_id=str(instance.id),
            datos_anteriores=snapshot,
            datos_nuevos=None,
        )
        logger.info(f"[AUDIT] Paciente eliminado (signal): #{instance.id} - {snapshot.get('nombre_completo', '')}")
    except Exception as e:
        logger.error(f"[AUDIT] Error en audit_log_paciente_delete: {e}")


@receiver(pre_delete, sender='core.OrdenDeServicio', dispatch_uid='audit_log_orden_delete')
def audit_log_orden_delete(sender, instance, **kwargs):
    """Registra en AuditLog cuando se elimina una orden de servicio."""
    try:
        from core.models import AuditLog
        empresa = getattr(instance, 'empresa', None)
        if not empresa:
            return  # Multi-tenant: no usar Empresa.objects.first(); solo auditar cuando hay empresa
        snapshot = {
            'id': instance.id,
            'folio_orden': getattr(instance, 'folio_orden', None),
            'estado': getattr(instance, 'estado', None),
            'total': str(instance.total) if getattr(instance, 'total', None) is not None else None,
            'paciente_id': instance.paciente_id if hasattr(instance, 'paciente_id') else None,
        }
        AuditLog.objects.create(
            empresa=empresa,
            usuario=None,
            accion='DELETE',
            modelo_afectado='OrdenDeServicio',
            objeto_id=str(instance.id),
            datos_anteriores=snapshot,
            datos_nuevos=None,
        )
        logger.info(f"[AUDIT] OrdenDeServicio eliminada (signal): #{instance.id} - {snapshot.get('folio_orden', '')}")
    except Exception as e:
        logger.error(f"[AUDIT] Error en audit_log_orden_delete: {e}")


# ==============================================================================
# SIGNAL: AUTO-ETIQUETADO DE TENANT (PILAR 1 — PRISLAB V6.0)
# ==============================================================================
# Garantiza que NINGÚN objeto se cree sin empresa cuando hay un usuario en sesión.
# Esto elimina el vector de "escape de tenant" por omisión de empresa en vistas.

# Lista de modelos que DEBEN tener empresa asignada automáticamente.
# Excluimos modelos globales (ConfiguracionModulos se crea manualmente, etc.)
_MODELOS_TENANT_AWARE = {
    'core.Paciente', 'core.OrdenDeServicio', 'core.Venta', 'core.Lote',
    'core.Producto', 'core.Empleado', 'core.Medico', 'core.Receta',
    'core.HistoriaClinica', 'core.ConsultaMedica', 'core.DetalleOrden',
    'core.DetalleVenta', 'core.Pago', 'core.Gasto', 'core.GastoOperativo',
    'core.MovimientoCaja', 'core.GastoCaja', 'core.TomaMuestra',
    'core.BitacoraEntregaResultados', 'core.ResultadoParametro',
    'laboratorio.Resultado',
    'farmacia.MovimientoInventario', 'farmacia.MermaFarmacia',
}


@receiver(pre_save, dispatch_uid='auto_etiquetado_tenant_v6')
def auto_assign_empresa(sender, instance, **kwargs):
    """
    SIGNAL UNIVERSAL: Si un objeto de un modelo tenant-aware se está guardando
    sin empresa, la asigna automáticamente desde el contexto del hilo.

    REGLAS:
    1. Solo actúa sobre modelos en _MODELOS_TENANT_AWARE.
    2. Solo asigna si empresa_id es None (respeta asignación manual).
    3. Solo asigna si hay empresa en el contexto del hilo actual.
    4. No actúa en objetos ya existentes (pk is not None and empresa_id set).
    """
    model_label = f'{sender._meta.app_label}.{sender.__name__}'
    if model_label not in _MODELOS_TENANT_AWARE:
        return

    if getattr(instance, 'empresa_id', None):
        return  # Ya tiene empresa, no sobrescribir

    try:
        from core.tenant import get_current_empresa
        empresa = get_current_empresa()
        if empresa:
            instance.empresa = empresa
            logger.debug(
                '[TENANT] Auto-etiquetado: %s → empresa=%s',
                model_label, empresa.pk
            )
    except Exception as exc:
        logger.warning('[TENANT] auto_assign_empresa falló: %s', exc)


@receiver(post_save, sender='core.Usuario', dispatch_uid='auto_empresa_nuevo_usuario_v6')
def auto_assign_empresa_nuevo_usuario(sender, instance, created, **kwargs):
    """
    Cuando se crea un nuevo usuario desde el Admin de un tenant,
    lo vincula automáticamente a la empresa del creador (hilo activo).

    Esto previene que un admin-cliente pueda crear usuarios sin empresa
    o asignarlos a otra empresa.
    """
    if not created:
        return

    if getattr(instance, 'empresa_id', None):
        return  # Ya tiene empresa

    # No tocar al superusuario PRISLAB
    if instance.is_superuser:
        return

    try:
        from core.tenant import get_current_empresa
        empresa = get_current_empresa()
        if empresa:
            instance.empresa = empresa
            # Guardamos solo el campo empresa para evitar recursión
            type(instance).objects.filter(pk=instance.pk).update(empresa=empresa)
            logger.info(
                '[TENANT] Nuevo usuario %s vinculado a empresa %s',
                instance.username, empresa.pk
            )
    except Exception as exc:
        logger.warning('[TENANT] auto_assign_empresa_nuevo_usuario falló: %s', exc)
