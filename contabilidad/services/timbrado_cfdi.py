"""
Lógica de timbrado CFDI con lock pesimista e idempotencia determinista (Punto 16).
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from django.contrib import messages
from django.db import IntegrityError, OperationalError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from contabilidad.facturama_api import FacturamaAPI
from contabilidad.models import FacturaCFDI

logger = logging.getLogger('contabilidad.timbrado')


def _empresa_fiscal(request):
    # FIX V8.2 SAT TENANT (alineado con contabilidad.views)
    return getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)


def _lock_fuentes_operacion_timbrado(factura: FacturaCFDI, empresa) -> None:
    """
    # FIX DOBLE TIMBRADO: bloquea orden/venta/pago ligados antes del PAC (misma transacción).
    Evita carreras con otro flujo que facture el mismo origen.
    """
    from core.models import OrdenDeServicio
    from core.models.ventas import PagoOrden, Venta

    eid = empresa.pk
    if factura.orden_laboratorio_id:
        if not OrdenDeServicio.objects.select_for_update(nowait=True).filter(
            pk=factura.orden_laboratorio_id, empresa_id=eid
        ).exists():
            raise ValueError(
                'La orden de laboratorio vinculada no pertenece a su empresa o no existe.'
            )
    if factura.venta_farmacia_id:
        if not Venta.objects.select_for_update(nowait=True).filter(
            pk=factura.venta_farmacia_id, empresa_id=eid
        ).exists():
            raise ValueError('La venta vinculada no pertenece a su empresa o no existe.')
    if factura.pago_orden_id:
        if not PagoOrden.objects.select_for_update(nowait=True).filter(
            pk=factura.pago_orden_id, orden__empresa_id=eid
        ).exists():
            raise ValueError('El pago de orden vinculado no pertenece a su empresa o no existe.')

_facturama_factory: Callable[[], Any] | None = None

_PAC_MSG_MAX_LEN = 4000


def set_facturama_factory_for_tests(factory: Callable[[], Any] | None) -> None:
    global _facturama_factory
    _facturama_factory = factory


def _api() -> FacturamaAPI:
    if _facturama_factory is not None:
        return _facturama_factory()
    return FacturamaAPI()


def _wants_json(request) -> bool:
    accept = request.META.get('HTTP_ACCEPT') or ''
    return 'application/json' in accept or request.GET.get('fmt') == 'json'


def _truncate_pac_message(text: str) -> str:
    t = (text or '').strip()
    if len(t) > _PAC_MSG_MAX_LEN:
        return t[:_PAC_MSG_MAX_LEN] + '…'
    return t


def _safe_next_redirect(request, factura_id: int):
    next_url = (request.POST.get('next') or request.GET.get('next') or '').strip()
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect('contabilidad:detalle_factura', factura_id=factura_id)


def _conflict_response(request, msg: str, factura_id: int):
    if _wants_json(request):
        return JsonResponse(
            {'ok': False, 'code': 'CONFLICT', 'mensaje': msg, 'factura_id': factura_id},
            status=409,
        )
    messages.warning(request, msg)
    return _safe_next_redirect(request, factura_id)


def ejecutar_timbrado(request, factura_id: int):
    """
    Timbrado con transaction.atomic + select_for_update(nowait=True).
    No propaga excepciones: respuesta HTML (redirect + messages) o JSON (200/403/404/409).
    """
    empresa = _empresa_fiscal(request)
    if not empresa:
        msg = 'Usuario sin empresa asignada.'
        if _wants_json(request):
            return JsonResponse({'ok': False, 'code': 'NO_EMPRESA', 'mensaje': msg}, status=403)
        messages.error(request, msg)
        return redirect('contabilidad:lista_facturas')

    wants_json = _wants_json(request)

    try:
        with transaction.atomic():
            try:
                factura = (
                    FacturaCFDI.objects.select_for_update(nowait=True)
                    .select_related('cliente', 'usuario_creo')
                    .get(id=factura_id, empresa=empresa)
                )
            except FacturaCFDI.DoesNotExist:
                if wants_json:
                    return JsonResponse(
                        {'ok': False, 'code': 'NOT_FOUND', 'mensaje': 'Factura no encontrada.'},
                        status=404,
                    )
                messages.error(request, 'Factura no encontrada o no pertenece a su empresa.')
                return redirect('contabilidad:lista_facturas')
            except OperationalError:
                logger.warning(
                    'Timbrado concurrente: lock nowait rechazado factura_id=%s empresa=%s',
                    factura_id,
                    empresa.id,
                )
                return _conflict_response(
                    request,
                    'Otro proceso está timbrando esta factura. Espere o reintente tras unos segundos.',
                    factura_id,
                )

            if factura.estado == 'TIMBRADO':
                msg = 'La factura ya se encontraba timbrada.'
                if wants_json:
                    return JsonResponse(
                        {
                            'ok': True,
                            'code': 'ALREADY_STAMPED',
                            'mensaje': msg,
                            'factura_id': factura.id,
                        },
                        status=200,
                    )
                messages.info(request, msg)
                return _safe_next_redirect(request, factura.id)

            if factura.estado == 'FACTURANDO':
                return _conflict_response(
                    request,
                    'Factura en estado FACTURANDO. Si lleva varios minutos, ejecute reconciliar_facturas_pendientes.',
                    factura_id,
                )

            if factura.estado not in ('BORRADOR', 'PENDIENTE', 'ERROR'):
                msg = f'No se puede timbrar en estado {factura.estado}.'
                if wants_json:
                    return JsonResponse(
                        {'ok': False, 'code': 'INVALID_STATE', 'mensaje': msg, 'factura_id': factura.id},
                        status=400,
                    )
                messages.error(request, msg)
                return _safe_next_redirect(request, factura.id)

            try:
                _lock_fuentes_operacion_timbrado(factura, empresa)
            except ValueError as verr:
                if wants_json:
                    return JsonResponse(
                        {
                            'ok': False,
                            'code': 'ORIGEN_INVALIDO',
                            'mensaje': str(verr),
                            'factura_id': factura.id,
                        },
                        status=400,
                    )
                messages.error(request, str(verr))
                return _safe_next_redirect(request, factura.id)

            factura.estado = 'FACTURANDO'
            factura.timbrado_intento_en = timezone.now()
            factura.timbrando_en_proceso = True
            factura.save(update_fields=['estado', 'timbrado_intento_en', 'timbrando_en_proceso'])

            resultado = _api().timbrar_cfdi(factura)

            if resultado.get('success'):
                factura.uuid_sat = resultado.get('uuid')
                factura.xml_timbrado = resultado.get('xml') or ''
                factura.fecha_timbrado = resultado.get('fecha_timbrado')
                factura.estado = 'TIMBRADO'
                factura.timbrando_en_proceso = False
                factura.timbrado_intento_en = None
                factura.ultimo_error_pac = ''
                factura.save()
                msg_ok = f'Factura timbrada exitosamente. UUID: {resultado.get("uuid")}'
                if wants_json:
                    return JsonResponse(
                        {
                            'ok': True,
                            'code': 'STAMPED',
                            'mensaje': msg_ok,
                            'factura_id': factura.id,
                            'uuid': resultado.get('uuid'),
                        },
                        status=200,
                    )
                messages.success(request, f'✓ {msg_ok}')
                return _safe_next_redirect(request, factura.id)

            if resultado.get('timeout'):
                logger.warning(
                    'Facturama timeout factura_id=%s — permanece FACTURANDO para reconciliación',
                    factura_id,
                )
                msg_w = (
                    'El PAC no respondió a tiempo. La factura quedó en FACTURANDO; '
                    'si no se actualiza, ejecute reconciliar_facturas_pendientes.'
                )
                if wants_json:
                    return JsonResponse(
                        {
                            'ok': False,
                            'code': 'PAC_TIMEOUT',
                            'mensaje': msg_w,
                            'factura_id': factura.id,
                        },
                        status=200,
                    )
                messages.warning(request, msg_w)
                return _safe_next_redirect(request, factura.id)

            err_txt = _truncate_pac_message(
                str(resultado.get('error') or 'Error desconocido del PAC')
            )
            factura.estado = 'ERROR'
            factura.timbrando_en_proceso = False
            factura.timbrado_intento_en = None
            factura.ultimo_error_pac = err_txt
            factura.save(
                update_fields=[
                    'estado',
                    'timbrando_en_proceso',
                    'timbrado_intento_en',
                    'ultimo_error_pac',
                ]
            )
            msg_err = f'Error al timbrar: {err_txt}'
            if wants_json:
                return JsonResponse(
                    {
                        'ok': False,
                        'code': 'PAC_ERROR',
                        'mensaje': msg_err,
                        'factura_id': factura.id,
                        'detalle_pac': err_txt,
                    },
                    status=200,
                )
            messages.error(request, f'✗ {msg_err}')
            return _safe_next_redirect(request, factura.id)

    except (OperationalError, ValueError, IntegrityError, ConnectionError, TimeoutError) as exc:
        logger.exception('Error al timbrar factura %s', factura_id)
        friendly = str(exc).strip() if str(exc).strip() else (
            'No se pudo completar el timbrado. Si el problema persiste, contacte a soporte.'
        )
        if len(friendly) > 500:
            friendly = friendly[:500] + '…'
        try:
            with transaction.atomic():
                f_rec = (
                    FacturaCFDI.objects.select_for_update(nowait=True)
                    .filter(id=factura_id, empresa=empresa)
                    .first()
                )
                if f_rec and f_rec.estado == 'FACTURANDO':
                    f_rec.estado = 'ERROR'
                    f_rec.timbrando_en_proceso = False
                    f_rec.timbrado_intento_en = None
                    f_rec.ultimo_error_pac = _truncate_pac_message(str(exc))
                    f_rec.save(
                        update_fields=[
                            'estado',
                            'timbrando_en_proceso',
                            'timbrado_intento_en',
                            'ultimo_error_pac',
                        ]
                    )
        except (OperationalError, ValueError, IntegrityError):
            logger.exception('No se pudo recuperar factura tras error de timbrado %s', factura_id)

        if wants_json:
            return JsonResponse(
                {
                    'ok': False,
                    'code': 'INTERNAL',
                    'mensaje': friendly,
                    'factura_id': factura_id,
                },
                status=200,
            )
        messages.error(request, f'✗ {friendly}')
        return _safe_next_redirect(request, factura_id)
