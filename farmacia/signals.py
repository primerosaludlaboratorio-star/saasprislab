"""
PRISLAB - SIGNALS DE FARMACIA
==============================
Automatizaciones post-save para el módulo de Farmacia.

SIGNAL 1: CierreTurnoFarmacia → Email al Director con resumen de ingresos
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
import logging

logger = logging.getLogger('signals')


# ==============================================================================
# SIGNAL: CIERRE DE CAJA → EMAIL AL DIRECTOR
# ==============================================================================

@receiver(post_save, sender='farmacia.CierreTurnoFarmacia',
          dispatch_uid='cierre_turno_email_director_unico')
def enviar_resumen_cierre_caja(sender, instance, created, **kwargs):
    """
    Al cerrar una caja (CierreTurnoFarmacia), envía un correo automático
    al Director con el resumen de ingresos: Efectivo, Tarjeta, Transferencia,
    diferencias detectadas y si requiere revisión.

    Solo se ejecuta al CREAR el cierre (created=True).
    """
    if not created:
        return

    director_email = getattr(settings, 'DIRECTOR_EMAIL', '')
    if not director_email:
        logger.warning(
            f"[SIGNAL] Cierre {instance.folio}: DIRECTOR_EMAIL no configurado. "
            f"No se envía correo."
        )
        return

    try:
        # Construir datos del resumen
        efectivo_teorico = instance.efectivo_teorico or 0
        tarjeta_teorica = instance.tarjeta_teorico or 0
        vales_teorico = instance.vales_teorico or 0
        total_teorico = efectivo_teorico + tarjeta_teorica + vales_teorico

        efectivo_declarado = instance.efectivo_declarado or 0
        tarjeta_declarada = instance.tarjeta_declarado or 0
        vales_declarado = instance.vales_declarado or 0
        total_declarado = efectivo_declarado + tarjeta_declarada + vales_declarado

        diferencia = instance.diferencia_total or 0
        requiere_revision = instance.requiere_revision

        responsable = instance.usuario_responsable.get_full_name() if instance.usuario_responsable else 'N/A'
        sucursal = str(instance.sucursal) if instance.sucursal else 'N/A'

        # Construir asunto
        emoji_alerta = '🔴' if requiere_revision else '✅'
        asunto = (
            f"{emoji_alerta} PRISLAB - Cierre de Caja {instance.folio} | "
            f"Total: ${total_declarado:,.2f}"
        )

        # Construir cuerpo del email (texto plano)
        cuerpo = f"""
PRISLAB - RESUMEN DE CIERRE DE CAJA
{'='*50}

Folio: {instance.folio}
Sucursal: {sucursal}
Responsable: {responsable}
Fecha: {instance.fecha_cierre if hasattr(instance, 'fecha_cierre') else 'Hoy'}

{'─'*50}
INGRESOS TEÓRICOS (Sistema)
{'─'*50}
  Efectivo:       ${efectivo_teorico:>12,.2f}
  Tarjeta:        ${tarjeta_teorica:>12,.2f}
  Vales/Transf:   ${vales_teorico:>12,.2f}
  TOTAL TEÓRICO:  ${total_teorico:>12,.2f}

{'─'*50}
INGRESOS DECLARADOS (Cajero)
{'─'*50}
  Efectivo:       ${efectivo_declarado:>12,.2f}
  Tarjeta:        ${tarjeta_declarada:>12,.2f}
  Vales/Transf:   ${vales_declarado:>12,.2f}
  TOTAL DECLARADO:${total_declarado:>12,.2f}

{'─'*50}
DIFERENCIA:       ${diferencia:>12,.2f}  {'⚠️ REQUIERE REVISIÓN' if requiere_revision else '✅ OK'}
{'='*50}

Este correo fue generado automáticamente por PRISLAB.
"""

        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[director_email],
            fail_silently=True,
        )

        logger.info(
            f"✅ [SIGNAL] Email de cierre de caja {instance.folio} enviado a {director_email}"
        )

    except Exception as e:
        logger.error(
            f"❌ [SIGNAL] Error enviando email de cierre {instance.folio}: {e}",
            exc_info=True
        )
