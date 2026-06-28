"""
Escudo clínico v1.14 — notificación ISO automática desde umbrales LIMS.
Crea `NotificacionPanico` enlazada a ODS + ResultadoParametro cuando `validar_contra_rango` marca pánico.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.utils import timezone

logger = logging.getLogger('laboratorio.escudo_clinico_lims')

MARCA_ESCUDO = '[ESCUDO-LIMS v1.14]'


def _usuario_para_registro_automatico():
    from django.conf import settings

    User = get_user_model()
    raw = getattr(settings, 'PRISLAB_ESCUDO_USUARIO_ID', None)
    if raw is not None:
        try:
            uid = int(raw)
            u = User.objects.filter(pk=uid, is_active=True).first()
            if u:
                return u
            logger.error(
                'Escudo LIMS: PRISLAB_ESCUDO_USUARIO_ID=%s no existe o está inactivo — '
                'se usará fallback staff (alertas de pánico pueden quedar mal atribuidas). '
                'Ejecute verify_escudo_clinico o cron /cron/verify-escudo-clinico/.',
                raw,
            )
        except (TypeError, ValueError):
            logger.error(
                'Escudo LIMS: PRISLAB_ESCUDO_USUARIO_ID inválido (%r); usando fallback staff.',
                raw,
            )
    return User.objects.filter(is_active=True, is_staff=True).order_by('pk').first()


def notificar_panico_escudo_lims(rp, orden, validacion_dict: dict, request_user=None, disparar_telegram: bool = True):
    """
    Registra NotificacionPanico y opcionalmente Telegram (disparar_alerta_critica).

    validacion_dict: retorno de ResultadoParametro.validar_contra_rango
    (es_critico, mensaje_critico, estado, ...).
    """
    if not getattr(rp, 'es_critico', False) and not validacion_dict.get('es_critico'):
        return None

    from laboratorio.models import NotificacionPanico
    from laboratorio.services.iso15189 import ValidacionResultado, disparar_alerta_critica

    if NotificacionPanico.objects.filter(
        resultado_id=rp.pk,
        fecha_hora_notificacion__gte=timezone.now() - timedelta(hours=24),
        observaciones__contains=MARCA_ESCUDO,
    ).exists():
        return None

    user = request_user or _usuario_para_registro_automatico()
    if not user:
        logger.warning('Escudo LIMS: sin usuario staff para NotificacionPanico (rp=%s)', rp.pk)
        return None

    medico = 'Pendiente — contactar médico tratante'
    if getattr(orden, 'medico_referente_id', None):
        m = orden.medico_referente
        medico = (getattr(m, 'nombre', None) or str(m))[:255]

    msg = (validacion_dict.get('mensaje_critico') or '').strip()
    obs = f'{MARCA_ESCUDO} {msg}'.strip()[:2000]

    notif = NotificacionPanico.objects.create(
        resultado=rp,
        orden=orden,
        medico_notificado=medico[:255],
        medio_notificacion=NotificacionPanico.MEDIO_TELEFONO,
        usuario_notifico=user,
        observaciones=obs or MARCA_ESCUDO,
    )

    if disparar_telegram:
        try:
            vnum = None
            if rp.valor:
                try:
                    vnum = Decimal(str(rp.valor).replace(',', '.').split()[0].lstrip('><= '))
                except (InvalidOperation, IndexError, ValueError):
                    vnum = None
            val = ValidacionResultado(
                es_numerico=vnum is not None,
                valor_numerico=vnum,
                es_critico=True,
                es_anormal=True,
                nivel=str(validacion_dict.get('estado') or 'CRITICO'),
                mensaje=msg or MARCA_ESCUDO,
            )
            paciente_nombre = str(orden.paciente) if orden.paciente else ''
            nombre_param = rp.analito.nombre if getattr(rp, 'analito_id', None) else ''
            disparar_alerta_critica(
                resultado_id=rp.pk,
                validacion=val,
                orden_id=orden.pk,
                paciente_nombre=paciente_nombre,
                parametro_nombre=nombre_param,
            )
        except (ValidationError, IntegrityError) as exc:
            logger.error('Escudo LIMS - Error de datos en alerta crítica: %s', exc, exc_info=True)
        except OperationalError as exc:
            logger.error('Escudo LIMS - Error de base de datos en alerta crítica: %s', exc, exc_info=True)
        except ImportError as exc:
            logger.warning('Escudo LIMS - Modelo de notificación no disponible: %s', exc)
        except Exception as exc:
            logger.error('Escudo LIMS - Error inesperado en alerta crítica: %s', exc, exc_info=True)

    return notif
