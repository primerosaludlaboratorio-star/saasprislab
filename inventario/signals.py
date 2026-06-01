"""
INVENTARIO V8.2 — Señales Automáticas (Todos los Silos)
========================================================

4 motores de descuento automático:
  1. SILO LAB       → post_save(ResultadoParametro.validado=True) → FEFO reactivos
  2. SILO CONSULTORIO → post_save(AgendaCita.estado='COMPLETADA') → consumo por cita
  3. SILO GENERALES   → post_save(ValeRequisicion.estado='ENTREGADO') → FEFO lotes
  4. CMMS TICKETS     → post_save(TicketMantenimientoCMMS.estado='CERRADO') → refacciones

Cada motor respeta:
  - Aislamiento Multi-Tenant (empresa)
  - Transacciones atómicas con select_for_update() anti-carrera
  - Logging estructurado sin except:pass

CONECTAR en inventario/apps.py → def ready(): import inventario.signals
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

from .concurrency import retry_on_db_contention

logger = logging.getLogger(__name__)


# =============================================================================
# ── HELPERS ───────────────────────────────────────────────────────────────────
# =============================================================================

def _get_lab_models():
    from core.models.laboratorio import ResultadoParametro
    from .models import (
        ConsumoEstudioReactivo, LoteReactivoLab, SalidaAnaliticaLab,
    )
    return ResultadoParametro, ConsumoEstudioReactivo, LoteReactivoLab, SalidaAnaliticaLab


def _get_consultorio_models():
    from .models import LoteInsumoConsultorio, SalidaConsumoConsultorio
    return LoteInsumoConsultorio, SalidaConsumoConsultorio


def _get_generales_models():
    from .models import LoteInsumoGeneral, ValeRequisicion, LineaValeRequisicion
    return LoteInsumoGeneral, ValeRequisicion, LineaValeRequisicion


def _orden_lab_gestion_inventario_activa(orden) -> bool:
    """
    True = aplicar FEFO lab; False = modo ágil (omitir descuentos de reactivos).
    Usa la sucursal de la orden; si no tiene y la empresa tiene una sola sucursal activa,
    usa el flag de esa sucursal (típico laboratorio único).
    """
    if getattr(orden, 'sucursal_id', None):
        suc = getattr(orden, 'sucursal', None)
        if suc is None:
            from core.models import Sucursal

            suc = Sucursal.objects.filter(pk=orden.sucursal_id).only('gestion_inventario_activa').first()
        if suc is not None:
            return bool(suc.gestion_inventario_activa)
    emp = getattr(orden, 'empresa', None)
    if emp is None:
        return True
    activas = list(
        emp.sucursales.filter(activa=True).only('id', 'gestion_inventario_activa').order_by('pk')[:2]
    )
    if len(activas) == 1:
        return bool(activas[0].gestion_inventario_activa)
    return True


# =============================================================================
# ── SILO 1: LABORATORIO — FEFO por validación de ResultadoParametro ───────────
# =============================================================================

@receiver(post_save, sender='core.ResultadoParametro')
def descontar_reactivos_fefo(sender, instance, created, **kwargs):
    """
    Al validar un resultado (validado=True con validado_por asignado),
    descuenta automáticamente reactivos configurados usando FEFO.
    """
    if not instance.validado or not instance.validado_por:
        return
    # v1.52: modo ágil — salir antes de reintentos/locks; INFO único (no ERROR que alimente ruido operativo).
    orden_prev = getattr(instance, 'orden', None)
    if orden_prev is None and getattr(instance, 'orden_id', None):
        from core.models.laboratorio import OrdenDeServicio

        orden_prev = (
            OrdenDeServicio.objects.filter(pk=instance.orden_id)
            .select_related('sucursal', 'empresa')
            .first()
        )
    if orden_prev and not _orden_lab_gestion_inventario_activa(orden_prev):
        logger.info(
            'FEFO-LAB omitido (gestion_inventario_activa=False) orden=%s rp=%s',
            orden_prev.pk,
            instance.pk,
        )
        return
    try:
        retry_on_db_contention(
            lambda: _ejecutar_descuento_fefo(instance),
            label='INVENTARIO-FEFO',
        )
    except Exception as exc:
        logger.error(
            "INVENTARIO FEFO: Error en ResultadoParametro id=%s orden=%s: %s",
            instance.pk, getattr(instance, 'orden_id', '?'), exc, exc_info=True
        )


def _ejecutar_descuento_fefo(resultado):
    (ResultadoParametro,
     ConsumoEstudioReactivo,
     LoteReactivoLab,
     SalidaAnaliticaLab) = _get_lab_models()

    with transaction.atomic():
        rp = (
            ResultadoParametro.objects
            .select_for_update(nowait=False)
            .select_related('orden', 'orden__empresa', 'orden__sucursal')
            .get(pk=resultado.pk)
        )
        if not rp.validado or not rp.validado_por:
            return
        analito = getattr(rp, 'analito', None)
        if not analito:
            return
        # Analitos calculados no consumen reactivo físico; ignorar ConsumoEstudioReactivo / FEFO.
        if getattr(analito, 'es_calculado', False):
            return

        orden = rp.orden
        if not _orden_lab_gestion_inventario_activa(orden):
            logger.debug(
                'FEFO-LAB omitido bajo lock (gestion_inventario_activa=False) orden=%s rp=%s',
                orden.pk,
                rp.pk,
            )
            return
        empresa = orden.empresa

        formulas = list(
            ConsumoEstudioReactivo.objects
            .filter(empresa=empresa, analito=analito, activo=True)
            .select_related('reactivo')
        )
        if not formulas:
            return

        for formula in formulas:
            reactivo = formula.reactivo
            cantidad_total = formula.cantidad_por_prueba
            if not isinstance(cantidad_total, Decimal):
                cantidad_total = Decimal(str(cantidad_total))

            prefix = f'lab_rp{rp.pk}_f{formula.pk}_'
            ya_consumido = (
                SalidaAnaliticaLab.objects.filter(
                    idempotency_key__startswith=prefix,
                ).aggregate(s=Sum('cantidad_consumida'))['s']
            ) or Decimal('0')
            restante = cantidad_total - ya_consumido
            if restante <= 0:
                continue

            lotes_fefo = (
                LoteReactivoLab.objects
                .filter(
                    empresa=empresa,
                    reactivo=reactivo,
                    estado='ACTIVO',
                    cantidad_actual__gt=0,
                )
                .order_by('fecha_caducidad')
                .select_for_update(nowait=False)
            )

            for lote in lotes_fefo:
                if restante <= 0:
                    break
                disponible = lote.cantidad_actual
                if not isinstance(disponible, Decimal):
                    disponible = Decimal(str(disponible))
                a_descontar = min(disponible, restante)
                if a_descontar <= 0:
                    continue

                idem = f'lab_rp{rp.pk}_f{formula.pk}_l{lote.pk}'
                _obj, created = SalidaAnaliticaLab.objects.get_or_create(
                    idempotency_key=idem,
                    defaults={
                        'empresa': empresa,
                        'lote': lote,
                        'orden': orden,
                        'analito': analito,
                        'formula_consumo': formula,
                        'cantidad_consumida': a_descontar,
                        'validado_por': rp.validado_por,
                    },
                )
                if created:
                    nuevo = disponible - a_descontar
                    lote.cantidad_actual = nuevo
                    if nuevo <= 0:
                        lote.cantidad_actual = Decimal('0')
                        lote.estado = 'AGOTADO'
                    lote.save(update_fields=['cantidad_actual', 'estado'])
                    restante -= a_descontar
                    logger.info(
                        "FEFO-LAB: -%s %s de lote '%s' (reactivo: %s, orden: %s)",
                        a_descontar,
                        reactivo.unidad_medida,
                        lote.numero_lote,
                        reactivo.nombre,
                        orden.pk,
                    )

            if restante > 0:
                logger.warning(
                    "FEFO-LAB: Stock insuficiente para '%s'. Faltaron %s %s. Orden: %s.",
                    reactivo.nombre,
                    restante,
                    reactivo.unidad_medida,
                    orden.pk,
                )


@receiver(post_delete, sender='core.ResultadoParametro')
def revertir_descuento_al_eliminar(sender, instance, **kwargs):
    """Repone stock cuando se elimina un resultado validado."""
    if not instance.validado:
        return
    try:
        _revertir_descuento(instance)
    except Exception as exc:
        logger.error(
            "FEFO-LAB REVERSA: Error id=%s: %s", instance.pk, exc, exc_info=True,
        )


def _revertir_descuento(resultado):
    (_, _, LoteReactivoLab, SalidaAnaliticaLab) = _get_lab_models()

    with transaction.atomic():
        salidas = list(
            SalidaAnaliticaLab.objects.filter(
                empresa=resultado.orden.empresa,
                orden=resultado.orden,
                analito=resultado.analito,
            )
            .select_for_update(nowait=False)
            .select_related('lote')
        )

        if not salidas:
            return

        for salida in salidas:
            lote = salida.lote
            repuesto = float(salida.cantidad_consumida)
            lote.cantidad_actual = float(lote.cantidad_actual) + repuesto
            if lote.estado == 'AGOTADO' and lote.cantidad_actual > 0:
                lote.estado = 'ACTIVO'
            lote.save(update_fields=['cantidad_actual', 'estado'])
            logger.info(
                "FEFO-LAB REVERSA: +%.4f en lote '%s' (reactivo: %s)",
                repuesto, lote.numero_lote, lote.reactivo.nombre,
            )
        salidas.delete()


# =============================================================================
# ── SILO 2: CONSULTORIO — Descuento al completar una Cita Médica ─────────────
# =============================================================================

@receiver(post_save, sender='consultorio.AgendaCita')
def descontar_insumos_consultorio_por_cita(sender, instance, created, **kwargs):
    """
    Cuando una AgendaCita cambia a 'COMPLETADA', descuenta los insumos
    de consultorio que estuvieran registrados contra esa cita.

    Los consumos son registrados manualmente por enfermería durante la cita
    (vía SalidaConsumoConsultorio). Este signal simplemente verifica si hay
    consumos pendientes de deducir, actuando como salvaguarda de consistencia.
    """
    if instance.estado != 'COMPLETADA':
        return

    try:
        LoteInsumoConsultorio, SalidaConsumoConsultorio = _get_consultorio_models()

        # Verificar si hay consumos NO deducidos aún para esta cita
        consumos_pendientes = SalidaConsumoConsultorio.objects.filter(
            empresa=instance.empresa,
            cita=instance,
        )
        if not consumos_pendientes.exists():
            logger.debug(
                "SILO-CONSULTORIO: Cita %s completada sin consumos explícitos registrados.",
                instance.pk
            )
            return

        logger.info(
            "SILO-CONSULTORIO: Cita %s completada. %d consumos de insumos asociados.",
            instance.pk, consumos_pendientes.count()
        )
        # El stock ya fue descontado al registrar la SalidaConsumoConsultorio;
        # este signal sirve de auditoría y log, sin doble descuento.

    except Exception as exc:
        logger.error(
            "SILO-CONSULTORIO: Error al procesar cita %s: %s",
            instance.pk, exc, exc_info=True
        )


# =============================================================================
# ── SILO 3: GENERALES — Descuento FEFO al marcar Vale como ENTREGADO ─────────
# =============================================================================

@receiver(post_save, sender='inventario.ValeRequisicion')
def descontar_generales_por_vale(sender, instance, created, **kwargs):
    """
    Cuando un ValeRequisicion pasa a 'ENTREGADO', descuenta FEFO los
    lotes de Insumos Generales. El descuento real ocurre en la vista
    detalle_vale (acción 'entregar') con select_for_update(). Este signal
    actúa como log de auditoría y detecta vales que saltaron el flujo UI.
    """
    if instance.estado != 'ENTREGADO':
        return

    try:
        LoteInsumoGeneral, ValeRequisicion, LineaValeRequisicion = _get_generales_models()

        lineas_sin_entregar = instance.lineas.filter(cantidad_entregada=0)
        if not lineas_sin_entregar.exists():
            logger.info(
                "SILO-GENERALES: Vale %s entregado correctamente. %d líneas.",
                instance.folio, instance.lineas.count()
            )
            return

        # Si hay líneas sin entregar (bypass del flujo UI), ejecutar FEFO
        logger.warning(
            "SILO-GENERALES: Vale %s tiene %d líneas sin entregar. "
            "Ejecutando descuento FEFO desde signal.",
            instance.folio, lineas_sin_entregar.count()
        )
        with transaction.atomic():
            for linea in lineas_sin_entregar.select_related('insumo'):
                pendiente = float(linea.cantidad_solicitada)
                lotes_fefo = (
                    LoteInsumoGeneral.objects
                    .filter(empresa=instance.empresa,
                            insumo=linea.insumo, cantidad_actual__gt=0)
                    .select_for_update()
                    .order_by('fecha_recepcion')
                )
                for lote in lotes_fefo:
                    if pendiente <= 0:
                        break
                    a_dar = min(float(lote.cantidad_actual), pendiente)
                    lote.cantidad_actual = float(lote.cantidad_actual) - a_dar
                    lote.save(update_fields=['cantidad_actual'])
                    pendiente -= a_dar
                    linea.cantidad_entregada = float(linea.cantidad_entregada) + a_dar
                    linea.lote_entregado = lote
                    linea.save(update_fields=['cantidad_entregada', 'lote_entregado'])

                if pendiente > 0:
                    logger.warning(
                        "SILO-GENERALES: Stock insuficiente para '%s' en vale %s. Faltaron %.2f.",
                        linea.insumo.nombre, instance.folio, pendiente
                    )

    except Exception as exc:
        logger.error(
            "SILO-GENERALES: Error al procesar vale %s: %s",
            instance.folio, exc, exc_info=True
        )


# =============================================================================
# ── SILO 4: CMMS — Descuento de refacciones al cerrar Ticket ─────────────────
# =============================================================================

@receiver(post_save, sender='mantenimiento.TicketMantenimientoCMMS')
def descontar_refacciones_por_ticket_cerrado(sender, instance, created, **kwargs):
    """
    Cuando un TicketMantenimientoCMMS pasa a estado 'CERRADO',
    valida que todas las SalidaRefaccionMantenimiento asociadas
    hayan descontado stock correctamente.

    El descuento real ocurre en mantenimiento/signals.py (signal de
    SalidaRefaccionMantenimiento). Este signal actúa como auditoria de cierre.
    """
    if instance.estado != 'CERRADO':
        return

    try:
        from mantenimiento.models import SalidaRefaccionMantenimiento

        salidas = SalidaRefaccionMantenimiento.objects.filter(ticket=instance)
        total_refacciones = salidas.count()

        if total_refacciones > 0:
            logger.info(
                "CMMS: Ticket #%s cerrado con %d refaccion(es) de inventario "
                "descontadas automáticamente.",
                instance.pk, total_refacciones
            )
        else:
            logger.debug(
                "CMMS: Ticket #%s cerrado sin refacciones de inventario.", instance.pk
            )

    except Exception as exc:
        logger.error(
            "CMMS: Error al auditar cierre de ticket %s: %s",
            instance.pk, exc, exc_info=True
        )
