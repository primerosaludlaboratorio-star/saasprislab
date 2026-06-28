"""
Hito 16 Fase 2 — Generación automática de borradores FacturaCFDI tras cobro (lab / farmacia).
No invoca Facturama; solo persiste borrador listo para timbrar.
"""
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import IntegrityError, OperationalError
from contabilidad.models import ClienteFacturacion, ConceptoFactura, FacturaCFDI, ImpuestoConcepto

logger = logging.getLogger(__name__)

RFC_PUBLICO_GENERAL = 'XAXX010101000'
TASA_IVA = Decimal('0.16')
EMAIL_GENERICO_FACTURACION = getattr(
    settings,
    'PRISLAB_CFDI_EMAIL_GENERICO',
    'facturacion.generica@prislab.invalid',
)
CP_GENERICO = getattr(settings, 'PRISLAB_CFDI_CP_GENERICO', '01000')


def _split_iva_incluido_16(bruto: Decimal) -> tuple[Decimal, Decimal]:
    """Total con IVA incluido → (base, IVA) con ajuste a 2 decimales."""
    bruto = bruto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if bruto <= 0:
        return Decimal('0.00'), Decimal('0.00')
    base = (bruto / (Decimal('1') + TASA_IVA)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    iva = (bruto - base).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return base, iva


def _forma_pago_desde_montos(efectivo: Decimal, tarjeta: Decimal, transferencia: Decimal) -> str:
    """Código SAT simplificado (predominante)."""
    e, t, tr = efectivo or Decimal('0'), tarjeta or Decimal('0'), transferencia or Decimal('0')
    if tr >= e and tr >= t and tr > 0:
        return '03'
    if t >= e and t > 0:
        return '04'
    return '01'


def obtener_o_crear_cliente_publico_en_general(empresa) -> ClienteFacturacion:
    cliente, _ = ClienteFacturacion.objects.get_or_create(
        empresa=empresa,
        rfc=RFC_PUBLICO_GENERAL,
        defaults={
            'razon_social': 'PUBLICO EN GENERAL',
            'email': EMAIL_GENERICO_FACTURACION,
            'codigo_postal': CP_GENERICO,
            'regimen_fiscal': '616',
            'uso_cfdi_default': 'S01',
            'paciente': None,
            'activo': True,
        },
    )
    return cliente


def resolver_cliente_facturacion(empresa, paciente=None) -> ClienteFacturacion:
    if paciente is not None:
        c = (
            ClienteFacturacion.objects.filter(empresa=empresa, paciente=paciente, activo=True)
            .order_by('-fecha_creacion')
            .first()
        )
        if c:
            return c
    return obtener_o_crear_cliente_publico_en_general(empresa)


def _lineas_desde_orden_lab(orden, monto_cobrado: Decimal) -> list[tuple[str, Decimal, Decimal]]:
    """
    Lista (descripción, base, iva) por línea. Si no hay detalles o total orden es 0,
    una sola línea agregada con IVA 16%% incluido en monto_cobrado.
    """
    monto_cobrado = monto_cobrado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if monto_cobrado <= 0:
        return []

    detalles = list(orden.detalles.all())
    total_orden = orden.total or Decimal('0')
    if not detalles or total_orden <= 0:
        b, i = _split_iva_incluido_16(monto_cobrado)
        folio = orden.folio_orden or str(orden.pk)
        return [(f'Servicios de laboratorio (orden {folio})', b, i)]

    factor = (monto_cobrado / total_orden).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    lineas: list[tuple[str, Decimal, Decimal]] = []
    sum_bruto = Decimal('0')
    for d in detalles:
        bruto_linea = (d.precio_momento * factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        sum_bruto += bruto_linea
        label = (d.descripcion_linea or str(d))[:280]
        b, i = _split_iva_incluido_16(bruto_linea)
        lineas.append((label, b, i))

    diff = (monto_cobrado - sum_bruto).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if diff != 0 and lineas:
        desc0, b0, i0 = lineas[0]
        bruto0 = b0 + i0 + diff
        nb, ni = _split_iva_incluido_16(bruto0)
        lineas[0] = (desc0, nb, ni)
    return lineas


def _persistir_factura_borrador(
    *,
    empresa,
    usuario,
    cliente: ClienteFacturacion,
    forma_pago: str,
    lineas: list[tuple[str, Decimal, Decimal]],
    orden_lab=None,
    pago_orden=None,
    venta_farmacia=None,
) -> FacturaCFDI | None:
    if not lineas:
        return None

    subtotal = sum((t[1] for t in lineas), Decimal('0')).quantize(Decimal('0.01'))
    total_iva = sum((t[2] for t in lineas), Decimal('0')).quantize(Decimal('0.01'))
    total = (subtotal + total_iva).quantize(Decimal('0.01'))

    factura = FacturaCFDI(
        cliente=cliente,
        serie='A',
        tipo_comprobante='I',
        forma_pago=forma_pago,
        metodo_pago='PUE',
        subtotal=subtotal,
        total_impuestos_trasladados=total_iva,
        total=total,
        estado='BORRADOR',
        usuario_creo=usuario,
        orden_laboratorio=orden_lab,
        pago_orden=pago_orden,
        venta_farmacia=venta_farmacia,
    )
    factura.save()

    for idx, (descripcion, base, iva_amt) in enumerate(lineas, start=1):
        concepto = ConceptoFactura.objects.create(
            factura=factura,
            numero_linea=idx,
            descripcion=descripcion,
            cantidad=Decimal('1'),
            valor_unitario=base,
            importe=base,
            objeto_impuesto='02',
        )
        if base <= 0:
            continue
        if iva_amt <= 0:
            ImpuestoConcepto.objects.create(
                concepto=concepto,
                tipo='TRASLADO',
                impuesto='002',
                tasa_o_cuota=Decimal('0'),
                tipo_factor='Tasa',
                base=base,
                importe=Decimal('0'),
            )
            continue
        tasa = (iva_amt / base).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
        ImpuestoConcepto.objects.create(
            concepto=concepto,
            tipo='TRASLADO',
            impuesto='002',
            tasa_o_cuota=tasa,
            tipo_factor='Tasa',
            base=base,
            importe=iva_amt,
        )

    return factura


def crear_borrador_cfdi_desde_pago_orden(pago, usuario):
    """
    Crea FacturaCFDI BORRADOR vinculada a PagoOrden (monto = cobro del evento).
    Idempotente: si ya existe factura para ese pago, no duplica.
    """
    from core.models import PagoOrden

    if not isinstance(pago, PagoOrden):
        return None
    if pago.cancelado:
        return None
    monto = pago.monto_bruto
    if monto <= 0:
        return None
    if FacturaCFDI.objects.filter(pago_orden=pago).exists():
        return FacturaCFDI.objects.filter(pago_orden=pago).first()

    orden = pago.orden
    empresa = orden.empresa
    cliente = resolver_cliente_facturacion(empresa, orden.paciente)
    forma = _forma_pago_desde_montos(
        pago.monto_efectivo,
        pago.monto_tarjeta,
        pago.monto_transferencia,
    )
    lineas = _lineas_desde_orden_lab(orden, monto)
    sum_calc = sum(b + i for _, b, i in lineas)
    diff = (monto - sum_calc).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if diff != 0 and lineas:
        d0, b0, i0 = lineas[0]
        bruto0 = b0 + i0 + diff
        nb, ni = _split_iva_incluido_16(bruto0)
        lineas[0] = (d0, nb, ni)
    try:
        return _persistir_factura_borrador(
            empresa=empresa,
            usuario=usuario,
            cliente=cliente,
            forma_pago=forma,
            lineas=lineas,
            orden_lab=orden,
            pago_orden=pago,
            venta_farmacia=None,
        )
    except (IntegrityError, ValueError, OperationalError):
        logger.exception('cfdi_borrador_auto: fallo al crear borrador desde PagoOrden id=%s', pago.pk)
        raise


def crear_borrador_cfdi_desde_venta_farmacia(venta, usuario):
    """Una línea por DetalleVenta; IVA 0%% o tasa efectiva por partida."""
    from core.models import DetalleVenta, Venta

    if not isinstance(venta, Venta):
        return None
    if venta.total is None or venta.total <= 0:
        return None
    if getattr(venta, 'es_cortesia', False):
        return None
    if FacturaCFDI.objects.filter(venta_farmacia=venta).exists():
        return FacturaCFDI.objects.filter(venta_farmacia=venta).first()

    empresa = venta.empresa
    paciente = venta.paciente
    cliente = resolver_cliente_facturacion(empresa, paciente)

    from core.models import Pago as PagoModel

    pago_row = PagoModel.objects.filter(venta=venta).first()
    if pago_row:
        forma = _forma_pago_desde_montos(
            pago_row.monto_efectivo,
            pago_row.monto_tarjeta,
            pago_row.monto_transferencia,
        )
    else:
        forma = '01'

    lineas: list[tuple[str, Decimal, Decimal]] = []
    for d in DetalleVenta.objects.filter(venta=venta).select_related('producto'):
        nombre = (d.producto.nombre if d.producto_id else 'Producto')[:280]
        desc = f'{nombre} x{d.cantidad}'
        base = d.subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        iva_amt = d.iva_aplicado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        lineas.append((desc, base, iva_amt))

    if not lineas:
        b, i = _split_iva_incluido_16(venta.total)
        folio = venta.folio_operacion or str(venta.pk)
        lineas = [(f'Venta farmacia {folio}', b, i)]
    else:
        sum_b = sum(x[1] for x in lineas)
        sum_i = sum(x[2] for x in lineas)
        vb = venta.subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        vi = venta.impuestos_iva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if abs(sum_b - vb) > Decimal('0.02') or abs(sum_i - vi) > Decimal('0.02'):
            folio = venta.folio_operacion or str(venta.pk)
            lineas = [(f'Venta farmacia consolidada {folio}', vb, vi)]

    sum_net = sum(t[1] for t in lineas)
    sum_iva = sum(t[2] for t in lineas)
    gap = (venta.total - sum_net - sum_iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if gap != 0:
        lineas.append(('Ajuste redondeo / otros cargos PDV', gap, Decimal('0.00')))

    try:
        return _persistir_factura_borrador(
            empresa=empresa,
            usuario=usuario,
            cliente=cliente,
            forma_pago=forma,
            lineas=lineas,
            orden_lab=None,
            pago_orden=None,
            venta_farmacia=venta,
        )
    except (IntegrityError, ValueError, OperationalError):
        logger.exception('cfdi_borrador_auto: fallo al crear borrador desde Venta id=%s', venta.pk)
        raise
