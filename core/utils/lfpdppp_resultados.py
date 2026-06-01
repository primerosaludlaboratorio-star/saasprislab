"""
LFPDPPP — Comunicación digital de resultados clínicos (WhatsApp / correo con enlace).

Requiere registro de ConsentimientoInformado con aceptación de privacidad y tratamiento.
El alta en recepción crea ese registro; pacientes sin fila de consentimiento no deben
recibir enlaces por canales digitales hasta regularizar su expediente.
"""
import logging

logger = logging.getLogger(__name__)


def paciente_autorizado_canal_digital_resultados(paciente) -> bool:
    """
    True si existe consentimiento vigente (último por fecha) con privacidad y tratamiento aceptados.
    """
    if not paciente or not getattr(paciente, 'pk', None):
        return False
    from core.models import ConsentimientoInformado

    c = (
        ConsentimientoInformado.objects.filter(paciente_id=paciente.pk)
        .order_by('-fecha_firma')
        .only('acepta_privacidad', 'acepta_procesamiento', 'pk')
        .first()
    )
    if not c:
        logger.info('LFPDPPP resultados digitales: sin ConsentimientoInformado paciente_id=%s', paciente.pk)
        return False
    ok = bool(c.acepta_privacidad and c.acepta_procesamiento)
    if not ok:
        logger.info(
            'LFPDPPP resultados digitales: consentimiento incompleto paciente_id=%s consentimiento_id=%s',
            paciente.pk,
            c.pk,
        )
    return ok
