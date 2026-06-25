"""
CMMS V8.2 — Señales: Descuento Multi-Silo de Refacciones
=========================================================

Ajuste 1: Al registrar una SalidaRefaccionMantenimiento, el signal
descuenta automáticamente el stock del lote del silo correspondiente
usando GenericForeignKey.

Silos soportados:
  LAB        → inventario.LoteReactivoLab
  CONSULTORIO → inventario.LoteInsumoConsultorio
  GENERAL     → inventario.LoteInsumoGeneral

Cada lote tiene los campos `cantidad_actual` y `estado` que se actualizan.
"""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender='mantenimiento.SalidaRefaccionMantenimiento', dispatch_uid='cmms_salida_refaccion_auditoria_v118')
def descontar_refaccion_multi_silo(sender, instance, created, **kwargs):
    """
    Compatibilidad legacy: el descuento real ahora ocurre en
    mantenimiento.services.consumo_refacciones_service.registrar_consumo_refaccion.
    Esta señal queda únicamente como punto de auditoría sin mutar stock.
    """
    if not created:
        return

    logger.info(
        "CMMS Multi-Silo: salida %s registrada para ticket #%s en silo %s. "
        "El stock y costo histórico fueron procesados previamente por el servicio atómico.",
        instance.pk,
        instance.ticket_id,
        instance.silo_origen,
    )


# =============================================================================
# SIGNAL: LecturaSensorIoT → Ticket Crítico si fuera de rango
# =============================================================================

@receiver(post_save, sender='mantenimiento.LecturaSensorIoT')
def evaluar_lectura_iot(sender, instance, created, **kwargs):
    """
    Evalúa si la lectura está fuera del rango aceptable.
    Si es así:
      1. Marca fuera_de_rango = True en la lectura.
      2. Crea un TicketMantenimientoCMMS de prioridad CRITICA automáticamente.
      3. Genera NotificacionDiscrepancia al Director.
    Solo actúa en creaciones nuevas para evitar bucles.
    """
    if not created:
        return

    sensor = instance.sensor
    fuera = False
    razon_partes = []

    temp = float(instance.temperatura) if instance.temperatura is not None else None
    hum  = float(instance.humedad)     if instance.humedad is not None else None

    if temp is not None:
        t_min = float(sensor.temp_min_aceptable)
        t_max = float(sensor.temp_max_aceptable)
        if temp < t_min or temp > t_max:
            fuera = True
            razon_partes.append(
                f"Temperatura {temp}°C fuera del rango aceptable ({t_min}-{t_max}°C)"
            )

    if hum is not None and sensor.hum_min_aceptable and sensor.hum_max_aceptable:
        h_min = float(sensor.hum_min_aceptable)
        h_max = float(sensor.hum_max_aceptable)
        if hum < h_min or hum > h_max:
            fuera = True
            razon_partes.append(
                f"Humedad {hum}% fuera del rango aceptable ({h_min}-{h_max}%)"
            )

    if not fuera:
        return

    razon = ' | '.join(razon_partes)
    logger.warning("IoT ALERTA: %s — Sensor %s @ %s",
                   razon, sensor.codigo, instance.timestamp)

    try:
        with transaction.atomic():
            # Marcar lectura como fuera de rango
            LecturaSensorIoT = sender
            LecturaSensorIoT.objects.filter(pk=instance.pk).update(fuera_de_rango=True)

            # Crear ticket de mantenimiento CRITICO si no existe uno abierto
            from mantenimiento.models import TicketMantenimientoCMMS
            ticket_existente = TicketMantenimientoCMMS.objects.filter(
                empresa=instance.empresa,
                expediente=sensor.expediente if sensor.expediente else None,
                estado__in=('ABIERTO', 'EN_PROCESO'),
            ).first() if sensor.expediente else None

            ticket = None
            if not ticket_existente:
                descripcion = (
                    f"ALERTA IoT AUTOMÁTICA — Sensor: {sensor.codigo} ({sensor.nombre})\n"
                    f"Fecha/Hora: {instance.timestamp:%d/%m/%Y %H:%M}\n"
                    f"Lectura: T={temp}°C | H={hum}%\n"
                    f"Alerta: {razon}\n\n"
                    f"Acción requerida: Revisar condiciones del refrigerador/equipo de inmediato. "
                    f"Si la muestra ha estado expuesta, evaluar descarte."
                )
                ticket_kwargs = {
                    'empresa': instance.empresa,
                    'tipo_origen': 'CORRECTIVO',
                    'estado': 'ABIERTO',
                    'titulo': f'ALERTA IoT: {sensor.codigo} — {razon[:80]}',
                    'descripcion': descripcion,
                    'creado_por': None,
                }
                if sensor.expediente:
                    ticket_kwargs['expediente'] = sensor.expediente
                ticket = TicketMantenimientoCMMS.objects.create(**ticket_kwargs)

                # Vincular ticket a la lectura
                LecturaSensorIoT.objects.filter(pk=instance.pk).update(
                    fuera_de_rango=True,
                    ticket_generado=ticket,
                )

            # Notificación al Director
            try:
                from inventario.models import NotificacionDiscrepancia
                NotificacionDiscrepancia.objects.create(
                    empresa=instance.empresa,
                    tipo='STOCK_CRITICO',
                    nivel='CRITICO',
                    titulo=f'ALERTA IoT: {sensor.codigo} — {razon[:100]}',
                    detalle=(
                        f'Sensor: {sensor.codigo} — {sensor.nombre}\n'
                        f'Lectura: T={temp}°C | H={hum}%\n'
                        f'Rango aceptable: T {sensor.temp_min_aceptable}-{sensor.temp_max_aceptable}°C\n'
                        f'Timestamp: {instance.timestamp:%d/%m/%Y %H:%M}\n'
                        + (f'Ticket generado: #{ticket.pk}' if ticket else 'Ticket pre-existente')
                    ),
                )
            except Exception as exc:
                logger.error('IoT: Error creando NotificacionDiscrepancia: %s', exc)

    except Exception as exc:
        logger.error('IoT: Error procesando alerta fuera de rango: %s', exc, exc_info=True)
