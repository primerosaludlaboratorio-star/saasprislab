"""
Servicio de rastro forense COFEPRIS (Punto 12).
Encola Celery si hay broker real; si no, INSERT síncrono ligero.
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def _client_ip(request) -> str | None:
    if not request:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        forwarded_ips = [ip.strip() for ip in forwarded.split(',') if ip.strip()]
        if forwarded_ips:
            return forwarded_ips[-1][:45]
    addr = request.META.get('REMOTE_ADDR')
    return (addr or '')[:45] or None


def _user_agent(request) -> str:
    if not request:
        return ''
    return (request.META.get('HTTP_USER_AGENT', '') or '')[:2000]


def metadata_consentimiento_snapshot(paciente) -> dict[str, Any]:
    """
    Banderas de consentimiento al momento del acceso (sin PHI).
    acepta_privacidad se toma del ConsentimientoInformado más reciente si existe.
    """
    if paciente is None:
        return {}
    from core.models import ConsentimientoInformado

    out: dict[str, Any] = {
        'consentimiento_marketing': bool(getattr(paciente, 'consentimiento_marketing', False)),
    }
    ci = (
        ConsentimientoInformado.objects.filter(paciente_id=paciente.pk)
        .order_by('-fecha_firma')
        .only('acepta_privacidad', 'acepta_procesamiento')
        .first()
    )
    if ci:
        out['acepta_privacidad'] = bool(ci.acepta_privacidad)
        out['acepta_procesamiento'] = bool(ci.acepta_procesamiento)
    else:
        out['acepta_privacidad'] = False
        out['acepta_procesamiento'] = False
    return out


def _merge_metadata(base: dict | None, extra: dict | None) -> dict:
    m = dict(base or {})
    if extra:
        m.update(extra)
    return m


def _insert_row(
    *,
    empresa_id: int,
    accion: str,
    paciente_id: int | None,
    orden_id: int | None,
    usuario_id: int | None,
    ip_address: str | None,
    user_agent: str,
    token_prefix: str,
    es_publico: bool,
    metadata: dict,
) -> None:
    from core.models import ForenseAcceso

    ForenseAcceso.objects.create(
        empresa_id=empresa_id,
        paciente_id=paciente_id,
        orden_id=orden_id,
        usuario_id=usuario_id,
        accion=accion,
        ip_address=ip_address,
        user_agent=user_agent,
        token_prefix=(token_prefix or '')[:8],
        es_publico=es_publico,
        metadata=metadata,
    )


def registrar_acceso_forense(
    request,
    accion: str,
    *,
    paciente_id: int | None = None,
    orden_id: int | None = None,
    metadata: dict | None = None,
    es_publico: bool = False,
    empresa=None,
    token_str: str | None = None,
) -> None:
    """
    Registra acceso forense. No lanza excepciones hacia la vista.
    """
    try:
        emp = empresa
        if emp is None and request and getattr(request, 'user', None) is not None:
            if request.user.is_authenticated:
                emp = getattr(request.user, 'empresa', None)
        if emp is None:
            logger.debug('[FORENSE] Sin empresa; omitido accion=%s', accion)
            return

        uid = None
        if request and getattr(request, 'user', None) is not None and request.user.is_authenticated:
            uid = request.user.pk

        if es_publico:
            uid = None

        tp = ''
        if token_str:
            tp = str(token_str)[:8]

        meta = _merge_metadata(metadata, {})
        ip = _client_ip(request)
        ua = _user_agent(request)

        kwargs = {
            'empresa_id': emp.pk,
            'accion': accion,
            'paciente_id': paciente_id,
            'orden_id': orden_id,
            'usuario_id': uid,
            'ip_address': ip,
            'user_agent': ua,
            'token_prefix': tp,
            'es_publico': es_publico,
            'metadata': meta,
        }

        always_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', True)
        if always_eager:
            _insert_row(**kwargs)
            return

        try:
            from core.tasks import registrar_rastro_forense_task

            registrar_rastro_forense_task.delay(**kwargs)
        except Exception as exc:
            logger.warning('[FORENSE] Celery delay falló, sync: %s', exc)
            _insert_row(**kwargs)
    except Exception as exc:
        logger.warning('[FORENSE] registrar_acceso_forense omitido: %s', exc, exc_info=True)
