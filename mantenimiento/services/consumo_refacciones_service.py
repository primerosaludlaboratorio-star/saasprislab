from decimal import Decimal

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from mantenimiento.models import SalidaRefaccionMantenimiento


LOTE_MODEL_MAP = {
    'LAB': ('inventario', 'LoteReactivoLab'),
    'CONSULTORIO': ('inventario', 'LoteInsumoConsultorio'),
    'GENERAL': ('inventario', 'LoteInsumoGeneral'),
}

LOTE_CONTENT_TYPE_MAP = {
    'LAB': 'lotereactivolab',
    'CONSULTORIO': 'loteinsumoconsultorio',
    'GENERAL': 'loteinsumogeneral',
}


class ConsumoRefaccionError(Exception):
    pass


class EstadoTicketInvalidoError(ConsumoRefaccionError):
    pass


class StockInsuficienteError(ConsumoRefaccionError):
    pass


class LoteNoEncontradoError(ConsumoRefaccionError):
    pass


class SiloNoSoportadoError(ConsumoRefaccionError):
    pass


def _get_lote_model(silo_origen):
    mapping = LOTE_MODEL_MAP.get(silo_origen)
    if not mapping:
        raise SiloNoSoportadoError(f'Silo no soportado: {silo_origen}')
    return apps.get_model(*mapping)


def _get_content_type(silo_origen):
    model_name = LOTE_CONTENT_TYPE_MAP.get(silo_origen)
    if not model_name:
        raise SiloNoSoportadoError(f'Silo no soportado: {silo_origen}')
    return ContentType.objects.get(app_label='inventario', model=model_name)


@transaction.atomic
def registrar_consumo_refaccion(*, ticket, empresa, silo_origen, lote_object_id, cantidad_usada, unidad='', registrado_por=None, observacion='', paso_reparacion=None):
    if ticket.estado in ('CERRADO', 'CANCELADO'):
        raise EstadoTicketInvalidoError('No se pueden registrar refacciones en una orden cerrada o cancelada.')

    cantidad_decimal = Decimal(str(cantidad_usada))
    if cantidad_decimal <= 0:
        raise ConsumoRefaccionError('La cantidad debe ser mayor a cero.')

    LoteModel = _get_lote_model(silo_origen)
    lote = LoteModel.objects.select_for_update().filter(pk=lote_object_id, empresa=empresa).first()
    if not lote:
        raise LoteNoEncontradoError('Lote no encontrado para la empresa actual.')

    stock_anterior = Decimal(str(lote.cantidad_actual))
    if cantidad_decimal > stock_anterior:
        raise StockInsuficienteError(f'Stock insuficiente. Disponible: {stock_anterior}.')

    costo_unitario = Decimal(str(getattr(lote, 'precio_unitario_compra', 0) or 0))
    costo_total = (cantidad_decimal * costo_unitario).quantize(Decimal('0.01'))
    stock_resultante = stock_anterior - cantidad_decimal

    lote_content_type = _get_content_type(silo_origen)

    salida = SalidaRefaccionMantenimiento.objects.create(
        empresa=empresa,
        ticket=ticket,
        silo_origen=silo_origen,
        lote_content_type=lote_content_type,
        lote_object_id=lote.pk,
        cantidad_usada=cantidad_decimal,
        unidad=unidad,
        paso_reparacion=paso_reparacion,
        registrado_por=registrado_por,
        observacion=observacion,
        costo_unitario_snapshot=costo_unitario,
        costo_total_snapshot=costo_total,
        stock_anterior_snapshot=stock_anterior,
        stock_resultante_snapshot=stock_resultante,
    )

    lote.cantidad_actual = stock_resultante
    update_fields = ['cantidad_actual']
    if hasattr(lote, 'estado') and stock_resultante <= 0:
        lote.estado = 'AGOTADO'
        update_fields.append('estado')
    lote.save(update_fields=update_fields)

    return salida
