"""
PRISLAB V5 - Monitor de Producción del Laboratorio (Semaforización de Muestras)
Dashboard Kanban para rastrear el flujo de cada orden desde recepción hasta entrega.

Columnas:
  🔴 ROJO    (Pendientes)  → Órdenes recién creadas, esperando toma de muestra
  🟡 AMARILLO (En Proceso) → Muestras siendo analizadas
  🔵 AZUL    (Por Validar) → Resultados capturados, pendientes de autorización
  🟢 VERDE   (Finalizados) → Listos para imprimir o enviar
"""

import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, F, DurationField, ExpressionWrapper, Prefetch
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.lims_cart import detalle_orden_etiqueta
from core.models import OrdenDeServicio, DetalleOrden, Usuario

logger = logging.getLogger(__name__)

_PREFETCH_DETALLES_MONITOR = Prefetch(
    'detalles',
    queryset=DetalleOrden.objects.select_related(
        'analito', 'perfil_lims', 'paquete_lims'
    ),
)


def _calcular_metricas_tiempo(qs, ahora):
    """
    Calcula métricas de desempeño (tiempos de proceso) para las órdenes visibles.
    
    Tiempos medidos:
    1. Recepción → Toma de muestra  (fecha_creacion → fecha_toma_muestra)
    2. Toma de muestra → Validación  (fecha_toma_muestra → DetalleOrden.fecha_validacion)
    3. Total: Recepción → Finalizado (fecha_creacion → última fecha_validacion)
    
    Returns:
        dict con promedios en minutos y formato humano
    """
    metricas = {
        'recepcion_a_muestra': None,
        'muestra_a_validacion': None,
        'total_proceso': None,
        'ordenes_analizadas': 0,
    }
    
    try:
        # Tiempo 1: Recepción → Toma de muestra
        con_muestra = qs.filter(
            fecha_toma_muestra__isnull=False
        )
        if con_muestra.exists():
            avg_1 = con_muestra.annotate(
                delta=ExpressionWrapper(
                    F('fecha_toma_muestra') - F('fecha_creacion'),
                    output_field=DurationField()
                )
            ).aggregate(prom=Avg('delta'))['prom']
            
            if avg_1:
                mins = avg_1.total_seconds() / 60
                metricas['recepcion_a_muestra'] = _formato_tiempo(mins)
        
        # Tiempo 2 y 3: Usando DetalleOrden.fecha_validacion
        detalles_val = DetalleOrden.objects.filter(
            orden__in=qs,
            fecha_validacion__isnull=False,
        ).select_related('orden')
        
        tiempos_muestra_val = []
        tiempos_total = []
        
        for d in detalles_val:
            orden = d.orden
            # Muestra → Validación
            if orden.fecha_toma_muestra and d.fecha_validacion:
                delta = (d.fecha_validacion - orden.fecha_toma_muestra).total_seconds() / 60
                if 0 < delta < 1440:  # Menos de 24h (filtrar outliers)
                    tiempos_muestra_val.append(delta)
            
            # Total: Recepción → Validación
            if orden.fecha_creacion and d.fecha_validacion:
                delta = (d.fecha_validacion - orden.fecha_creacion).total_seconds() / 60
                if 0 < delta < 1440:
                    tiempos_total.append(delta)
        
        if tiempos_muestra_val:
            avg_mv = sum(tiempos_muestra_val) / len(tiempos_muestra_val)
            metricas['muestra_a_validacion'] = _formato_tiempo(avg_mv)
        
        if tiempos_total:
            avg_total = sum(tiempos_total) / len(tiempos_total)
            metricas['total_proceso'] = _formato_tiempo(avg_total)
            metricas['ordenes_analizadas'] = len(tiempos_total)
    
    except Exception as e:
        logger.warning(f"Error calculando métricas de tiempo: {e}")
    
    return metricas


def _formato_tiempo(minutos):
    """Convierte minutos a formato legible."""
    if minutos is None:
        return None
    minutos = abs(minutos)
    if minutos < 60:
        return {'valor': round(minutos), 'unidad': 'min', 'texto': f'{round(minutos)} min'}
    horas = minutos / 60
    if horas < 24:
        return {'valor': round(horas, 1), 'unidad': 'hrs', 'texto': f'{round(horas, 1)} hrs'}
    dias = horas / 24
    return {'valor': round(dias, 1), 'unidad': 'dias', 'texto': f'{round(dias, 1)} dias'}


# ======================================================================
# MAPEO DE ESTADOS → COLUMNAS KANBAN
# ======================================================================
KANBAN_COLUMNS = {
    'pendiente': {
        'label': 'Pendientes',
        'color': '#dc3545',      # Rojo
        'bg': '#fff5f5',
        'icon': 'fas fa-clock',
        'estados': ['PENDIENTE_TOMA'],
    },
    'en_proceso': {
        'label': 'En Proceso',
        'color': '#ffc107',      # Amarillo
        'bg': '#fffbeb',
        'icon': 'fas fa-flask',
        'estados': ['TOMA_REALIZADA', 'EN_PROCESO'],
    },
    'por_validar': {
        'label': 'Por Validar',
        'color': '#0d6efd',      # Azul
        'bg': '#eff6ff',
        'icon': 'fas fa-user-check',
        'estados': ['VALIDADO_PARCIAL'],
    },
    'finalizado': {
        'label': 'Finalizados',
        'color': '#198754',      # Verde
        'bg': '#f0fdf4',
        'icon': 'fas fa-check-circle',
        'estados': ['COMPLETO', 'ENTREGADO'],
    },
}

# Transiciones válidas (estado_actual → siguiente estado)
TRANSICIONES_VALIDAS = {
    'PENDIENTE_TOMA': 'TOMA_REALIZADA',
    'TOMA_REALIZADA': 'EN_PROCESO',
    'EN_PROCESO': 'VALIDADO_PARCIAL',
    'VALIDADO_PARCIAL': 'COMPLETO',
    'COMPLETO': 'ENTREGADO',
}

TRANSICION_LABELS = {
    'PENDIENTE_TOMA': 'Registrar Toma',
    'TOMA_REALIZADA': 'Iniciar Análisis',
    'EN_PROCESO': 'Enviar a Validación',
    'VALIDADO_PARCIAL': 'Aprobar Resultados',
    'COMPLETO': 'Marcar Entregado',
}


def _orden_to_card(orden, ahora):
    """Convierte una OrdenDeServicio en datos para la tarjeta Kanban."""
    delta = ahora - orden.fecha_creacion
    minutos = int(delta.total_seconds() / 60)
    
    if minutos < 60:
        tiempo_str = f"{minutos} min"
    elif minutos < 1440:
        horas = minutos // 60
        mins_rest = minutos % 60
        tiempo_str = f"{horas}h {mins_rest}m"
    else:
        dias = minutos // 1440
        tiempo_str = f"{dias}d"
    
    # Usar lista en memoria (prefetch LIMS) — evita count()/filter() que disparan N+1
    detalles_list = list(orden.detalles.all())
    total_estudios = len(detalles_list)
    estudios_listos = sum(
        1 for d in detalles_list
        if getattr(d, 'estado_procesamiento', '') == 'RESULTADO_LISTO'
    )
    estudios_nombres = []
    for d in detalles_list[:4]:
        lab = detalle_orden_etiqueta(d).strip()
        if lab:
            estudios_nombres.append(lab)
    
    es_urgente = orden.tipo_servicio == 'URGENCIA'
    sig_estado = TRANSICIONES_VALIDAS.get(orden.estado_clinico)
    sig_label = TRANSICION_LABELS.get(orden.estado_clinico, '')
    
    return {
        'id': orden.id,
        'folio': orden.folio_orden or f'ORD-{orden.id}',
        'paciente': orden.paciente.nombre_completo if orden.paciente else 'Sin paciente',
        'fecha_creacion': orden.fecha_creacion.strftime('%d/%m %H:%M'),
        'minutos_transcurridos': minutos,
        'tiempo_str': tiempo_str,
        'estado_clinico': orden.estado_clinico,
        'tipo_servicio': orden.tipo_servicio,
        'es_urgente': es_urgente,
        'total_estudios': total_estudios,
        'estudios_listos': estudios_listos,
        'progreso_pct': int((estudios_listos / total_estudios * 100) if total_estudios > 0 else 0),
        'siguiente_estado': sig_estado,
        'siguiente_label': sig_label,
        'estudios_nombres': estudios_nombres,
    }


# ======================================================================
# VISTA PRINCIPAL: MONITOR DE PRODUCCIÓN (KANBAN)
# ======================================================================

@login_required
def monitor_produccion(request):
    """
    Dashboard Kanban de producción del laboratorio.
    Divide las órdenes en 4 columnas por estado clínico.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    filtro_urgencia = request.GET.get('urgencia', '')
    
    # Base queryset: órdenes activas (no canceladas, no eliminadas)
    qs = OrdenDeServicio.objects.filter(
        empresa=empresa,
        deleted_at__isnull=True,
    ).exclude(
        estado='CANCELADO'
    ).select_related(
        'paciente', 'medico_referente', 'responsable_ingreso'
    ).prefetch_related(
        _PREFETCH_DETALLES_MONITOR,
    ).order_by('-fecha_creacion')
    
    # Filtro de urgencia
    if filtro_urgencia == 'URGENCIA':
        qs = qs.filter(tipo_servicio='URGENCIA')
    elif filtro_urgencia == 'RUTINA':
        qs = qs.filter(tipo_servicio='RUTINA')
    
    ahora = timezone.now()
    
    # Solo órdenes de los últimos 7 días (evitar cargar todo el histórico)
    qs = qs.filter(fecha_creacion__gte=ahora - timedelta(days=7))
    
    # Construir columnas
    columnas = []
    total_ordenes = 0
    
    for key, config in KANBAN_COLUMNS.items():
        ordenes_col = qs.filter(estado_clinico__in=config['estados'])
        cards = [_orden_to_card(o, ahora) for o in ordenes_col]
        total_ordenes += len(cards)
        
        columnas.append({
            'key': key,
            'label': config['label'],
            'color': config['color'],
            'bg': config['bg'],
            'icon': config['icon'],
            'count': len(cards),
            'cards': cards,
        })
    
    # Contadores rápidos
    urgentes_count = qs.filter(tipo_servicio='URGENCIA').count()
    rutina_count = qs.filter(tipo_servicio='RUTINA').count()
    
    # ── METRICAS DE DESEMPEÑO: Tiempos de Proceso ──
    metricas_tiempo = _calcular_metricas_tiempo(qs, ahora)
    
    context = {
        'columnas': columnas,
        'total_ordenes': total_ordenes,
        'urgentes_count': urgentes_count,
        'rutina_count': rutina_count,
        'filtro_urgencia': filtro_urgencia,
        'metricas_tiempo': metricas_tiempo,
    }
    
    return render(request, 'core/laboratorio/monitor_produccion.html', context)


# ======================================================================
# API AJAX: DATOS DEL MONITOR (PARA AUTO-REFRESH)
# ======================================================================

@login_required
def api_monitor_datos(request):
    """
    Retorna los datos del monitor en JSON para auto-refresh AJAX.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'columnas': [], 'total_ordenes': 0}, safe=False)
    filtro_urgencia = request.GET.get('urgencia', '')
    
    qs = OrdenDeServicio.objects.filter(
        empresa=empresa,
        deleted_at__isnull=True,
    ).exclude(
        estado='CANCELADO'
    ).select_related(
        'paciente', 'medico_referente', 'responsable_ingreso'
    ).prefetch_related(
        _PREFETCH_DETALLES_MONITOR,
    ).order_by('-fecha_creacion')
    
    if filtro_urgencia == 'URGENCIA':
        qs = qs.filter(tipo_servicio='URGENCIA')
    elif filtro_urgencia == 'RUTINA':
        qs = qs.filter(tipo_servicio='RUTINA')
    
    ahora = timezone.now()
    qs = qs.filter(fecha_creacion__gte=ahora - timedelta(days=7))
    
    columnas = {}
    for key, config in KANBAN_COLUMNS.items():
        ordenes_col = qs.filter(estado_clinico__in=config['estados'])
        columnas[key] = {
            'label': config['label'],
            'count': ordenes_col.count(),
            'cards': [_orden_to_card(o, ahora) for o in ordenes_col],
        }
    
    return JsonResponse({
        'status': 'success',
        'columnas': columnas,
        'timestamp': ahora.isoformat(),
    })


# ======================================================================
# API AJAX: AVANZAR ESTADO DE UNA ORDEN
# ======================================================================

def _descontar_insumos_orden(orden, usuario=None):
    """
    CEREBRO DE INVENTARIO (R107): Al finalizar una orden, descuenta
    automáticamente los insumos/reactivos vinculados a cada estudio.
    Usa InsumoEstudio para saber qué y cuánto descontar.
    """
    try:
        from laboratorio.models import InsumoEstudio
        from decimal import Decimal

        detalles = orden.detalles.select_related('estudio').all()
        descuentos = []

        for detalle in detalles:
            estudio = detalle.estudio
            if not estudio:
                continue

            insumos = InsumoEstudio.objects.filter(
                estudio=estudio
            ).select_related('producto')

            for insumo in insumos:
                producto = insumo.producto
                cantidad = int(insumo.cantidad)

                cant_real = min(cantidad, producto.stock) if producto.stock > 0 else 0

                if cant_real > 0:
                    # Usar Kardex (MovimientoInventario) para trazabilidad
                    try:
                        from farmacia.models import MovimientoInventario
                        MovimientoInventario.objects.create(
                            empresa=orden.empresa,
                            producto=producto,
                            tipo_movimiento='SALIDA_USO_INTERNO',
                            cantidad=cant_real,
                            costo_unitario=producto.precio_compra or Decimal('0.00'),
                            observaciones=(
                                f'Consumo estudio {estudio.nombre} - '
                                f'Orden {orden.folio_orden}'
                            ),
                            usuario_responsable=usuario or orden.responsable_ingreso,
                        )
                    except Exception:
                        # Fallback: actualizar stock directamente
                        producto.stock = max(0, (producto.stock or 0) - cant_real)
                        producto.save(update_fields=['stock'])

                    if cant_real < cantidad:
                        descuentos.append(
                            f"{producto.nombre}: -{cant_real} (PARCIAL, faltaron {cantidad - cant_real})"
                        )
                        logger.warning(
                            f"[INSUMOS] Stock insuficiente: {producto.nombre} "
                            f"(necesita {cantidad}, tiene {producto.stock}) "
                            f"para estudio {estudio.nombre} en orden {orden.folio_orden}"
                        )
                    else:
                        descuentos.append(
                            f"{producto.nombre}: -{cant_real} (quedan {max(0, producto.stock - cant_real)})"
                        )
                else:
                    logger.warning(
                        f"[INSUMOS] Sin stock: {producto.nombre} "
                        f"(necesita {cantidad}) - orden {orden.folio_orden}"
                    )

        if descuentos:
            logger.info(
                f"[INSUMOS] Orden {orden.folio_orden}: {len(descuentos)} insumos descontados | "
                + " | ".join(descuentos[:5])
            )

    except Exception as e:
        logger.error(f"[INSUMOS] Error descontando insumos para {orden.folio_orden}: {e}")


@login_required
@require_POST
def api_avanzar_estado(request):
    """
    Avanza la orden al siguiente estado en el flujo.
    Body JSON: { "orden_id": int }
    CICLO 13: select_for_update() must run inside transaction.atomic().
    """
    import json
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Usuario sin empresa asignada'
        }, status=403)
    try:
        try:
            data = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        orden_id = data.get('orden_id')
        if orden_id is None:
            return JsonResponse({'status': 'error', 'mensaje': 'Falta orden_id'}, status=400)

        # Verificar transición ANTES de abrir el atomic para evitar return dentro del bloque
        _orden_check = OrdenDeServicio.objects.filter(id=orden_id, empresa=empresa).first()
        if not _orden_check:
            return JsonResponse({'status': 'error', 'mensaje': 'Orden no encontrada'}, status=404)
        if not TRANSICIONES_VALIDAS.get(_orden_check.estado_clinico):
            return JsonResponse({
                'status': 'error',
                'mensaje': f'No hay transición válida desde "{_orden_check.estado_clinico}"'
            }, status=400)

        with transaction.atomic():
            orden = OrdenDeServicio.objects.select_for_update().get(
                id=orden_id,
                empresa=empresa
            )
            estado_actual = orden.estado_clinico
            sig_estado = TRANSICIONES_VALIDAS.get(estado_actual)
            if not sig_estado:
                raise ValueError(f'Transición inválida desde "{estado_actual}" (condición de carrera)')
            
            # Aplicar transición
            orden.estado_clinico = sig_estado
            alertas_ia = []  # SENTINEL 2.0: alertas para cualquier transicion
            
            # Acciones adicionales por transición
            if sig_estado == 'TOMA_REALIZADA' and not orden.hora_toma_muestra:
                orden.hora_toma_muestra = timezone.now()
                orden.fecha_toma_muestra = timezone.now()
                orden.usuario_tomo_muestra = request.user
            
            if sig_estado in ('EN_PROCESO', 'RESULTADOS_LISTOS'):
                if orden.estado == 'PAGADO':
                    orden.estado = 'EN_PROCESO'
            
            if sig_estado == 'COMPLETO':
                orden.estado = 'RESULTADOS_LISTOS'
                # ── SENTINEL 2.0: Validacion IA pre-finalizacion ──
                alertas_ia = []
                try:
                    from core.services.validador_ia import validar_orden_completa
                    alertas_ia = validar_orden_completa(orden)
                except Exception:
                    pass
                # ── CEREBRO DE INVENTARIO: Descontar insumos automáticamente ──
                _descontar_insumos_orden(orden, request.user)
            
            if sig_estado == 'ENTREGADO':
                orden.estado = 'ENTREGADO'
            
            orden.save()
        
        # ============================================================
        # TRIGGER: Generar PDF al marcar como COMPLETO (finalizado)
        # ============================================================
        pdf_url = None
        if sig_estado == 'COMPLETO':
            try:
                from core.services.motor_reportes_lab import (
                    generar_reporte_pdf,
                    guardar_reporte_en_storage,
                )
                from core.utils.candado_financiero import ReportePdfSaldoPendienteError

                pdf_bytes = generar_reporte_pdf(orden, request=request)
                pdf_url = guardar_reporte_en_storage(orden, pdf_bytes)
                logger.info(f"PDF generado automaticamente para {orden.folio_orden}: {pdf_url}")
            except ReportePdfSaldoPendienteError:
                logger.warning(
                    "PDF automático omitido: saldo pendiente en orden %s",
                    orden.folio_orden or orden.id,
                )
            except Exception as e_pdf:
                logger.error(f"Error generando PDF para {orden.folio_orden}: {e_pdf}")
        
        logger.info(
            f"Orden {orden.folio_orden} avanzada: {estado_actual} → {sig_estado} "
            f"por {request.user.get_full_name()}"
        )
        
        # ── R107: AuditLog ──
        try:
            from core.services.audit_service import registrar_auditoria
            registrar_auditoria(
                accion='UPDATE',
                modelo='OrdenDeServicio',
                objeto_id=str(orden.id),
                datos_anteriores={'estado_clinico': estado_actual},
                datos_nuevos={'estado_clinico': sig_estado},
                request=request,
            )
        except Exception:
            pass
        
        response_data = {
            'status': 'success',
            'orden_id': orden.id,
            'estado_anterior': estado_actual,
            'estado_nuevo': sig_estado,
            'mensaje': f'Orden {orden.folio_orden} actualizada correctamente',
        }
        
        # ── SENTINEL 2.0: Incluir alertas IA si existen ──
        if alertas_ia:
            response_data['alertas_ia'] = alertas_ia
            response_data['tiene_alertas'] = True
        
        if pdf_url:
            response_data['pdf_url'] = pdf_url
            response_data['mensaje'] += ' | PDF generado y guardado'
            # Datos para WhatsApp
            response_data['whatsapp_msg'] = (
                f'Hola, sus resultados de laboratorio (Folio: {orden.folio_orden}) '
                f'ya estan listos. Puede consultarlos en: {pdf_url}'
            )
        
        return JsonResponse(response_data)
        
    except OrdenDeServicio.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Orden no encontrada'
        }, status=404)
    except Exception as e:
        logger.error(f"Error avanzando estado: {e}")
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=500)
