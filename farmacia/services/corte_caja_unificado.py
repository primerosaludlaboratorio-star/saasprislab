"""
farmacia/services/corte_caja_unificado.py
════════════════════════════════════════════════════════════════════════════════
FASE 8 — Corte de Caja Unificado (Laboratorio + Farmacia)

Cierra sincronizadamente el turno de Farmacia Y Laboratorio,
generando un resumen financiero consolidado.

Flujo:
  cerrar_turno_unificado(cajero, empresa, sucursal)
    ├── Cerrar CierreTurnoFarmacia
    ├── Cerrar turno Laboratorio (ordenes del turno)
    ├── Generar corte_consolidado
    ├── Disparar signal post_corte_caja para conciliación contable futura
    └── Imprimir ticket ESC/POS (opcional)

Candado Migraciones: Los campos nuevos están comentados.
════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations
import logging
from decimal import Decimal
from datetime import datetime, timedelta

from django.db import transaction, DatabaseError
from django.utils import timezone
from django.dispatch import Signal

logger = logging.getLogger('farmacia.corte_caja_unificado')

# ── Signal para conciliación contable futura (FASE contabilidad) ──────────────
post_corte_caja_unificado = Signal()
# Recibe: sender, corte_data, cajero, empresa


def _money(value) -> str:
    """Serializa importes con escala monetaria estable para API, UI y auditoría."""
    return f"{Decimal(value or 0):.2f}"


def _es_administrador_caja(usuario):
    if not usuario:
        return False
    rol = (getattr(usuario, 'rol', '') or '').upper().strip()
    return usuario.is_superuser or rol in {
        'ADMIN', 'ADMINISTRADOR', 'GERENTE', 'DIRECTOR', 'FARMACIA'
    }


def calcular_precorte_unificado(cajero, empresa, sucursal=None) -> dict:
    """Calcula un resumen de solo lectura del turno actualmente abierto.

    Este flujo no crea cierres, no desactiva aperturas y no bloquea registros.
    Su objetivo es permitir que un responsable revise el estado antes del
    arqueo y del cierre definitivo.
    """
    if empresa is None:
        raise ValueError('empresa es obligatoria para precorte de caja.')

    ahora = timezone.now()
    farmacia = _precorte_farmacia(cajero, empresa, sucursal)
    laboratorio = _cerrar_laboratorio(cajero, empresa, sucursal, ahora)
    if laboratorio.get('estado') == 'error':
        raise RuntimeError('No fue posible calcular el precorte de laboratorio.')

    total_farmacia = farmacia['total']
    total_lab = laboratorio.get('total', Decimal('0'))
    total_consolidado = total_farmacia + total_lab
    gastos = farmacia['gastos']
    fondo = farmacia['fondo_inicial']
    efectivo_esperado = (
        fondo
        + farmacia['efectivo']
        + laboratorio.get('efectivo', Decimal('0'))
        - farmacia.get('gastos', Decimal('0'))
        - farmacia.get('egresos_kardex', Decimal('0'))
        - farmacia.get('retiros', Decimal('0'))
    )

    return {
        'fecha': ahora.isoformat(),
        'cajero': cajero.username if cajero else 'SISTEMA',
        'empresa': str(empresa),
        'sucursal': str(sucursal) if sucursal else 'General',
        'estado': 'PRECORTE',
        'solo_lectura': True,
        'apertura': {
            'activa': farmacia['apertura_activa'],
            'id': farmacia.get('apertura_id'),
            'folio': farmacia.get('folio_apertura'),
            'fecha_apertura': farmacia.get('fecha_apertura'),
            'fondo_inicial': _money(fondo),
            'responsable_apertura': farmacia.get('responsable_apertura'),
        },
        'farmacia': {
            'total': _money(total_farmacia),
            'ventas': farmacia['ventas'],
            'efectivo': _money(farmacia['efectivo']),
            'tarjeta': _money(farmacia.get('tarjeta', Decimal('0'))),
            'transferencia': _money(farmacia.get('transferencia', Decimal('0'))),
            'vales': _money(farmacia.get('vales', Decimal('0'))),
            'digital': _money(farmacia['digital']),
            'gastos': _money(gastos),
            'egresos_kardex': _money(farmacia.get('egresos_kardex', Decimal('0'))),
            'retiros': _money(farmacia.get('retiros', Decimal('0'))),
            'ajustes': _money(farmacia.get('ajustes', Decimal('0'))),
            'movimientos': farmacia.get('movimientos', []),
        },
        'laboratorio': {
            'total': _money(total_lab),
            'ordenes': laboratorio.get('ordenes', 0),
            'efectivo': _money(laboratorio.get('efectivo', Decimal('0'))),
            'digital': _money(laboratorio.get('digital', Decimal('0'))),
        },
        'total_consolidado': _money(total_consolidado),
        'efectivo_esperado': _money(efectivo_esperado),
    }


def _precorte_farmacia(cajero, empresa, sucursal) -> dict:
    """Lee apertura, ventas, pagos y gastos sin mutar el estado de caja."""
    from django.db.models import Sum
    from farmacia.models import AperturaCaja
    from core.models import GastoCaja, MovimientoCaja, Pago, Venta

    query = AperturaCaja.objects.filter(empresa=empresa, activa=True)
    if sucursal:
        query = query.filter(sucursal=sucursal)
    apertura = query.order_by('-fecha_apertura').first()
    if not apertura:
        return {
            'apertura_activa': False,
            'total': Decimal('0'),
            'ventas': 0,
            'efectivo': Decimal('0'),
            'digital': Decimal('0'),
            'gastos': Decimal('0'),
            'fondo_inicial': Decimal('0'),
            'movimientos': [],
        }

    ventas = Venta.objects.filter(
        empresa=empresa,
        fecha__gte=apertura.fecha_apertura,
    ).exclude(estado='CANCELADA')
    if sucursal:
        ventas = ventas.filter(sucursal=sucursal)

    total = ventas.aggregate(total=Sum('total'))['total'] or Decimal('0')
    pagos_qs = Pago.objects.filter(venta__in=ventas)
    pagos = pagos_qs.aggregate(
        efectivo=Sum('monto_efectivo'),
        tarjeta=Sum('monto_tarjeta'),
        transferencia=Sum('monto_transferencia'),
        vales=Sum('monto_vales'),
    )
    efectivo = pagos['efectivo'] or Decimal('0')
    tarjeta = pagos['tarjeta'] or Decimal('0')
    transferencia = pagos['transferencia'] or Decimal('0')
    vales = pagos['vales'] or Decimal('0')
    digital = tarjeta + transferencia
    # Compatibilidad segura con ventas históricas que no tienen desglose de pago:
    # se conservan como efectivo y quedan disponibles para conciliación posterior.
    if not pagos_qs.exists() and total:
        efectivo = total
    gastos = GastoCaja.objects.filter(
        empresa=empresa,
        fecha__gte=apertura.fecha_apertura,
        sucursal=apertura.sucursal,
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
    movimientos_qs = MovimientoCaja.objects.filter(
        empresa=empresa,
        fecha_movimiento__gte=apertura.fecha_apertura,
    ).exclude(concepto='APERTURA_CAJA')
    if sucursal:
        movimientos_qs = movimientos_qs.filter(sucursal=sucursal)
    egresos_kardex = movimientos_qs.filter(
        tipo_movimiento='EGRESO',
    ).exclude(concepto='GASTO_MENOR').aggregate(total=Sum('monto'))['total'] or Decimal('0')
    retiros = movimientos_qs.filter(
        tipo_movimiento='TRANSFERENCIA',
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
    ajustes = movimientos_qs.filter(
        tipo_movimiento='AJUSTE',
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
    movimientos = [
        {
            'fecha': movimiento.fecha_movimiento.isoformat(),
            'tipo': movimiento.get_tipo_movimiento_display(),
            'concepto': movimiento.get_concepto_display(),
            'monto': str(movimiento.monto),
            'usuario': getattr(movimiento.usuario_responsable, 'username', '') or 'Sistema',
            'referencia': movimiento.referencia or '',
        }
        for movimiento in movimientos_qs.select_related('usuario_responsable').order_by('-fecha_movimiento')[:200]
    ]

    return {
        'apertura_activa': True,
        'apertura_id': apertura.pk,
        'folio_apertura': apertura.folio,
        'fecha_apertura': apertura.fecha_apertura.isoformat(),
        'total': total,
        'ventas': ventas.count(),
        'efectivo': efectivo,
        'tarjeta': tarjeta,
        'transferencia': transferencia,
        'vales': vales,
        'digital': digital,
        'gastos': gastos,
        'egresos_kardex': egresos_kardex,
        'retiros': retiros,
        'ajustes': ajustes,
        'movimientos': movimientos,
        'fondo_inicial': apertura.fondo_efectivo,
        'responsable_apertura': apertura.usuario_responsable.username,
    }


def cerrar_turno_unificado(
    cajero,
    empresa,
    sucursal=None,
    efectivo_declarado: Decimal = Decimal('0'),
    tarjeta_declarado: Decimal = Decimal('0'),
    transferencia_declarado: Decimal = Decimal('0'),
    vales_declarado: Decimal = Decimal('0'),
    imprimir_ticket: bool = True,
    host_impresora: str = '',
) -> dict:
    """
    Cierra el turno de Farmacia y Laboratorio en una sola transacción atómica.

    Args:
        cajero:              Usuario que realiza el cierre
        empresa:             Empresa (tenant)
        sucursal:            Sucursal específica (None = todas)
        efectivo_declarado:  Efectivo contado físicamente en caja
        imprimir_ticket:     Si True, imprime el corte por ESC/POS
        host_impresora:      IP de la impresora térmica

    Returns:
        dict con resumen del corte (totales, diferencias, estado)
    """
    if empresa is None:
        raise ValueError('empresa es obligatoria para corte de caja (aislamiento multi-tenant).')

    ahora = timezone.now()

    with transaction.atomic():
        # ── 1. Corte Farmacia ─────────────────────────────────────────────────
        corte_farmacia = _cerrar_farmacia(
            cajero,
            empresa,
            sucursal,
            ahora,
            efectivo_declarado,
            tarjeta_declarado,
            transferencia_declarado,
            vales_declarado,
        )
        if corte_farmacia.get('estado') == 'sin_apertura':
            return {
                'fecha': ahora.isoformat(),
                'cajero': cajero.username if cajero else 'SISTEMA',
                'empresa': str(empresa),
                'sucursal': str(sucursal) if sucursal else 'General',
                'estado': 'SIN_APERTURA',
                'farmacia': corte_farmacia,
                'laboratorio': {'total': Decimal('0'), 'ordenes': 0, 'estado': 'no_aplica'},
                'total_consolidado': _money(Decimal('0')),
                'efectivo_esperado': _money(Decimal('0')),
                'efectivo_declarado': _money(efectivo_declarado),
                'tarjeta_declarado': _money(tarjeta_declarado),
                'transferencia_declarado': _money(transferencia_declarado),
                'vales_declarado': _money(vales_declarado),
                'diferencia': _money(Decimal('0')),
                'ticket_impreso': False,
            }
        if corte_farmacia.get('estado') == 'error':
            raise RuntimeError('No fue posible completar el corte unificado.')

        # ── 2. Corte Laboratorio ──────────────────────────────────────────────
        corte_lab = _cerrar_laboratorio(cajero, empresa, sucursal, ahora)
        if corte_lab.get('estado') == 'error':
            raise RuntimeError('No fue posible completar el corte unificado.')

        # ── 3. Consolidado ────────────────────────────────────────────────────
        total_farmacia = corte_farmacia.get('total', Decimal('0'))
        total_lab = corte_lab.get('total', Decimal('0'))
        total_consolidado = total_farmacia + total_lab
        fondo_inicial = corte_farmacia.get('fondo_inicial', Decimal('0'))
        gastos_farmacia = corte_farmacia.get('gastos', Decimal('0'))
        efectivo_esperado = (
            fondo_inicial
            + corte_farmacia.get('efectivo', Decimal('0'))
            + corte_lab.get('efectivo', Decimal('0'))
            - gastos_farmacia
            - corte_farmacia.get('egresos_kardex', Decimal('0'))
            - corte_farmacia.get('retiros', Decimal('0'))
        )

        teorico_tarjeta = corte_farmacia.get('tarjeta', Decimal('0')) + corte_lab.get('tarjeta', Decimal('0'))
        teorico_transferencia = corte_farmacia.get('transferencia', Decimal('0')) + corte_lab.get('transferencia', Decimal('0'))
        teorico_vales = corte_farmacia.get('vales', Decimal('0')) + corte_lab.get('vales', Decimal('0'))
        diferencia_efectivo = efectivo_declarado - efectivo_esperado
        diferencia_tarjeta = tarjeta_declarado - teorico_tarjeta
        diferencia_transferencia = transferencia_declarado - teorico_transferencia
        diferencia_vales = vales_declarado - teorico_vales
        diferencia = diferencia_efectivo + diferencia_tarjeta + diferencia_transferencia + diferencia_vales

        corte_data = {
            'fecha': ahora.isoformat(),
            'cajero': cajero.username if cajero else 'SISTEMA',
            'empresa': str(empresa),
            'sucursal': str(sucursal) if sucursal else 'General',
            'farmacia': corte_farmacia,
            'laboratorio': corte_lab,
            'total_consolidado': _money(total_consolidado),
            'fondo_inicial': _money(fondo_inicial),
            'efectivo_esperado': _money(efectivo_esperado),
            'efectivo_declarado': _money(efectivo_declarado),
            'tarjeta_declarado': _money(tarjeta_declarado),
            'transferencia_declarado': _money(transferencia_declarado),
            'vales_declarado': _money(vales_declarado),
            'diferencia_efectivo': _money(diferencia_efectivo),
            'diferencia_tarjeta': _money(diferencia_tarjeta),
            'diferencia_transferencia': _money(diferencia_transferencia),
            'diferencia_vales': _money(diferencia_vales),
            'diferencia': _money(diferencia),
            'estado': 'CUADRADO' if abs(diferencia) < Decimal('1') else 'DESCUADRADO',
        }

        logger.info(
            f'[CorteUnificado] {cajero} | Total: ${total_consolidado} | '
            f'Diferencia: ${diferencia} | Estado: {corte_data["estado"]}'
        )

    # ── 4. Disparar signal contable (post-transacción) ────────────────────────
    try:
        post_corte_caja_unificado.send(
            sender=None,
            corte_data=corte_data,
            cajero=cajero,
            empresa=empresa,
        )
    except Exception as exc:
        # Justificación: Auditoría secundaria no bloqueante (Signal contable).
        logger.warning(f'[CorteUnificado] Signal contable no enviado: {exc}')

    # ── 5. Imprimir ticket ────────────────────────────────────────────────────
    if imprimir_ticket and host_impresora:
        try:
            _imprimir_corte(corte_data, host_impresora)
        except Exception as exc:
            # Justificación: Integración externa no confiable (Impresión térmica en red local).
            logger.warning(f'[CorteUnificado] Error imprimiendo ticket: {exc}')
            corte_data['ticket_impreso'] = False
    else:
        corte_data['ticket_impreso'] = False

    return corte_data


def _cerrar_farmacia(
    cajero,
    empresa,
    sucursal,
    ahora: datetime,
    efectivo_declarado: Decimal,
    tarjeta_declarado: Decimal,
    transferencia_declarado: Decimal,
    vales_declarado: Decimal,
) -> dict:
    """Cierra el turno de farmacia y retorna el resumen."""
    try:
        from farmacia.models import CierreTurnoFarmacia, AperturaCaja

        # La caja pertenece a empresa+sucursal; el usuario que cierra puede ser
        # distinto del responsable que abrió el turno (entrega/recepción).
        q = AperturaCaja.objects.select_for_update().filter(empresa=empresa, activa=True)
        if sucursal:
            q = q.filter(sucursal=sucursal)
        apertura = q.select_related('usuario_responsable').first()

        if not apertura:
            logger.info('[CorteUnificado] Sin apertura de caja activa en farmacia')
            return {'total': Decimal('0'), 'ventas': 0, 'estado': 'sin_apertura'}

        # Calcular total de ventas del turno actual (Venta usa estado, no campo boolean cancelada)
        from core.models import Venta
        ventas_del_turno = Venta.objects.filter(
            empresa=empresa,
            fecha__gte=apertura.fecha_apertura,
        ).exclude(estado='CANCELADA')
        if sucursal:
            ventas_del_turno = ventas_del_turno.filter(sucursal=sucursal)
        from django.db.models import Sum
        total = ventas_del_turno.aggregate(t=Sum('total'))['t'] or Decimal('0')
        num_ventas = ventas_del_turno.count()

        from core.models import GastoCaja, MovimientoCaja, Pago
        gastos_del_turno = GastoCaja.objects.filter(
            empresa=empresa,
            fecha__gte=apertura.fecha_apertura,
            sucursal=apertura.sucursal,
        ).aggregate(t=Sum('monto'))['t'] or Decimal('0')
        pagos_qs = Pago.objects.filter(venta__in=ventas_del_turno)
        pagos = pagos_qs.aggregate(
            efectivo=Sum('monto_efectivo'),
            tarjeta=Sum('monto_tarjeta'),
            transferencia=Sum('monto_transferencia'),
            vales=Sum('monto_vales'),
        )
        efectivo_ventas = pagos['efectivo'] or Decimal('0')
        tarjeta_ventas = pagos['tarjeta'] or Decimal('0')
        transferencia_ventas = pagos['transferencia'] or Decimal('0')
        vales_ventas = pagos['vales'] or Decimal('0')
        if not pagos_qs.exists() and total:
            efectivo_ventas = total
        movimientos_qs = MovimientoCaja.objects.filter(
            empresa=empresa,
            fecha_movimiento__gte=apertura.fecha_apertura,
        ).exclude(concepto='APERTURA_CAJA')
        if sucursal:
            movimientos_qs = movimientos_qs.filter(sucursal=sucursal)
        egresos_kardex = movimientos_qs.filter(
            tipo_movimiento='EGRESO',
        ).exclude(concepto='GASTO_MENOR').aggregate(t=Sum('monto'))['t'] or Decimal('0')
        retiros = movimientos_qs.filter(
            tipo_movimiento='TRANSFERENCIA',
        ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

        cierre = CierreTurnoFarmacia.objects.create(
            empresa=empresa,
            sucursal=apertura.sucursal,
            usuario_responsable=apertura.usuario_responsable,
            cerrado_por=cajero,
            apertura_caja=apertura,
            fecha_apertura=apertura.fecha_apertura,
            efectivo_declarado=efectivo_declarado,
            tarjeta_declarado=tarjeta_declarado,
            transferencia_declarado=transferencia_declarado,
            vales_declarado=vales_declarado,
            efectivo_teorico=efectivo_ventas - gastos_del_turno - egresos_kardex - retiros,
            tarjeta_teorico=tarjeta_ventas,
            transferencia_teorico=transferencia_ventas,
            vales_teorico=vales_ventas,
            observaciones='Cierre generado por corte unificado.',
        )

        return {
            'total': total,
            'num_ventas': num_ventas,
            'gastos': gastos_del_turno,
            'efectivo': efectivo_ventas,
            'egresos_kardex': egresos_kardex,
            'retiros': retiros,
            'tarjeta': tarjeta_ventas,
            'transferencia': transferencia_ventas,
            'vales': vales_ventas,
            'diferencia_efectivo': efectivo_declarado - (apertura.fondo_efectivo + efectivo_ventas - gastos_del_turno - egresos_kardex - retiros),
            'diferencia_tarjeta': tarjeta_declarado - tarjeta_ventas,
            'diferencia_transferencia': transferencia_declarado - transferencia_ventas,
            'diferencia_vales': vales_declarado - vales_ventas,
            'apertura_id': apertura.pk,
            'cierre_id': cierre.pk,
            'folio_cierre': cierre.folio,
            'fondo_inicial': apertura.fondo_efectivo,
            'estado': 'cerrado',
        }
    except (DatabaseError, ValueError, TypeError, AttributeError) as exc:
        logger.warning(f'[CorteUnificado] Error cierre farmacia: {exc}')
        return {'total': Decimal('0'), 'estado': 'error', 'error': str(exc)[:200]}


def _cerrar_laboratorio(cajero, empresa, sucursal, ahora: datetime) -> dict:
    """Calcula el total de órdenes de laboratorio del turno actual."""
    try:
        from django.db.models import Sum as _Sum
        from core.models import OrdenDeServicio

        inicio_turno = ahora - timedelta(hours=12)
        ordenes_qs = OrdenDeServicio.objects.filter(
            empresa=empresa,
            fecha_creacion__gte=inicio_turno,
            fecha_creacion__lte=ahora,
        )
        resultado = ordenes_qs.aggregate(t=_Sum('total'))
        total = Decimal(str(resultado['t'] or 0))
        count = ordenes_qs.count()
        from core.models import PagoOrden
        pagos = PagoOrden.objects.filter(orden__in=ordenes_qs, cancelado=False).aggregate(
            efectivo=_Sum('monto_efectivo'),
            tarjeta=_Sum('monto_tarjeta'),
            transferencia=_Sum('monto_transferencia'),
            vales=_Sum('monto_vales'),
        )
        efectivo = Decimal(str(pagos['efectivo'] or 0))
        digital = Decimal(str((pagos['tarjeta'] or 0) + (pagos['transferencia'] or 0)))
        tarjeta = Decimal(str(pagos['tarjeta'] or 0))
        transferencia = Decimal(str(pagos['transferencia'] or 0))
        vales = Decimal(str(pagos['vales'] or 0))

        return {
            'total': total,
            'ordenes': count,
            'efectivo': efectivo,
            'digital': digital,
            'tarjeta': tarjeta,
            'transferencia': transferencia,
            'vales': vales,
            'estado': 'calculado',
        }
    except (DatabaseError, ValueError, TypeError, AttributeError) as exc:
        logger.warning(f'[CorteUnificado] Error cierre lab: {exc}')
        return {'total': Decimal('0'), 'estado': 'error', 'error': str(exc)[:200]}


def _imprimir_corte(corte_data: dict, host: str):
    """Imprime el ticket de corte por ESC/POS."""
    from farmacia.services.impresora_termica import ImpressoraTermicaTCP, TicketBuilder

    ticket = (
        TicketBuilder()
        .header(corte_data.get('empresa', 'PRISLAB'))
        .texto_libre(f"CORTE DE TURNO — {corte_data.get('fecha', '')[:16]}\n"
                     f"Cajero: {corte_data.get('cajero', '')}")
        .separador()
        .texto_libre('--- FARMACIA ---')
        .linea('Total Farmacia',
               corte_data.get('farmacia', {}).get('total', '0.00'))
        .separador()
        .texto_libre('--- LABORATORIO ---')
        .linea('Total Laboratorio',
               corte_data.get('laboratorio', {}).get('total', '0.00'))
        .separador()
        .total(corte_data.get('total_consolidado', '0.00'))
        .linea('Efectivo declarado',
               corte_data.get('efectivo_declarado', '0.00'))
        .linea('Diferencia',
               corte_data.get('diferencia', '0.00'))
        .texto_libre(f"\nESTADO: {corte_data.get('estado', '')}", centrado=True)
        .footer()
        .cortar()
        .build()
    )

    imp = ImpressoraTermicaTCP(host)
    resultado = imp.imprimir(ticket)
    corte_data['ticket_impreso'] = resultado.get('ok', False)
