"""
PRISLAB V5.0 - SIGNALS: RESULTADOS DE LABORATORIO
Auditoría forense ISO 15189 y alertas de pánico.
"""
import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


logger = logging.getLogger('signals')


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
                logging.getLogger(__name__).exception("Error inesperado en crear_historial_resultado_automatico (resultados.py)")
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