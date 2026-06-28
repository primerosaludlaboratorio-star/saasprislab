"""
Servicios de devolución y cancelación de ventas PDV.
"""
import json
import logging
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from django.db import transaction
from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce

from core.models import SalesReturn, Venta
from core.services.ventas.catalogo_service import _int_or_none

logger = logging.getLogger("core.farmacia")


class DevolucionService:
    """Devoluciones parciales/totales y cancelación de ventas con reversión Kardex."""

    @staticmethod
    def registrar_devolucion_resultado(request, empresa, data: dict):
        """POST devolución: SalesReturn + auditoría. Retorna {http_status, body}."""
        if not empresa:
            return {'http_status': 403, 'body': {'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}}
        venta_id = data.get('venta_id')
        if not venta_id:
            return {'http_status': 400, 'body': {'status': 'error', 'mensaje': 'venta_id requerido'}}
        try:
            monto = Decimal(str(data.get('monto_reembolsado') or data.get('monto', 0)))
        except (InvalidOperation, TypeError, ValueError):
            monto = Decimal('0')
        tipo = data.get('tipo_devolucion') or data.get('tipo', 'TOTAL')
        motivo = data.get('motivo_error') or data.get('motivo', '')
        accion_stock = (data.get('accion_stock') or 'RETORNO_ALMACEN').strip().upper()
        if accion_stock == 'REINGRESAR':
            accion_stock = 'RETORNO_ALMACEN'
        if accion_stock not in {'RETORNO_ALMACEN', 'MERMA_DESECHO'}:
            return {
                'http_status': 400,
                'body': {'status': 'error', 'mensaje': 'acción de stock no válida'},
            }
        try:
            venta = Venta.objects.prefetch_related(
                'detalles__producto',
                'detalles__lote_vendido',
                'detalles__lotes_extraidos__lote',
                'devoluciones',
            ).get(id=venta_id, empresa=empresa)
        except Venta.DoesNotExist:
            return {'http_status': 404, 'body': {'status': 'error', 'mensaje': 'Venta no encontrada'}}
        if monto <= 0:
            return {'http_status': 400, 'body': {'status': 'error', 'mensaje': 'El monto debe ser mayor a cero'}}

        def _total_devuelto_core(venta_obj):
            return venta_obj.devoluciones.aggregate(
                total=Coalesce(Sum('monto_reembolsado'), Decimal('0.00'), output_field=DecimalField())
            )['total'] or Decimal('0.00')

        def _total_devuelto_erp(venta_obj):
            return venta_obj.devoluciones_farmacia.aggregate(
                total=Coalesce(Sum('monto_devolucion'), Decimal('0.00'), output_field=DecimalField())
            )['total'] or Decimal('0.00')

        total_devuelto_previo = _total_devuelto_core(venta) + _total_devuelto_erp(venta)
        disponible_monto = (venta.total or Decimal('0.00')) - total_devuelto_previo
        if monto > disponible_monto:
            return {
                'http_status': 400,
                'body': {
                    'status': 'error',
                    'mensaje': f'Monto excede lo disponible para devolución (${disponible_monto})',
                },
            }
        productos = (
            data.get('productos')
            or data.get('productos_devueltos')
            or []
        )
        if isinstance(productos, str):
            try:
                productos = json.loads(productos)
            except (json.JSONDecodeError, TypeError):
                productos = []

        detalles_map = {d.id: d for d in venta.detalles.all()}
        if tipo == 'TOTAL' and not productos:
            productos = [
                {'detalle_id': d.id, 'cantidad': d.cantidad, 'motivo': motivo}
                for d in detalles_map.values()
            ]

        def _cantidad_ya_devuelta(venta_obj):
            acumulado = {}
            for devolucion_prev in venta_obj.devoluciones.all():
                raw_obs = devolucion_prev.observaciones or ''
                if 'productos_devueltos' not in raw_obs:
                    continue
                try:
                    idx = raw_obs.index('{')
                    blob = json.loads(raw_obs[idx:])
                except (ValueError, json.JSONDecodeError, TypeError):
                    continue
                for item in blob.get('productos_devueltos', []):
                    did = _int_or_none(item.get('detalle_id'))
                    qty = _int_or_none(item.get('cantidad')) or 0
                    if did:
                        acumulado[did] = acumulado.get(did, 0) + max(qty, 0)
            return acumulado

        devuelto_previo = _cantidad_ya_devuelta(venta)
        productos_validados = []
        for p in productos:
            detalle_id = _int_or_none(p.get('detalle_id')) or _int_or_none(p.get('id'))
            detalle = detalles_map.get(detalle_id) if detalle_id else None
            if not detalle:
                continue
            cantidad = _int_or_none(p.get('cantidad')) or 0
            if cantidad <= 0:
                return {
                    'http_status': 400,
                    'body': {'status': 'error', 'mensaje': 'La cantidad devuelta debe ser mayor a cero'},
                }
            ya_devuelta = devuelto_previo.get(detalle_id, 0)
            disponible = int(detalle.cantidad or 0) - ya_devuelta
            if cantidad > disponible:
                return {
                    'http_status': 400,
                    'body': {
                        'status': 'error',
                        'mensaje': (
                            f'La partida {detalle_id} ya no tiene cantidad disponible suficiente para devolución '
                            f'(disponible: {max(disponible, 0)}).'
                        ),
                    },
                }
            productos_validados.append({
                'detalle_id': detalle_id,
                'cantidad': cantidad,
                'motivo': p.get('motivo', '') or motivo,
            })
        if tipo == 'PARCIAL' and not productos_validados:
            return {
                'http_status': 400,
                'body': {
                    'status': 'error',
                    'mensaje': 'Debe seleccionar al menos un producto válido para devolución parcial',
                },
            }
        observaciones = data.get('observaciones', '')
        if productos_validados:
            observaciones_json = json.dumps({'productos_devueltos': productos_validados}, ensure_ascii=False)
            observaciones = f"{observaciones}\n\nDetalle de productos:\n{observaciones_json}".strip()
        try:
            from core.services.audit_service import registrar_auditoria
            from farmacia.models import MovimientoInventario
            with transaction.atomic():
                venta_bloqueada = Venta.objects.select_for_update().get(pk=venta.pk, empresa=empresa)
                total_devuelto_previo = _total_devuelto_core(venta_bloqueada) + _total_devuelto_erp(venta_bloqueada)
                disponible_monto = (venta_bloqueada.total or Decimal('0.00')) - total_devuelto_previo
                if monto > disponible_monto:
                    return {
                        'http_status': 400,
                        'body': {
                            'status': 'error',
                            'mensaje': f'Monto excede lo disponible para devolución (${disponible_monto})',
                        },
                    }

                devolucion = SalesReturn.objects.create(
                    empresa=empresa,
                    venta_original=venta_bloqueada,
                    tipo_devolucion=tipo,
                    monto_reembolsado=monto,
                    motivo_error=motivo,
                    usuario_error_origen=request.user,
                    usuario_autorizo=request.user,
                    accion_stock=accion_stock,
                    observaciones=observaciones or None,
                )

                if accion_stock == 'RETORNO_ALMACEN':
                    for item in productos_validados:
                        detalle = detalles_map.get(item['detalle_id'])
                        if not detalle or not detalle.producto:
                            continue
                        cantidad_retorno = int(item['cantidad'])
                        lotes_fuente = list(detalle.lotes_extraidos.all())
                        if not lotes_fuente and detalle.lote_vendido_id:
                            lotes_fuente = [SimpleNamespace(lote=detalle.lote_vendido, cantidad_extraida=detalle.cantidad)]

                        restante = cantidad_retorno
                        for uso in lotes_fuente:
                            lote = getattr(uso, 'lote', None)
                            extraida = int(getattr(uso, 'cantidad_extraida', 0) or 0)
                            if not lote or extraida <= 0 or restante <= 0:
                                continue
                            cantidad_lote = min(restante, extraida)
                            MovimientoInventario.objects.create(
                                empresa=empresa,
                                sucursal=getattr(request.user, 'sucursal', None),
                                producto=detalle.producto,
                                lote=lote,
                                tipo_movimiento='ENTRADA_DEVOLUCION',
                                cantidad=cantidad_lote,
                                costo_unitario=(
                                    detalle.costo_unitario_momento
                                    or getattr(lote, 'costo_adquisicion', None)
                                    or detalle.producto.precio_compra
                                    or Decimal('0')
                                ),
                                venta=venta,
                                usuario_responsable=request.user,
                                observaciones=(
                                    f'Devolución de cliente sobre venta #{venta.id} '
                                    f'(detalle #{detalle.id}, devolución #{devolucion.id})'
                                ),
                            )
                            restante -= cantidad_lote

                registrar_auditoria(
                    accion='CREATE',
                    modelo='SalesReturn',
                    objeto_id=str(devolucion.id),
                    datos_nuevos={
                        'venta_id': venta.id,
                        'folio_venta': getattr(venta, 'folio', None) or str(venta.id),
                        'tipo_devolucion': tipo,
                        'monto_reembolsado': str(monto),
                        'motivo': motivo,
                        'autorizado_por': request.user.get_full_name(),
                    },
                    request=request,
                )
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _cantidad_ya_devuelta (devolucion_service.py)")
            return {'http_status': 400, 'body': {'status': 'error', 'mensaje': str(e)}}
        return {'http_status': 200, 'body': {'status': 'success'}}

    @staticmethod
    def cancelar_venta_resultado(request, empresa, venta_id: int):
        """Cancelación + reversión Kardex. Retorna {http_status, body}."""
        if not empresa:
            return {'http_status': 403, 'body': {'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}}
        try:
            venta = Venta.objects.select_related('empresa').prefetch_related(
                'detalles__lote_vendido', 'detalles__producto'
            ).get(id=venta_id, empresa=empresa)
        except Venta.DoesNotExist:
            return {'http_status': 404, 'body': {'status': 'error', 'mensaje': 'Venta no encontrada'}}
        if venta.estado == 'CANCELADA':
            return {'http_status': 400, 'body': {'status': 'error', 'mensaje': 'La venta ya está cancelada'}}
        estado_anterior = venta.estado

        try:
            from farmacia.models import MovimientoInventario
            from core.services.audit_service import registrar_auditoria

            with transaction.atomic():
                venta_bloqueada = Venta.objects.select_for_update().get(pk=venta.pk)
                if venta_bloqueada.estado == 'CANCELADA':
                    return {'http_status': 400, 'body': {'status': 'error', 'mensaje': 'La venta ya está cancelada'}}

                venta_bloqueada.estado = 'CANCELADA'
                venta_bloqueada.save(update_fields=['estado'])

                movimientos_originales = MovimientoInventario.objects.select_for_update().filter(
                    venta=venta_bloqueada,
                    tipo_movimiento='SALIDA_VENTA',
                ).select_related('producto', 'lote')
                for mov in movimientos_originales:
                    if not mov.lote or not mov.producto or not mov.cantidad:
                        continue
                    MovimientoInventario.objects.create(
                        empresa=empresa,
                        sucursal=getattr(request.user, 'sucursal', None),
                        producto=mov.producto,
                        lote=mov.lote,
                        tipo_movimiento='ENTRADA_DEVOLUCION',
                        cantidad=mov.cantidad,
                        costo_unitario=mov.costo_unitario or 0,
                        venta=venta,
                        usuario_responsable=request.user,
                        observaciones=f'Reversión automática por cancelación de venta #{venta_id}',
                    )

            try:
                registrar_auditoria(
                    accion='UPDATE',
                    modelo='Venta',
                    objeto_id=str(venta.id),
                    datos_anteriores={'estado': estado_anterior},
                    datos_nuevos={'estado': 'CANCELADA', 'cancelado_por': request.user.get_full_name()},
                    request=request,
                )
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en cancelar_venta_resultado (devolucion_service.py)")
                pass

            return {
                'http_status': 200,
                'body': {
                    'status': 'success',
                    'mensaje': f'Venta #{venta_id} cancelada y stock revertido correctamente',
                    'folio': getattr(venta, 'folio_operacion', str(venta_id)),
                },
            }
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en cancelar_venta_resultado (devolucion_service.py)")
            return {'http_status': 400, 'body': {'status': 'error', 'mensaje': str(e)}}