"""
Módulo de Vistas para Laboratorio Clínico.
Incluye: Recepción, búsqueda de estudios, órdenes de servicio, tickets, lista de trabajo.
"""
import json
import io
import os
from types import SimpleNamespace
import base64
import re
import logging
from decimal import Decimal
from datetime import timedelta, datetime
from django.shortcuts import render, get_object_or_404, redirect

logger = logging.getLogger('core')
from django.db import transaction, IntegrityError
from django.db.models import Q, Value, IntegerField
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import qrcode

from django.conf import settings
from django.core import signing
from django.urls import reverse

from core.models import (
    Empresa, Paciente, OrdenDeServicio,
    DetalleOrden, AuditLog, ControlCalidad, TomaMuestra,
    PreOrdenLaboratorio, DetallePreOrden, GastoCaja, PagoOrden,
    Medico, Convenio, ResultadoParametro, ForenseAcceso,
)
from core.lims_cart import (
    aplicar_precio_convenio,
    convenio_precio_map,
    detalle_orden_etiqueta,
    resolve_lims_cart_ids,
    resolve_lims_line,
    search_lims_catalog,
)
from core.utils.trazabilidad import registrar_trazabilidad, serializar_modelo
from core.services.audit_service import registrar_auditoria
from core.services.lims import OrdenServicioLims, parse_optional_client_mutation_uuid, ResultadosLimsService
from core.services.forense_service import metadata_consentimiento_snapshot, registrar_acceso_forense
from core.api_contracts.errors import BusinessApiError
from core.decorators import role_required
from lims.models import Analito

# Logger para transacciones críticas
logger_core = logging.getLogger('core')


def _convenio_desde_tarifa(orden, empresa):
    t = (getattr(orden, 'tarifa', '') or '')
    if not t.startswith('CONVENIO_'):
        return None
    try:
        cid = int(t.split('_', 1)[1])
    except (ValueError, IndexError):
        return None
    return Convenio.objects.filter(id=cid, empresa=empresa).first()


def _lims_line_key_detalle(detail):
    if getattr(detail, 'analito_id', None):
        return ('analito', detail.analito_id)
    if getattr(detail, 'perfil_lims_id', None):
        return ('perfil', detail.perfil_lims_id)
    if getattr(detail, 'paquete_lims_id', None):
        return ('paquete', detail.paquete_lims_id)
    return (None, None)


def _lims_line_key_row(row):
    if row.get('analito'):
        return ('analito', row['analito'].id)
    if row.get('perfil_lims'):
        return ('perfil', row['perfil_lims'].id)
    if row.get('paquete_lims'):
        return ('paquete', row['paquete_lims'].id)
    return (None, None)


def _detalle_codigo_lista(detail):
    if getattr(detail, 'analito_id', None) and detail.analito:
        return (detail.analito.codigo or detail.analito.abreviatura or '')[:30]
    if getattr(detail, 'perfil_lims_id', None):
        return f'PF{detail.perfil_lims_id}'
    if getattr(detail, 'paquete_lims_id', None):
        return f'PQ{detail.paquete_lims_id}'
    return (getattr(detail, 'descripcion_linea', '') or '?')[:30]

@login_required
def recepcion_lab(request):
    """Pantalla de recepción del laboratorio."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Tu usuario no tiene una empresa asignada. Contacta al administrador.')
        return redirect('home')

    from lims.models import Analito
    deps = sorted(
        set(
            Analito.objects.filter(activo=True).exclude(departamento='').values_list(
                'departamento', flat=True
            )
        )
    )[:80]
    categorias = [{'id': d, 'nombre': d} for d in deps]
    
    # Obtener pre-órdenes pendientes para mostrar cuando se busque un paciente
    # Esto se manejará vía AJAX cuando se seleccione un paciente
    
    return render(request, 'core/recepcion_lab.html', {
        'empresa': empresa.nombre if empresa else 'PRISLAB',
        'categorias': categorias
    })


@login_required
def dashboard_laboratorio(request):
    """
    Dashboard de laboratorio con estadísticas y lista de trabajo.
    Renderiza dashboards/dashboard_laboratorio.html con contexto completo.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Tu usuario no tiene una empresa asignada.')
        return redirect('home')

    hoy = timezone.now().date()
    inicio_dia = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))

    # Órdenes en proceso (no entregadas)
    ordenes_en_proceso = OrdenDeServicio.objects.filter(
        empresa=empresa
    ).exclude(
        estado__in=['ENTREGADO', 'CANCELADO']
    )
    muestras_pendientes = ordenes_en_proceso.count()

    # Resultados críticos: órdenes validadas pendientes de notificación/entrega
    resultados_criticos = ordenes_en_proceso.filter(estado='RESULTADOS_LISTOS').count()

    # Procesadas hoy (entregadas hoy)
    procesadas_hoy = OrdenDeServicio.objects.filter(
        empresa=empresa,
        fecha_creacion__range=(inicio_dia, timezone.now()),
        estado='ENTREGADO'
    ).count()

    # Reactivos bajos (productos con stock bajo)
    reactivos_bajos = 0
    try:
        from core.models import Producto
        reactivos_bajos = Producto.objects.filter(
            empresa=empresa,
            stock_minimo__isnull=False
        ).filter(
            Q(stock_minimo__gt=0)
        ).count()
    except Exception:
        logger.warning('Dashboard lab: error contando reactivos bajos para empresa %s', empresa, exc_info=True)

    # Muestras urgentes (órdenes STAT o prioritarias)
    muestras_urgentes = []
    try:
        for orden in ordenes_en_proceso.select_related('paciente').order_by('fecha_creacion')[:10]:
            det_qs = orden.detalles.all()[:5]
            estudios = ', '.join(detalle_orden_etiqueta(d) for d in det_qs) if det_qs else 'N/A'
            muestras_urgentes.append({
                'id': orden.id,
                'folio_orden': getattr(orden, 'folio_orden', f'ORD-{orden.id}'),
                'paciente': orden.paciente,
                'estudios': estudios or 'N/A',
                'fecha_recepcion': orden.fecha_creacion,
            })
    except Exception:
        logger.warning('Dashboard lab: error armando muestras_urgentes para empresa %s', empresa, exc_info=True)

    # Lista de trabajo (órdenes en proceso con datos para template)
    lista_trabajo = []
    for orden in ordenes_en_proceso.select_related('paciente').prefetch_related(
        'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims',
    ).order_by('fecha_creacion')[:20]:
        detalles_qs = getattr(orden, 'detalles', None)
        if detalles_qs is not None:
            estudios_solicitados = ', '.join(detalle_orden_etiqueta(d) for d in detalles_qs.all()[:5])
        else:
            estudios_solicitados = 'N/A'
        try:
            total = detalles_qs.count() if detalles_qs is not None else 0
            # Contar solo detalles que tienen resultado capturado (no vacío)
            completados = detalles_qs.exclude(
                resultado__isnull=True
            ).exclude(resultado='').count() if total else 0
            porcentaje = round(100 * completados / total, 0) if total else 0
        except Exception:
            porcentaje = 0
        lista_trabajo.append({
            'id': orden.id,
            'folio_orden': getattr(orden, 'folio_orden', f'ORD-{orden.id}'),
            'paciente': orden.paciente,
            'estado': getattr(orden, 'estado', 'EN_PROCESO'),
            'urgente': getattr(orden, 'prioridad', '') == 'STAT' or getattr(orden, 'es_urgente', False),
            'estudios_solicitados': estudios_solicitados,
            'fecha_recepcion': orden.fecha_creacion,
            'porcentaje_completado': porcentaje,
        })

    # Reactivos con stock bajo (para widget)
    reactivos_stock_bajo = []
    try:
        from core.models import Producto
        for p in Producto.objects.filter(empresa=empresa).filter(
            Q(stock_minimo__isnull=False) & Q(stock_minimo__gt=0)
        )[:10]:
            stock_actual = getattr(p, 'stock_actual', None) or sum(
                l.cantidad for l in getattr(p, 'lotes', []).all() if l.cantidad > 0
            ) if hasattr(p, 'lotes') else 0
            if stock_actual is not None and p.stock_minimo and stock_actual <= p.stock_minimo:
                reactivos_stock_bajo.append({
                    'nombre': p.nombre,
                    'cantidad_actual': stock_actual,
                    'unidad': getattr(p, 'unidad', 'pz'),
                })
    except Exception:
        logger.warning('Dashboard Lab: error cargando widget reactivos_stock_bajo', exc_info=True)

    controles_hoy = []
    try:
        controles_hoy = list(
            ControlCalidad.objects.filter(
                empresa=empresa,
                fecha_registro__range=(inicio_dia, timezone.now()),
            ).order_by('-fecha_registro')[:10]
        )
    except Exception:
        logger.warning('Dashboard Lab: error cargando controles de calidad del dia', exc_info=True)

    return render(request, 'dashboards/dashboard_laboratorio.html', {
        'empresa': empresa.nombre if hasattr(empresa, 'nombre') else str(empresa),
        'muestras_pendientes': muestras_pendientes,
        'resultados_criticos': resultados_criticos,
        'procesadas_hoy': procesadas_hoy,
        'reactivos_bajos': reactivos_bajos,
        'muestras_urgentes': muestras_urgentes,
        'lista_trabajo': lista_trabajo,
        'reactivos_stock_bajo': reactivos_stock_bajo,
        'controles_hoy': controles_hoy,
    })


@login_required
def api_buscar_estudios(request):
    """
    API: catálogo LIMS v7.5 (analitos, perfiles, paquetes).
    Cada ítem usa `id` compuesto: analito:12, perfil:3, paquete:1.
    GET /laboratorio/api/buscar-estudios/?q=gluc
    """
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)
    empresa = getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse(
            {'estudios': [], 'results': [], 'error': 'sin_empresa', 'mensaje': 'Usuario sin empresa asignada.'},
            status=403,
        )
    query = (request.GET.get('q') or request.GET.get('term') or '').strip()
    try:
        resultados = search_lims_catalog(query, empresa=empresa)
    except Exception:
        logger.error('api_buscar_estudios LIMS (query=%r)', query, exc_info=True)
        resultados = []
    return JsonResponse({'estudios': resultados, 'results': resultados})


@login_required
def api_listar_medicos(request):
    """API: lista médicos (maestro) para selección en recepción. Scoped by empresa."""
    empresa = getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)
    qs = Medico.objects.filter(empresa=empresa, activo=True).order_by("nombre_completo") if empresa else Medico.objects.none()
    termino = (request.GET.get('q') or request.GET.get('term') or '').strip()
    if termino:
        qs = qs.filter(nombre_completo__icontains=termino)
    qs = qs[:500]
    data = [
        {
            "id": m.id,
            "nombre_completo": m.nombre_completo,
            "cedula_profesional": getattr(m, 'cedula_profesional', ''),
            "especialidad": getattr(m, 'especialidad', ''),
        }
        for m in qs
    ]
    return JsonResponse({"ok": True, "medicos": data})


@login_required
def api_listar_convenios(request):
    """
    API: lista convenios activos del tenant para selección en recepción (core.Convenio).
    """
    empresa = getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({"ok": True, "convenios": [], "mensaje": "sin_empresa"})
    convenios = (
        Convenio.objects.filter(empresa=empresa, activo=True)
        .order_by("nombre")[:500]
    )
    data = [
        {
            "id": c.id,
            "nombre": c.nombre,
            "tipo": c.tipo,
            "descuento_porcentaje": float(c.descuento_porcentaje or 0),
        }
        for c in convenios
    ]
    return JsonResponse({"ok": True, "convenios": data})


@login_required
def api_precios_convenio(request, convenio_id: int):
    """
    API: devuelve mapa de precios especiales por estudio para un convenio.
    Fuente de verdad server-side para el frontend de recepción.
    """
    empresa = getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({"ok": False, "error": "Usuario sin empresa asignada"}, status=403)
    convenio = Convenio.objects.filter(
        id=convenio_id, empresa=empresa, activo=True
    ).first()

    if not convenio:
        return JsonResponse({"ok": False, "error": "Convenio no encontrado"}, status=404)

    precios = {k: float(v) for k, v in convenio_precio_map(convenio).items()}

    return JsonResponse({
        "ok": True,
        "convenio": {
            "id": convenio.id,
            "nombre": convenio.nombre,
            "tipo": convenio.tipo,
            "descuento_porcentaje": float(convenio.descuento_porcentaje or 0),
        },
        "precios": precios,
    })


@login_required
def crear_orden_servicio(request):
    """
    Endpoint de recepción unificado.

    La UI actual de laboratorio usa identificadores del catálogo LIMS
    (`analito:ID`, `perfil:ID`, `paquete:ID`). La implementación legacy de esta
    vista aún intentaba resolver contra `laboratorio.Estudio`, lo que provocaba
    fallos falsos al confirmar órdenes aunque el carrito visual sí tuviera ítems.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)

    empresa = getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)

    result = OrdenServicioLims.crear_desde_recepcion(request, empresa)
    return JsonResponse(result['body'], status=result['http_status'])

@login_required
def api_ordenes_recientes(request):
    """API para obtener las últimas órdenes del día ingresadas por el usuario actual."""
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)
    
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'success', 'ordenes': []})
    hoy = timezone.localtime(timezone.now()).date()
    
    # Obtener las últimas 10 órdenes del día creadas por el usuario actual
    ordenes = OrdenDeServicio.objects.filter(
        empresa=empresa,
        responsable_ingreso=request.user,
        fecha_creacion__date=hoy,
        deleted_at__isnull=True
    ).select_related('paciente').prefetch_related(
        'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims', 'pagos_realizados'
    ).order_by('-fecha_creacion')[:10]
    
    resultados = []
    for orden in ordenes:
        detalles_list = list(orden.detalles.all())
        num_estudios = len(detalles_list)
        estudios_nombres = [detalle_orden_etiqueta(det) for det in detalles_list[:3]]
        estudios_texto = ', '.join(estudios_nombres)
        if num_estudios > 3:
            estudios_texto += f' (+{num_estudios - 3} más)'
        
        # Estado de pago con semáforo (para Consola 360°)
        estado_pago = getattr(orden, 'estado_pago', 'PENDIENTE')
        estado_pago_colores = {
            'PENDIENTE': {'icono': '🔴', 'clase': 'danger', 'texto': 'Debe'},
            'PARCIAL': {'icono': '🟡', 'clase': 'warning', 'texto': 'Parcial'},
            'PAGADO': {'icono': '🟢', 'clase': 'success', 'texto': 'Pagado'}
        }
        estado_pago_info = estado_pago_colores.get(estado_pago, {'icono': '⚪', 'clase': 'secondary', 'texto': estado_pago})
        
        # Estado de laboratorio con semáforo
        estado_lab_colores = {
            'PENDIENTE_PAGO': {'icono': '⚪', 'clase': 'secondary', 'texto': 'Pendiente'},
            'PAGADO': {'icono': '⚪', 'clase': 'secondary', 'texto': 'Pendiente Toma'},
            'EN_PROCESO': {'icono': '🔵', 'clase': 'info', 'texto': 'Procesando'},
            'RESULTADOS_LISTOS': {'icono': '🟢', 'clase': 'success', 'texto': 'Validado'},
            'ENTREGADO': {'icono': '✅', 'clase': 'success', 'texto': 'Entregado'}
        }
        estado_lab_info = estado_lab_colores.get(orden.estado, {'icono': '⚪', 'clase': 'secondary', 'texto': orden.estado})
        
        resultados.append({
            'id': orden.id,
            'folio': orden.folio_orden or f'#{orden.id}',
            'hora': timezone.localtime(orden.fecha_creacion).strftime('%H:%M'),
            'fecha_completa': timezone.localtime(orden.fecha_creacion).strftime('%d/%m/%Y %H:%M'),
            'paciente': orden.paciente.nombre_completo if hasattr(orden.paciente, 'nombre_completo') else str(orden.paciente),
            'estudios': estudios_texto,
            'num_estudios': num_estudios,
            'estado': orden.estado,
            'estado_display': orden.get_estado_display() if hasattr(orden, 'get_estado_display') else orden.estado.replace('_', ' '),
            'estado_icono': estado_lab_info['icono'],
            'estado_pago': estado_pago,
            'estado_pago_info': estado_pago_info,
            'estado_lab_info': estado_lab_info,
            'total': float(orden.total),
            'anticipo': float(orden.anticipo),
            'saldo': float(max(orden.total - sum((p.monto_total for p in orden.pagos_realizados.all()), Decimal('0.00')), Decimal('0.00'))),
            'tipo_servicio': getattr(orden, 'tipo_servicio', 'RUTINA'),
            'es_cortesia': orden.es_cortesia
        })
    
    return JsonResponse({'status': 'success', 'ordenes': resultados})

@login_required
def imprimir_ticket_lab(request, orden_id):
    """Genera el ticket térmico de impresión para una orden de laboratorio."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return redirect('home')
    try:
        orden = OrdenDeServicio.objects.select_related('paciente', 'empresa').prefetch_related(
            'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
        ).get(id=orden_id, empresa=empresa)
    except OrdenDeServicio.DoesNotExist:
        return render(request, 'core/error.html', {
            'mensaje': 'Orden no encontrada'
        }, status=404)
    
    mayor_dias_entrega = 0
    fecha_entrega_estimada = timezone.localtime(timezone.now()) + timedelta(days=mayor_dias_entrega)
    # Ajustar a las 5:00 PM del día de entrega
    fecha_entrega_estimada = fecha_entrega_estimada.replace(hour=17, minute=0, second=0, microsecond=0)
    
    detalles = orden.detalles.select_related(
        'analito', 'perfil_lims', 'paquete_lims'
    ).all()

    # Calcular saldo pendiente
    pagado = orden.anticipo or Decimal('0.00')
    saldo_pendiente = (orden.total or Decimal('0.00')) - pagado

    # Obtener informacion de pago
    pago_info = None
    try:
        pago_info = PagoOrden.objects.filter(orden=orden).order_by('-fecha_pago').first()
    except Exception:
        pass

    return render(request, 'core/ticket_lab.html', {
        'orden': orden,
        'detalles': detalles,
        'fecha_entrega': fecha_entrega_estimada,
        'fecha_entrega_estimada': fecha_entrega_estimada,
        'pagado': pagado,
        'saldo_pendiente': saldo_pendiente,
        'pago_info': pago_info,
        'empresa': empresa,
    })

@login_required
def registro_resultados_entrada(request):
    """
    Punto de entrada inteligente para "Registro de Resultados" (estilo DevelLab).
    Carga automáticamente la primera orden con muestra lista para captura.
    Si no hay órdenes activas, redirige a la lista de trabajo completa.

    BLINDAJE P0: envuelto en try/except global — nunca devuelve 500.
    Si la orden auto-seleccionada desaparece entre la consulta y el redirect
    (race condition o acceso por URL directa a orden de otra empresa), el
    usuario recibe un mensaje claro y es llevado a la lista de trabajo.
    """
    from django.contrib import messages as _msgs
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return redirect('home')

    try:
        # ── Prioridad 1: órdenes con muestra ya recibida / en análisis ────────
        # Orden: URGENTE/STAT primero, luego por antigüedad (FEFO temporal)
        ESTADOS_CAPTURA = ['PAGADO', 'EN_PROCESO', 'MUESTRA_RECIBIDA', 'EN_ANALISIS']
        orden = (
            OrdenDeServicio.objects
            .filter(empresa=empresa, estado__in=ESTADOS_CAPTURA)
            .only('id', 'tipo_servicio', 'fecha_creacion')
            .order_by('fecha_creacion')
            .first()
        )
        if orden:
            return redirect('captura_resultados', orden_id=orden.id)

        # ── Prioridad 2: órdenes pendientes de pago (acceso anticipado) ───────
        orden_fallback = (
            OrdenDeServicio.objects
            .filter(empresa=empresa, estado='PENDIENTE_PAGO')
            .only('id', 'tipo_servicio', 'fecha_creacion')
            .order_by('fecha_creacion')
            .first()
        )
        if orden_fallback:
            return redirect('captura_resultados', orden_id=orden_fallback.id)

        # ── Sin órdenes activas ────────────────────────────────────────────────
        _msgs.info(request, 'No hay órdenes pendientes de captura en este momento.')
        return redirect('lista_trabajo_lab')

    except Exception as exc:
        logger.error(
            'registro_resultados_entrada: error inesperado para empresa=%s usuario=%s — %s',
            getattr(empresa, 'pk', '?'), request.user.username, exc, exc_info=True
        )
        _msgs.warning(
            request,
            'No se pudo cargar el Registro de Resultados automáticamente. '
            'Selecciona una orden desde la lista de trabajo.'
        )
        return redirect('lista_trabajo_lab')


@login_required
def lista_trabajo_lab(request):
    """Dashboard operativo del laboratorio (Worklist) con filtros avanzados."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return redirect('home')

    from django.utils.dateparse import parse_date

    # ── Parámetros de filtro ──────────────────────────────────────────────────
    departamento   = (request.GET.get("departamento") or "").strip()
    folio          = (request.GET.get("folio")        or "").strip()
    paciente_q     = (request.GET.get("paciente")     or "").strip()
    fecha_desde    = (request.GET.get("fecha_desde")  or "").strip()
    fecha_hasta    = (request.GET.get("fecha_hasta")  or "").strip()
    sucursal_id    = (request.GET.get("sucursal")     or "").strip()

    fecha_inicio = parse_date(fecha_desde) if fecha_desde else None
    fecha_fin    = parse_date(fecha_hasta) if fecha_hasta else None

    # ── Query base con optimización N+1 ──────────────────────────────────────
    ordenes_qs = OrdenDeServicio.objects.filter(
        empresa=empresa,
        estado__in=['PENDIENTE_PAGO', 'PAGADO', 'EN_PROCESO', 'RESULTADOS_LISTOS']
    ).exclude(
        estado='ENTREGADO'
    )

    # Filtros de búsqueda directa (DB-level)
    if folio:
        ordenes_qs = ordenes_qs.filter(folio_orden__icontains=folio)
    if paciente_q:
        ordenes_qs = ordenes_qs.filter(
            Q(paciente__nombre_completo__icontains=paciente_q)
        )
    if fecha_inicio:
        ordenes_qs = ordenes_qs.filter(fecha_creacion__date__gte=fecha_inicio)
    if fecha_fin:
        ordenes_qs = ordenes_qs.filter(fecha_creacion__date__lte=fecha_fin)
    if sucursal_id:
        try:
            ordenes_qs = ordenes_qs.filter(sucursal_id=int(sucursal_id))
        except (ValueError, TypeError):
            pass

    ordenes = ordenes_qs.annotate(
        max_dias_entrega=Value(0, output_field=IntegerField())
    ).select_related(
        'paciente', 'medico_referente', 'responsable_ingreso', 'sucursal'
    ).prefetch_related(
        'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims', 'detalles__validado_por'
    ).order_by('fecha_creacion')
    
    # v7.5: validación solo en core.OrdenDeServicio.estado (sin laboratorio.Orden)
    # Procesar cada orden para calcular urgencia y tiempo restante
    ordenes_procesadas = []
    ahora = timezone.localtime(timezone.now())

    for orden in ordenes:
        # Usar valor anotado (evita 1 query por orden)
        mayor_dias_entrega = orden.max_dias_entrega or 0
        
        fecha_creacion_local = timezone.localtime(orden.fecha_creacion)
        fecha_entrega = fecha_creacion_local + timedelta(days=mayor_dias_entrega)
        fecha_entrega = fecha_entrega.replace(hour=17, minute=0, second=0, microsecond=0)
        tiempo_restante = fecha_entrega - ahora
        
        # Determinar urgencia
        horas_restantes = tiempo_restante.total_seconds() / 3600
        if horas_restantes < 2:
            urgencia = 'URGENTE'
            icono_urgencia = '⚠️'
            clase_urgencia = 'danger'
        elif horas_restantes < 8:
            urgencia = 'PRÓXIMO'
            icono_urgencia = '🟡'
            clase_urgencia = 'warning'
        else:
            urgencia = 'A TIEMPO'
            icono_urgencia = '🟢'
            clase_urgencia = 'success'
        
        # Obtener lista breve de estudios usando la caché de prefetch (cero queries extra)
        detalles_prefetched = list(orden.detalles.all())  # usa caché prefetch
        if departamento:
            dep_lower = departamento.lower()
            detalles_prefetched = [
                d for d in detalles_prefetched
                if (
                    (d.analito_id and d.analito and dep_lower in (d.analito.departamento or '').lower())
                    or (not d.analito_id and dep_lower in (d.descripcion_linea or '').lower())
                )
            ]
            if not detalles_prefetched:
                continue

        estudios_lista = [_detalle_codigo_lista(d) for d in detalles_prefetched][:5]
        estudios_texto = ', '.join(estudios_lista)
        total_detalles_dep = len(detalles_prefetched)
        if total_detalles_dep > 5:
            estudios_texto += f"... (+{total_detalles_dep - 5} más)"

        secciones_set = set()
        for d in detalles_prefetched:
            if d.analito_id and d.analito and (d.analito.departamento or '').strip():
                secciones_set.add(d.analito.departamento.strip())
        departamentos_texto = ', '.join(sorted(secciones_set)) if secciones_set else '—'

        esta_validado = orden.estado == 'RESULTADOS_LISTOS'

        # Contar pendientes de validación usando prefetch cache (sin query extra)
        detalles_pendientes_validacion = sum(
            1 for d in orden.detalles.all()
            if getattr(d, 'estado_procesamiento', '') == 'RESULTADO_LISTO'
            and d.validado_por_id is None
        )
        tiene_resultados_pendientes = detalles_pendientes_validacion > 0
        
        ordenes_procesadas.append({
            'orden': orden,
            'fecha_entrega': fecha_entrega,
            'tiempo_restante': tiempo_restante,
            'horas_restantes': horas_restantes,
            'urgencia': urgencia,
            'icono_urgencia': icono_urgencia,
            'clase_urgencia': clase_urgencia,
            'tiene_resultados_pendientes': tiene_resultados_pendientes,
            'detalles_pendientes_count': detalles_pendientes_validacion,
            'estudios_texto': estudios_texto,
            'esta_validado': esta_validado,
            'departamentos_texto': departamentos_texto,
        })
    
    # Ordenar por urgencia (fecha de entrega más próxima primero)
    ordenes_procesadas.sort(key=lambda x: x['fecha_entrega'])
    
    # Filtros
    filtro = request.GET.get('filtro', 'todos')
    if filtro == 'urgente':
        ordenes_procesadas = [o for o in ordenes_procesadas if o['horas_restantes'] < 8]
    elif filtro == 'hoy':
        hoy = ahora.date()
        ordenes_procesadas = [o for o in ordenes_procesadas if o['fecha_entrega'].date() == hoy]
    elif filtro == 'listos':
        ordenes_procesadas = [o for o in ordenes_procesadas if o['orden'].estado == 'RESULTADOS_LISTOS']
    
    from django.core.paginator import Paginator

    departamentos = list(
        Analito.objects.filter(activo=True)
        .exclude(departamento='')
        .values_list('departamento', flat=True)
        .distinct()
        .order_by('departamento')
    )

    # Paginación defensiva — 100 órdenes por página (Punto 19)
    paginator = Paginator(ordenes_procesadas, 100)
    page_num = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_num)
    except Exception:
        page_obj = paginator.page(1)

    # Lista de sucursales para el selector de filtro
    from core.models import Sucursal
    sucursales = list(Sucursal.objects.filter(empresa=empresa, activa=True).order_by('nombre'))

    return render(request, 'core/lista_trabajo.html', {
        'ordenes': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'filtro_actual': filtro,
        'departamentos': departamentos,
        'departamento_actual': departamento,
        'empresa': empresa,
        'folio_actual': folio,
        'paciente_actual': paciente_q,
        'fecha_desde_actual': fecha_desde,
        'fecha_hasta_actual': fecha_hasta,
        'sucursal_actual': sucursal_id,
        'sucursales': sucursales,
    })


@login_required
def imprimir_hoja_trabajo_pdf(request):
    """
    GENERADOR DE HOJAS DE TRABAJO (Workflow)
    - PDF compacto filtrado por Departamento y Sucursal.
    - Agrupa analitos de forma compacta para facilitar anotación manual del químico.
    - QR dinámico que abre captura_resultados con todos los folios precargados.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return redirect('home')
    departamento = (request.GET.get("departamento") or "").strip()
    sucursal_id = request.GET.get("sucursal")
    fecha = (request.GET.get("fecha") or "").strip()

    fecha_invalida = False
    try:
        if fecha:
            from datetime import datetime as _dt
            fecha_dt = _dt.strptime(fecha, "%Y-%m-%d").date()
        else:
            fecha_dt = timezone.localtime(timezone.now()).date()
    except (ValueError, TypeError):
        logger.warning('hoja_trabajo_lab: fecha inválida recibida (%r), usando hoy', fecha)
        fecha_dt = timezone.localtime(timezone.now()).date()
        fecha_invalida = True

    qs = (
        OrdenDeServicio.objects.filter(empresa=empresa, fecha_creacion__date=fecha_dt)
        .exclude(estado="ENTREGADO")
        .select_related("paciente", "sucursal")
        .prefetch_related("detalles__analito", "detalles__perfil_lims", "detalles__paquete_lims")
        .order_by("fecha_creacion")
    )
    
    if departamento:
        qs = qs.filter(
            Q(detalles__analito__departamento__icontains=departamento)
            | Q(detalles__perfil_lims__analitos__departamento__icontains=departamento)
            | Q(detalles__paquete_lims__analitos__departamento__icontains=departamento)
            | Q(detalles__paquete_lims__perfiles__analitos__departamento__icontains=departamento)
        ).distinct()
    
    # Filtro por sucursal
    if sucursal_id:
        try:
            qs = qs.filter(sucursal_id=int(sucursal_id))
        except (ValueError, TypeError):
            pass

    ordenes = list(qs[:500])
    orden_ids = [o.id for o in ordenes]

    token = signing.dumps(
        {"ids": orden_ids, "dep": departamento or "TODOS", "suc": sucursal_id or "TODOS", "fecha": str(fecha_dt)},
        salt="worklist",
    )

    qr_url = request.build_absolute_uri(reverse("abrir_worklist_qr", args=[token]))

    # Generar QR (PNG in-memory)
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    # PDF (ReportLab) - Formato compacto con analitos agrupados
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, height - 18 * mm, f"PRISLAB v5 | HOJA DE TRABAJO")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, height - 24 * mm, f"Empresa: {empresa.nombre}")
    c.drawString(20 * mm, height - 29 * mm, f"Fecha: {fecha_dt.isoformat()}")
    c.drawString(20 * mm, height - 34 * mm, f"Departamento: {departamento or 'TODOS'}")
    if sucursal_id:
        from core.models import Sucursal
        try:
            suc = Sucursal.objects.get(id=sucursal_id, empresa=empresa)
            c.drawString(20 * mm, height - 39 * mm, f"Sucursal: {suc.nombre}")
        except Sucursal.DoesNotExist:
            pass

    # QR top-right
    c.drawImage(ImageReader(qr_buf), width - 42 * mm, height - 42 * mm, 30 * mm, 30 * mm, mask="auto")
    c.setFont("Helvetica", 8)
    c.drawRightString(width - 12 * mm, height - 44 * mm, "Escanea para abrir Captura (set de folios)")

    # Table header (formato compacto)
    y = height - 50 * mm
    c.setFont("Helvetica-Bold", 8)
    c.drawString(12 * mm, y, "FOLIO")
    c.drawString(35 * mm, y, "PACIENTE")
    c.drawString(90 * mm, y, "ANALITOS (COMPACTO)")
    c.drawString(170 * mm, y, "ESTADO")
    y -= 4 * mm
    c.line(10 * mm, y, width - 10 * mm, y)
    y -= 5 * mm

    c.setFont("Helvetica", 8)
    filas_por_pagina = 35  # Más filas por página (formato compacto)
    fila = 0

    for o in ordenes:
        if fila >= filas_por_pagina:
            c.showPage()
            width, height = letter
            y = height - 20 * mm
            c.setFont("Helvetica-Bold", 12)
            c.drawString(20 * mm, y, "PRISLAB v5 | HOJA DE TRABAJO (continuación)")
            y -= 10 * mm
            c.setFont("Helvetica-Bold", 8)
            c.drawString(12 * mm, y, "FOLIO")
            c.drawString(35 * mm, y, "PACIENTE")
            c.drawString(90 * mm, y, "ANALITOS (COMPACTO)")
            c.drawString(170 * mm, y, "ESTADO")
            y -= 4 * mm
            c.line(10 * mm, y, width - 10 * mm, y)
            y -= 5 * mm
            c.setFont("Helvetica", 8)
            fila = 0

        detalles_qs = o.detalles.select_related(
            'analito', 'perfil_lims', 'paquete_lims'
        ).all()
        if departamento:
            detalles_qs = detalles_qs.filter(analito__departamento__icontains=departamento)
        analitos = [_detalle_codigo_lista(d) for d in detalles_qs[:12]]
        analitos_txt = ", ".join(analitos)
        if detalles_qs.count() > 12:
            analitos_txt += f" (+{detalles_qs.count() - 12})"

        folio = o.folio_orden or f"ORD-{o.id}"
        paciente = (o.paciente.nombre_completo or "")[:30]

        c.drawString(12 * mm, y, folio[:14])
        c.drawString(35 * mm, y, paciente)
        c.drawString(90 * mm, y, analitos_txt[:50])
        c.drawString(170 * mm, y, o.estado[:12])

        y -= 5 * mm  # Menos espacio entre filas (compacto)
        fila += 1

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    from django.http import HttpResponse

    nombre_suc = f"_Suc{sucursal_id}" if sucursal_id else ""
    filename = f"HojaDeTrabajo_{fecha_dt.strftime('%Y%m%d')}_{(departamento or 'TODOS').replace(' ', '_')}{nombre_suc}.pdf"
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@login_required
def abrir_worklist_qr(request, token: str):
    """
    Resuelve el QR de la hoja de trabajo:
    - Verifica el token (lista de folios)
    - Abre captura industrial del primer folio y limita la lista izquierda a ese set
    """
    try:
        payload = signing.loads(token, salt="worklist", max_age=60 * 60 * 24 * 7)
        ids = payload.get("ids") or []
        ids_limpios = [int(x) for x in ids if str(x).isdigit()]
        if not ids_limpios:
            return redirect("lista_trabajo_lab")

        primer_id = ids_limpios[0]
        return redirect(f"{reverse('captura_resultados', args=[primer_id])}?worklist={token}")
    except Exception:
        return redirect("lista_trabajo_lab")

@login_required
@role_required('QUIMICO', 'ADMIN', 'LABORATORIO')
@require_http_methods(["POST"])
def api_guardar_resultados(request, orden_id):
    """API para guardar los resultados capturados de laboratorio (delega en ResultadosLimsService)."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)

    out = ResultadosLimsService.guardar_captura(request, empresa, orden_id)
    return JsonResponse(out['body'], status=out['http_status'])


@login_required
@role_required('QUIMICO', 'ADMIN', 'LABORATORIO')
@require_http_methods(['POST'])
def api_preview_formulas_lims(request, orden_id):
    """
    Previsualiza analitos es_calculado sin persistir (misma lógica que al guardar).
    Body JSON: { "overrides": { "<analito_id>": "12.5", ... } } mezclado con BD.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    try:
        orden = OrdenDeServicio.objects.get(id=orden_id, empresa=empresa)
    except OrdenDeServicio.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': f'Orden {orden_id} no encontrada'}, status=404)
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
    overrides = body.get('overrides') or {}

    detalles = DetalleOrden.objects.filter(orden=orden, analito__isnull=False).select_related('analito')
    analitos_orden = [d.analito for d in detalles]
    rps = {rp.analito_id: rp for rp in ResultadoParametro.objects.filter(orden=orden)}
    valores = {}
    for a in analitos_orden:
        sk = str(a.id)
        if sk in overrides:
            valores[a.id] = str(overrides[sk]).strip()
        else:
            valores[a.id] = (rps[a.id].valor if a.id in rps else '') or ''

    from core.services.clinical_math import sync_calculated_resultados_for_orden

    out = sync_calculated_resultados_for_orden(
        orden,
        request.user,
        accion_validar=False,
        valores_por_analito_id=valores,
        dry_run=True,
    )
    return JsonResponse({
        'status': 'success',
        'computados': out.get('computados', {}),
        'avisos': out.get('avisos', []),
    })


def generar_qr_orden(orden_id, folio_orden=None, url_verificacion=None):
    """
    Genera un código QR único para la orden de laboratorio.
    Si se provee url_verificacion, el QR apunta a esa URL pública.
    Retorna la imagen QR codificada en base64 para usar en el template.
    """
    qr_data = url_verificacion or f"ORDEN-{orden_id}-{folio_orden or orden_id}"
    
    # Crear instancia QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=4,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    # Crear imagen
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str


@login_required
def imprimir_resultados_pdf(request, orden_id):
    """Vista para imprimir resultados formales de laboratorio (documento médico)."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('lista_trabajo_lab')
    
    # Obtener el modo de impresión (membrete o digital)
    modo_impresion = request.GET.get('modo', 'digital')  # 'membrete' o 'digital'
    
    # Obtener la orden o devolver 404
    orden = get_object_or_404(
        OrdenDeServicio.objects.select_related('paciente', 'empresa', 'responsable_ingreso'),
        id=orden_id,
        empresa=empresa
    )
    
    # Triple Llave de Envío: Validar 3 condiciones antes de permitir PDF
    # 1. Saldo de la orden igual a $0.00 (orden pagada completamente)
    saldo_pendiente = orden.total - orden.anticipo
    saldo_cero = saldo_pendiente <= Decimal('0.00')
    
    # 2. Validación técnica (solo core.OrdenDeServicio)
    esta_validado = orden.estado in ('RESULTADOS_LISTOS', 'ENTREGADO')
    
    # 3. Firma de aviso de privacidad y tratamiento de datos registrada.
    from core.utils.lfpdppp_resultados import paciente_autorizado_canal_digital_resultados
    firma_privacidad = paciente_autorizado_canal_digital_resultados(orden.paciente)
    
    # ── CANDADO FINANCIERO (TRIPLE LLAVE — Saldo) ────────────────────────────
    if not saldo_cero:
        from core.utils.candado_financiero import respuesta_retenida_html
        import logging as _log
        _log.getLogger(__name__).warning(
            "CANDADO: imprimir_resultados_pdf bloqueado por saldo — orden %s usuario %s saldo $%.2f",
            orden_id, request.user.username, saldo_pendiente
        )
        return respuesta_retenida_html(saldo_pendiente, folio=orden.folio_orden or str(orden_id))
    # ─────────────────────────────────────────────────────────────────────────
    
    if not esta_validado:
        from django.contrib import messages
        messages.error(request, '❌ TRIPLE LLAVE: Esta orden no está validada por el Químico. Solo se pueden enviar órdenes validadas.')
        return redirect('captura_resultados', orden_id=orden_id)
    
    if not firma_privacidad:
        from django.contrib import messages
        messages.error(request, '❌ TRIPLE LLAVE: El paciente no tiene registrada la firma de aviso de privacidad. Se requiere verificación de teléfono para enviar resultados.')
        return redirect('captura_resultados', orden_id=orden_id)
    
    from core.services.resultados_impresion_presentacion import construir_detalles_procesados_orden

    mayor_dias_entrega = 0
    fecha_creacion_local = timezone.localtime(orden.fecha_creacion)
    fecha_entrega = fecha_creacion_local + timedelta(days=mayor_dias_entrega)
    fecha_entrega = fecha_entrega.replace(hour=17, minute=0, second=0, microsecond=0)

    detalles_procesados, ultimo_validador = construir_detalles_procesados_orden(orden)

    # Generar QR único para esta orden con URL pública de verificación
    url_base = getattr(settings, 'SITE_URL', '') or os.environ.get('SITE_URL', 'http://localhost:8000')
    url_verificacion = f"{url_base}/validar/resultado/{orden.token_acceso}/"
    qr_image_base64 = generar_qr_orden(orden_id, orden.folio_orden, url_verificacion)
    
    # Integridad forense: usar snapshot de paciente en el documento (no datos actuales)
    paciente_nombre_documento = (orden.paciente_nombre_snapshot or '').strip()
    if not paciente_nombre_documento and orden.paciente_id:
        paciente_nombre_documento = orden.paciente.nombre_completo if orden.paciente else ''
    
    # Auditoría: registro de acceso a impresión de resultados (Flow 6)
    registrar_auditoria(
        accion='PRINT',
        modelo='OrdenDeServicio',
        objeto_id=str(orden.id),
        datos_nuevos={
            'accion': 'IMPRESION_RESULTADOS_PDF',
            'folio': orden.folio_orden or str(orden.id),
            'modo': modo_impresion,
        },
        request=request,
    )

    fmeta = metadata_consentimiento_snapshot(orden.paciente) if orden.paciente_id else {}
    fmeta['vista'] = 'imprimir_resultados_pdf'
    fmeta['modo_impresion'] = modo_impresion
    registrar_acceso_forense(
        request,
        ForenseAcceso.ACCION_PDF_STAFF,
        paciente_id=orden.paciente_id,
        orden_id=orden.id,
        metadata=fmeta,
        es_publico=False,
        empresa=empresa,
    )

    if (request.GET.get('formato') or '').lower() == 'pdf':
        pdf_bytes = None
        if orden.archivo_resultado and getattr(orden.archivo_resultado, 'name', None):
            try:
                with orden.archivo_resultado.open('rb') as archivo_pdf:
                    pdf_bytes = archivo_pdf.read()
            except Exception:
                logger_core.warning(
                    'imprimir_resultados_pdf: no se pudo leer PDF almacenado, se regenerara orden=%s',
                    orden.id,
                    exc_info=True,
                )

        if pdf_bytes is None:
            from core.services.motor_reportes_lab import (
                generar_reporte_pdf,
                generar_reporte_pdf_simple,
                guardar_reporte_en_storage,
            )
            try:
                pdf_bytes = generar_reporte_pdf(orden, request=request)
            except Exception:
                logger_core.warning(
                    'imprimir_resultados_pdf: motor principal fallo, usando contingencia orden=%s',
                    orden.id,
                    exc_info=True,
                )
                pdf_bytes = generar_reporte_pdf_simple(orden, request=request)
            guardar_reporte_en_storage(orden, pdf_bytes)

        filename = f"resultados_{orden.folio_orden or orden.id}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    return render(request, 'core/resultados_print.html', {
        'orden': orden,
        'detalles': detalles_procesados,
        'paciente': orden.paciente,
        'paciente_nombre_documento': paciente_nombre_documento,
        'empresa': empresa,
        'fecha_entrega': fecha_entrega,
        'ultimo_validador': ultimo_validador,
        'fecha_impresion': timezone.localtime(timezone.now()),
        'modo_impresion': modo_impresion,
        'qr_image': qr_image_base64,
        'url_verificacion': url_verificacion,
    })

# Nota: lista_estudios y funciones de catálogo movidas a core/views/catalogos.py


@login_required
def control_calidad(request):
    """
    Dashboard de Control de Calidad (Levey-Jennings).
    Permite ingreso manual de valores de control, carga por lote,
    gráfica de Levey-Jennings y asistencia de PRIS.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')

    # POST: guardar nuevo registro de control
    if request.method == 'POST':
        try:
            with transaction.atomic():
                lote = request.POST.get('lote_control', '').strip()
                parametro_nombre = request.POST.get('parametro_nombre', '').strip()
                valor_str = request.POST.get('valor', '').strip()
                valor_esperado_str = request.POST.get('valor_esperado', '').strip()
                desviacion_str = request.POST.get('desviacion_std', '').strip()
                equipo_nombre = ''
                equipo_id = request.POST.get('equipo_id') or None
                if equipo_id:
                    try:
                        from laboratorio.models import Equipo as EquipoLab
                        eq = EquipoLab.objects.filter(id=int(equipo_id)).first()
                        equipo_nombre = str(eq) if eq else ''
                    except Exception:
                        pass
                nivel = request.POST.get('observaciones', 'Normal').strip() or 'Normal'

                valor_num = Decimal(valor_str.replace(',', '.')) if valor_str else Decimal('0')
                valor_esperado_num = Decimal(valor_esperado_str.replace(',', '.')) if valor_esperado_str else None
                # Calcular desviación vs media
                desviacion = Decimal('0')
                if valor_esperado_num:
                    desviacion = valor_num - valor_esperado_num
                elif desviacion_str:
                    desviacion = Decimal(desviacion_str.replace(',', '.'))

                ControlCalidad.objects.create(
                    empresa=empresa,
                    lote=lote or f'LOTE-{timezone.now().strftime("%Y%m%d")}',
                    parametro=parametro_nombre,
                    valor=valor_num,
                    desviacion=desviacion,
                    equipo=equipo_nombre,
                    nivel=nivel,
                )
                from django.contrib import messages
                messages.success(request, f'Control registrado: {parametro_nombre} = {valor_str}')
        except Exception as _e:
            from django.contrib import messages
            messages.error(request, f'Error al registrar: {_e}')
        return redirect('control_calidad')

    # GET: listar controles y preparar contexto para gráficas
    try:
        qs = ControlCalidad.objects.filter(empresa=empresa).order_by('-fecha_registro')[:200]
    except Exception as e:
        logger.error(f'Error en control_calidad: {e}', exc_info=True)
        qs = ControlCalidad.objects.none()

    # Preparar datos para Levey-Jennings (últimas 30 lecturas por parámetro)
    graficas_data = {}
    try:
        from django.db.models import Avg, StdDev
        parametros_en_cc = qs.values_list('parametro', flat=True).distinct()[:10]
        for param_nombre in parametros_en_cc:
            if not param_nombre:
                continue
            lecturas = ControlCalidad.objects.filter(
                empresa=empresa,
                parametro=param_nombre,
            ).order_by('fecha_registro')[:30]
            valores = []
            fechas = []
            for l in lecturas:
                try:
                    valores.append(float(l.valor))
                    fechas.append(l.fecha_registro.strftime('%d/%m'))
                except (ValueError, TypeError):
                    pass
            if valores:
                promedio = sum(valores) / len(valores)
                graficas_data[param_nombre] = {
                    'valores': valores,
                    'fechas': fechas,
                    'promedio': round(promedio, 3),
                }
    except Exception:
        pass

    # Equipos disponibles
    equipos = []
    try:
        from laboratorio.models import Equipo
        equipos = list(Equipo.objects.filter(activo=True).values('id', 'nombre', 'marca'))
    except Exception:
        pass

    parametros_lista = list(
        Analito.objects.filter(activo=True).values_list('nombre', flat=True).order_by('nombre')[:200]
    )
    analitos_cci = list(
        Analito.objects.filter(activo=True)
        .order_by('nombre')
        .values('id', 'codigo', 'nombre')[:400]
    )
    from core.services.feature_flags import flag_activo

    qc_westgard_estricto = flag_activo('QC_WESTGARD_ACTIVO', empresa)

    return render(request, 'core/control_calidad.html', {
        'empresa': empresa,
        'controles': qs,
        'graficas_data_json': json.dumps(graficas_data),
        'equipos': equipos,
        'parametros_lista_json': json.dumps(parametros_lista),
        'analitos_cci_json': json.dumps(analitos_cci),
        'qc_westgard_estricto': qc_westgard_estricto,
    })


@login_required
def toma_muestra_index(request):
    """
    Índice de toma de muestra:
    - Filtra órdenes PAGADAS que aún no tienen registro de TomaMuestra.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    from django.db.models import Exists, OuterRef
    # Usar Exists/OuterRef en lugar de hasattr para evitar el comportamiento
    # indefinido de RelatedObjectDoesNotExist en accesos OneToOne inversos.
    ordenes_pagadas = (
        OrdenDeServicio.objects
        .filter(empresa=empresa, estado="PAGADO")
        .annotate(_tiene_toma=Exists(TomaMuestra.objects.filter(orden=OuterRef('pk'))))
        .filter(_tiene_toma=False)
        .select_related("paciente")
        .order_by("-fecha_creacion")[:300]
    )
    ordenes_pendientes = list(ordenes_pagadas)

    if request.method == "POST":
        orden_id = request.POST.get("orden_id")
        orden = OrdenDeServicio.objects.filter(id=orden_id, empresa=empresa).first()
        _ya_tiene_toma = TomaMuestra.objects.filter(orden=orden).exists() if orden else True
        if orden and orden.estado == "PAGADO" and not _ya_tiene_toma:
            TomaMuestra.objects.create(
                empresa=empresa,
                sucursal=getattr(request.user, "sucursal", None),
                orden=orden,
                tomada_por=request.user,
            )
        from django.shortcuts import redirect
        return redirect("toma_muestra_index")

    return render(
        request,
        "core/toma_muestra_index.html",
        {"empresa": empresa, "ordenes": ordenes_pendientes},
    )


@login_required
@require_http_methods(["POST"])
def api_toma_muestra(request, orden_id: int):
    """API: marca toma de muestra (crea TomaMuestra) sin recargar."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({"ok": False, "error": "Usuario sin empresa asignada"}, status=403)
    orden = OrdenDeServicio.objects.filter(id=orden_id, empresa=empresa).first()
    if not orden:
        return JsonResponse({"ok": False, "error": "Orden no encontrada"}, status=404)

    if orden.estado != "PAGADO":
        return JsonResponse({"ok": False, "error": "La orden debe estar PAGADA para tomar muestra."}, status=400)

    if TomaMuestra.objects.filter(orden=orden).exists():
        return JsonResponse({"ok": True, "ya_existia": True})

    TomaMuestra.objects.create(
        empresa=empresa,
        sucursal=getattr(request.user, "sucursal", None),
        orden=orden,
        tomada_por=request.user,
    )
    return JsonResponse({"ok": True, "ya_existia": False})


@login_required
def api_validar_pin(request, orden_id: int):
    """API: valida resultados por PIN (MVP)."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({"ok": False, "error": "Usuario sin empresa asignada"}, status=403)
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        data = {}

    pin = str(data.get("pin") or "").strip()
    if not pin:
        return JsonResponse({"ok": False, "error": "PIN requerido"}, status=400)

    validation_pin = str(getattr(settings, "LAB_VALIDATION_PIN", "") or "").strip()
    if not validation_pin:
        logger_core.error(
            'api_validar_pin: LAB_VALIDATION_PIN no configurado; orden=%s usuario=%s',
            orden_id,
            getattr(request.user, 'username', 'anon'),
        )
        return JsonResponse(
            {"ok": False, "error": "PIN de validación no configurado"},
            status=503,
        )

    if pin != validation_pin:
        return JsonResponse({"ok": False, "error": "PIN incorrecto"}, status=403)

    orden = OrdenDeServicio.objects.filter(id=orden_id, empresa=empresa).first()
    if not orden:
        return JsonResponse({"ok": False, "error": "Orden no encontrada"}, status=404)

    try:
        from core.utils.candado_financiero import tiene_saldo_pendiente
        if not tiene_saldo_pendiente(orden) and not (
            orden.archivo_resultado and getattr(orden.archivo_resultado, 'name', None)
        ):
            from core.services.motor_reportes_lab import (
                generar_reporte_pdf,
                generar_reporte_pdf_simple,
                guardar_reporte_en_storage,
            )
            try:
                pdf_bytes = generar_reporte_pdf(orden, request=request)
            except Exception:
                logger_core.warning(
                    'api_validar_pin: motor PDF principal fallo, usando contingencia orden=%s',
                    orden.id,
                    exc_info=True,
                )
                pdf_bytes = generar_reporte_pdf_simple(orden, request=request)

            pdf_url = guardar_reporte_en_storage(orden, pdf_bytes)
            orden.refresh_from_db(fields=['archivo_resultado'])
            if not pdf_url and not (
                orden.archivo_resultado and getattr(orden.archivo_resultado, 'name', None)
            ):
                return JsonResponse(
                    {"ok": False, "error": "No se pudo guardar el PDF de resultados"},
                    status=500,
                )
    except Exception:
        logger_core.exception(
            'api_validar_pin: no se pudo preparar PDF antes de validar orden=%s',
            orden.id,
        )
        return JsonResponse(
            {"ok": False, "error": "No se pudo generar el PDF de resultados"},
            status=500,
        )

    orden.estado = 'RESULTADOS_LISTOS'
    try:
        OrdenDeServicio.objects.filter(id=orden.id, empresa=empresa).update(estado='RESULTADOS_LISTOS')
    except Exception:
        logger_core.exception('api_validar_pin: no se pudo marcar orden validada orden=%s', orden.id)
        return JsonResponse(
            {"ok": False, "error": "No se pudo validar la orden"},
            status=500,
        )

    try:
        registrar_auditoria(
            accion='UPDATE',
            modelo='OrdenDeServicio',
            objeto_id=str(orden.id),
            datos_nuevos={'validacion_pin': True, 'folio': orden.folio_orden or str(orden.id)},
            request=request,
        )
    except Exception:
        pass

    # WhatsApp trigger — generar enlace listo para enviar al paciente (LFPDPPP)
    whatsapp_enlace = None
    from core.utils.lfpdppp_resultados import paciente_autorizado_canal_digital_resultados

    lfpdppp_bloqueo_canal = bool(
        orden.paciente and not paciente_autorizado_canal_digital_resultados(orden.paciente)
    )
    if lfpdppp_bloqueo_canal:
        logger_core.warning(
            'api_validar_pin: WhatsApp omitido por LFPDPPP (sin consentimiento digital) orden=%s paciente=%s',
            orden.id,
            orden.paciente_id,
        )

    try:
        if orden.paciente and orden.paciente.telefono and not lfpdppp_bloqueo_canal:
            from core.utils.whatsapp_sender import enviar_whatsapp, generar_enlace_whatsapp
            empresa_nombre = getattr(empresa, 'nombre', 'PRISLAB')
            folio_display = orden.folio_orden or str(orden.id)
            nombre_pac = (orden.paciente.nombre_completo or '').split()[0] if orden.paciente.nombre_completo else 'Paciente'
            # Incluir link al PDF público si el token de acceso existe
            pdf_link = ''
            try:
                site_url = getattr(settings, 'SITE_URL', '')
                if not site_url:
                    site_url = request.build_absolute_uri('/').rstrip('/')
                if orden.token_acceso:
                    pdf_link = f'\n\n🔗 Descarga tu reporte aquí:\n{site_url}/validar/resultado/{orden.token_acceso}/'
            except Exception:
                pass
            mensaje_wa = (
                f"Hola {nombre_pac} 👋\n\n"
                f"Tus resultados de laboratorio ({folio_display}) "
                f"de *{empresa_nombre}* ya están listos y validados por nuestro equipo.{pdf_link}\n\n"
                f"¡Que te encuentres muy bien! 🧬"
            )
            # Intento de envío automático — si hay credenciales API, envía solo; si no, devuelve link
            wa_resultado = enviar_whatsapp(orden.paciente.telefono, mensaje_wa)
            if wa_resultado.get('enviado'):
                whatsapp_enlace = None  # Ya se envió — no hace falta el link manual
                logger.info(
                    'api_validar_orden_pin: WA enviado automáticamente a orden %s via %s',
                    orden.id, wa_resultado.get('canal')
                )
            else:
                whatsapp_enlace = wa_resultado.get('link') or generar_enlace_whatsapp(
                    orden.paciente.telefono, mensaje_wa
                )
    except Exception:
        pass

    wmeta = metadata_consentimiento_snapshot(orden.paciente) if orden.paciente_id else {}
    wmeta['lfpdppp_bloqueo_canal_digital'] = lfpdppp_bloqueo_canal
    wmeta['whatsapp_enlace_generado'] = bool(whatsapp_enlace)
    wmeta['validacion_pin'] = True
    registrar_acceso_forense(
        request,
        ForenseAcceso.ACCION_WHATSAPP_ENVIO,
        paciente_id=orden.paciente_id,
        orden_id=orden.id,
        metadata=wmeta,
        es_publico=False,
        empresa=empresa,
    )

    return JsonResponse({
        "ok": True,
        "whatsapp_enlace": whatsapp_enlace,
        "whatsapp_enviado_auto": whatsapp_enlace is None and not lfpdppp_bloqueo_canal,
        "lfpdppp_bloqueo_canal_digital": lfpdppp_bloqueo_canal,
    })


@login_required
def api_estado_orden(request, orden_id: int):
    """API: retorna estado resumido para refrescar filas del tablero."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({"ok": False, "error": "Usuario sin empresa asignada"}, status=403)
    orden = (
        OrdenDeServicio.objects.filter(id=orden_id, empresa=empresa)
        .select_related("paciente")
        .first()
    )
    if not orden:
        return JsonResponse({"ok": False, "error": "Orden no encontrada"}, status=404)

    tomada = hasattr(orden, "toma_muestra")
    capturada = bool(orden.detalles.filter(resultado__isnull=False).exclude(resultado="").exists())

    esta_validado = orden.estado == 'RESULTADOS_LISTOS'

    return JsonResponse(
        {
            "ok": True,
            "folio": orden.folio_orden or str(orden.id),
            "estado": orden.estado,
            "tomada": tomada,
            "capturada": capturada,
            "validada": esta_validado,
        }
    )


@login_required
def api_preordenes_pendientes(request):
    """
    API que busca si un paciente tiene pre-órdenes pendientes enviadas por el médico.
    Recibe: ?paciente_id=123
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    paciente_id = request.GET.get('paciente_id')
    if not paciente_id:
        return JsonResponse({'status': 'error', 'mensaje': 'Falta paciente_id'}, status=400)
    
    try:
        # Busca pre-órdenes PENDIENTES del paciente
        preordenes = PreOrdenLaboratorio.objects.filter(
            paciente_id=paciente_id,
            empresa=empresa,
            estado='PENDIENTE'
        ).select_related('medico_solicitante').prefetch_related(
            'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
        ).order_by('-fecha_creacion')
        
        data = []
        for p in preordenes:
            estudios = [detalle_orden_etiqueta(d) for d in p.detalles.all()]
            medico_nombre = f"{p.medico_solicitante.get_full_name()}" if p.medico_solicitante else "N/A"
            
            data.append({
                'id': p.id,
                'medico': medico_nombre,
                'fecha': timezone.localtime(p.fecha_creacion).strftime('%d/%m/%Y %H:%M'),
                'estudios': estudios,
                'observaciones': p.observaciones or "",
                'fecha_creacion': p.fecha_creacion.isoformat()
            })
        
        return JsonResponse({'status': 'success', 'preordenes': data})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@login_required
def api_cargar_preorden(request):
    """
    API para cargar los estudios de una pre-orden en el formulario de recepción.
    Recibe: POST con preorden_id
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body) if request.body else {}
        preorden_id = data.get('preorden_id')
        
        if not preorden_id:
            return JsonResponse({'status': 'error', 'mensaje': 'Falta preorden_id'}, status=400)
        
        # Buscar la pre-orden
        preorden = get_object_or_404(
            PreOrdenLaboratorio,
            id=preorden_id,
            empresa=empresa,
            estado='PENDIENTE'  # Solo cargar si está pendiente
        )
        
        detalles = preorden.detalles.select_related(
            'analito', 'perfil_lims', 'paquete_lims'
        ).all()
        estudios_ids = []
        estudios_data = []
        for d in detalles:
            row = None
            if d.analito_id:
                row = resolve_lims_line('analito', d.analito_id, empresa=empresa)
            elif d.perfil_lims_id:
                row = resolve_lims_line('perfil', d.perfil_lims_id, empresa=empresa)
            elif d.paquete_lims_id:
                row = resolve_lims_line('paquete', d.paquete_lims_id, empresa=empresa)
            if not row:
                continue
            tid = row['precio_key']
            estudios_ids.append(tid)
            codigo = ''
            nombre = row['descripcion_linea'] or ''
            if row['analito']:
                codigo = row['analito'].codigo or ''
                nombre = row['analito'].nombre
            elif row['perfil_lims']:
                nombre = row['perfil_lims'].nombre
            elif row['paquete_lims']:
                nombre = row['paquete_lims'].nombre
            estudios_data.append({
                'id': tid,
                'codigo': codigo,
                'nombre': nombre,
                'precio': float(row['precio_base']),
            })
        
        return JsonResponse({
            'status': 'success',
            'preorden_id': preorden.id,
            'estudios_ids': estudios_ids,
            'estudios': estudios_data,
            'medico': preorden.medico_solicitante.get_full_name() if preorden.medico_solicitante else "N/A",
            'observaciones': preorden.observaciones or "",
            'mensaje': f'Pre-orden cargada: {len(estudios_ids)} estudios del Dr. {preorden.medico_solicitante.get_full_name() if preorden.medico_solicitante else "N/A"}'
        })
        
    except PreOrdenLaboratorio.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Pre-orden no encontrada o ya fue procesada'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_cobrar_orden(request, orden_id):
    """
    API para cobrar una orden de laboratorio (cobro inmediato desde Recepción).
    Actualiza el anticipo y estado de pago.
    
    Entrada:
        - POST JSON: {
            'monto': Decimal (monto total a pagar),
            'monto_efectivo': Decimal (opcional, desglose multimodal),
            'monto_tarjeta': Decimal (opcional, desglose multimodal),
            'monto_transferencia': Decimal (opcional, desglose multimodal),
            'referencia_pago': str (opcional, referencia de pago)
        }
        - Requiere autenticación (@login_required)
        - Requiere método POST (@require_http_methods)
    
    Salida:
        - JSON: {
            'status': 'success' | 'error',
            'mensaje': str,
            'orden_id': int,
            'anticipo_actual': float,
            'saldo_pendiente': float,
            'estado_pago': str
        }
        - Siempre devuelve JSON, incluso en caso de error
    
    Excepciones:
        - OrdenDeServicio.DoesNotExist: Orden no encontrada (404 JSON)
        - json.JSONDecodeError: JSON inválido (400 JSON con logging)
        - ValueError: Validación de datos (400 JSON con logging)
        - Exception: Error inesperado (500 JSON con logging)
    
    Validaciones:
        - Monto debe ser mayor a cero
        - Montos multimodales deben sumar el monto total (tolerancia 1 centavo)
        - Si no se proporcionan montos multimodales, se asume todo efectivo
    
    Auditoría:
        - Registra inicio de cobro en log
        - Registra fallos en log con detalles completos
        - Crea registro PagoOrden para auditoría multimodal
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    usuario = request.user

    try:
        # Validar que el request tenga body
        if not request.body:
            return JsonResponse({'status': 'error', 'mensaje': 'No se recibieron datos'}, status=400)
        
        # Parsear JSON
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'status': 'error', 'mensaje': f'Error al procesar los datos JSON: {str(e)}'}, status=400)

        try:
            cmid_pay = parse_optional_client_mutation_uuid(data.get('client_mutation_id'))
        except ValueError:
            return JsonResponse(
                {'status': 'error', 'mensaje': 'client_mutation_id no es un UUID válido'},
                status=400,
            )

        # Obtener la orden
        try:
            orden = OrdenDeServicio.objects.select_related('paciente', 'empresa').get(id=orden_id, empresa=empresa)
        except OrdenDeServicio.DoesNotExist:
            return JsonResponse({'status': 'error', 'mensaje': 'Orden no encontrada'}, status=404)

        if cmid_pay:
            dup = PagoOrden.objects.filter(orden=orden, client_mutation_id=cmid_pay, cancelado=False).first()
            if dup:
                orden.refresh_from_db()
                return JsonResponse({
                    'status': 'success',
                    'mensaje': 'Pago ya registrado (idempotencia).',
                    'orden_id': orden.id,
                    'anticipo_actual': float(orden.anticipo),
                    'saldo_pendiente': float(orden.total - orden.anticipo),
                    'estado_pago': orden.estado_pago,
                    'idempotent_replay': True,
                }, status=200)

        # CICLO 14: Normalizar montos a 2 decimales y validar rango (evitar overflow DecimalField)
        from decimal import ROUND_HALF_UP, InvalidOperation
        _max_monto = Decimal('99999999.99')
        def _moneto(s, default=0):
            try:
                d = Decimal(str(s))
            except (InvalidOperation, TypeError):
                return Decimal(str(default))
            return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        monto_pago = _moneto(data.get('monto', 0))
        monto_efectivo = _moneto(data.get('monto_efectivo', 0))
        monto_tarjeta = _moneto(data.get('monto_tarjeta', 0))
        monto_transferencia = _moneto(data.get('monto_transferencia', 0))
        if monto_pago > _max_monto or monto_efectivo > _max_monto or monto_tarjeta > _max_monto or monto_transferencia > _max_monto:
            return JsonResponse({'status': 'error', 'mensaje': 'Algún monto excede el rango permitido (máx. 99,999,999.99)'}, status=400)
        referencia_pago = data.get('referencia_pago', '').strip() if data.get('referencia_pago') else ''
        if monto_efectivo < 0 or monto_tarjeta < 0 or monto_transferencia < 0:
            return JsonResponse({'status': 'error', 'mensaje': 'Los montos de pago no pueden ser negativos.'}, status=400)
        
        # BITÁCORA DE TRANSACCIÓN CRÍTICA: Inicio de cobro
        try:
            logger_core.info(
                f"Iniciando intento de cobro (LABORATORIO) - "
                f"Usuario: {usuario.username} (ID: {usuario.id}) - "
                f"Orden ID: {orden_id} - "
                f"Monto: ${monto_pago:.2f} - "
                f"Empresa: {empresa.nombre}"
            )
        except Exception as log_error:
            pass
        
        # Si no hay monto total pero sí hay montos multimodales, calcular el total
        if monto_pago == 0:
            monto_pago = monto_efectivo + monto_tarjeta + monto_transferencia
        
        # Validar que el monto sea mayor a cero
        if monto_pago <= 0:
            return JsonResponse({'status': 'error', 'mensaje': 'El monto debe ser mayor a cero'}, status=400)
        
        # Validar que los montos multimodales sumen correctamente (si se proporcionaron)
        suma_modos = monto_efectivo + monto_tarjeta + monto_transferencia
        if suma_modos > 0 and abs(suma_modos - monto_pago) > Decimal('0.01'):  # Tolerancia de 1 centavo
            return JsonResponse({
                'status': 'error', 
                'mensaje': f'Los montos multimodales (${suma_modos}) no coinciden con el monto total (${monto_pago})'
            }, status=400)
        
        # Si no se proporcionaron montos multimodales, asumir que todo es efectivo
        if suma_modos == 0:
            monto_efectivo = monto_pago
            monto_tarjeta = Decimal('0')
            monto_transferencia = Decimal('0')
        
        # Actualizar anticipo y estado con transacción atómica + bloqueo de fila para evitar cobro doble
        try:
            with transaction.atomic():
                orden = OrdenDeServicio.objects.select_for_update().get(id=orden_id, empresa=empresa)
                nuevo_anticipo = orden.anticipo + monto_pago

                # Determinar estado de pago
                if nuevo_anticipo >= orden.total:
                    estado_pago = 'PAGADO'
                    estado_orden = 'PAGADO'
                elif nuevo_anticipo > 0:
                    estado_pago = 'PARCIAL'
                    estado_orden = 'PENDIENTE_PAGO'
                else:
                    estado_pago = 'PENDIENTE'
                    estado_orden = 'PENDIENTE_PAGO'

                # Actualizar orden
                orden.anticipo = nuevo_anticipo
                orden.estado_pago = estado_pago
                orden.estado = estado_orden
                orden.save()

                # Registrar el pago multimodal en la base de datos para auditoría
                from contabilidad.services.cfdi_borrador_auto import (
                    crear_borrador_cfdi_desde_pago_orden,
                )

                pago_reg = PagoOrden.objects.create(
                    orden=orden,
                    monto_efectivo=monto_efectivo,
                    monto_tarjeta=monto_tarjeta,
                    monto_transferencia=monto_transferencia,
                    referencia_pago=referencia_pago if referencia_pago else None,
                    usuario_registro=request.user,
                    client_mutation_id=cmid_pay,
                )
                crear_borrador_cfdi_desde_pago_orden(pago_reg, request.user)
        except IntegrityError:
            if cmid_pay:
                dup = PagoOrden.objects.filter(
                    orden_id=orden_id, client_mutation_id=cmid_pay, cancelado=False
                ).first()
                if dup:
                    orden = OrdenDeServicio.objects.get(id=orden_id, empresa=empresa)
                    return JsonResponse({
                        'status': 'success',
                        'mensaje': 'Pago ya registrado (idempotencia).',
                        'orden_id': orden.id,
                        'anticipo_actual': float(orden.anticipo),
                        'saldo_pendiente': float(orden.total - orden.anticipo),
                        'estado_pago': orden.estado_pago,
                        'idempotent_replay': True,
                    }, status=200)
            raise

        return JsonResponse({
            'status': 'success',
            'mensaje': 'Pago registrado correctamente',
            'orden_id': orden.id,
            'anticipo_actual': float(nuevo_anticipo),
            'saldo_pendiente': float(orden.total - nuevo_anticipo),
            'estado_pago': estado_pago
        })
        
    except OrdenDeServicio.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Orden no encontrada'}, status=404)
    except json.JSONDecodeError as e:
        # BITÁCORA DE TRANSACCIÓN CRÍTICA: Fallo en cobro
        try:
            logger_core.error(
                f"FALLO EN COBRO (LABORATORIO) - "
                f"Usuario: {usuario.username} (ID: {usuario.id}) - "
                f"Orden ID: {orden_id} - "
                f"Error: JSON inválido - {str(e)} - "
                f"Empresa: {empresa.nombre}"
            )
        except Exception as log_error:
            pass
        return JsonResponse({'status': 'error', 'mensaje': f'Error al procesar los datos JSON: {str(e)}'}, status=400)
    except ValueError as e:
        # BITÁCORA DE TRANSACCIÓN CRÍTICA: Fallo en cobro
        try:
            logger_core.error(
                f"FALLO EN COBRO (LABORATORIO) - "
                f"Usuario: {usuario.username} (ID: {usuario.id}) - "
                f"Orden ID: {orden_id} - "
                f"Error: Validación - {str(e)} - "
                f"Empresa: {empresa.nombre}"
            )
        except Exception as log_error:
            pass
        return JsonResponse({'status': 'error', 'mensaje': f'Error de validación: {str(e)}'}, status=400)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        
        # BITÁCORA DE TRANSACCIÓN CRÍTICA: Fallo en cobro
        try:
            logger_core.error(
                f"FALLO EN COBRO (LABORATORIO) - "
                f"Usuario: {usuario.username} (ID: {usuario.id}) - "
                f"Orden ID: {orden_id} - "
                f"Error: {str(e)} - "
                f"Tipo: {type(e).__name__} - "
                f"Traceback: {error_details[:500]} - "
                f"Empresa: {empresa.nombre}"
            )
        except Exception as log_error:
            # Silencioso: Si el logging falla, no debe detener la operación
            pass
        
        logger_core.error(f"Error en api_cobrar_orden: {error_details}")
        return JsonResponse({
            'status': 'error', 
            'mensaje': f'Error inesperado al procesar el pago: {str(e)}',
            'detalle': error_details if settings.DEBUG else None
        }, status=500)


@login_required
def imprimir_etiquetas_lab(request, orden_id):
    """
    [DEPRECADO] Usa laboratorio.views.etiquetas.imprimir_etiqueta_tubo() en su lugar.
    
    Esta función se mantiene temporalmente por compatibilidad pero será eliminada.
    Redirige a la nueva implementación optimizada en laboratorio/views/etiquetas.py
    """
    import warnings
    from django.shortcuts import redirect
    from django.urls import reverse
    
    warnings.warn(
        "imprimir_etiquetas_lab está deprecada. Usa laboratorio.views.etiquetas.imprimir_etiqueta_tubo",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Redirigir a la nueva vista
    return redirect(reverse('imprimir_etiqueta_tubo', args=[orden_id]))


@login_required
@require_http_methods(["POST"])
def escanear_receta_ia(request):
    """
    Vista para escanear recetas médicas usando Gemini Vision API.
    Recibe una imagen y devuelve JSON con datos extraídos.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)
    try:
        # Verificar que hay API Key configurada
        if not settings.GOOGLE_API_KEY:
            return JsonResponse({
                'error': 'GOOGLE_API_KEY no configurada. Configure la variable de entorno GOOGLE_API_KEY.'
            }, status=500)
        
        # Gemini via cliente centralizado (google.genai SDK)
        
        # Obtener la imagen del request
        if 'imagen' not in request.FILES:
            return JsonResponse({'error': 'No se recibió ninguna imagen'}, status=400)
        
        imagen_file = request.FILES['imagen']
        
        # Leer la imagen
        imagen_bytes = imagen_file.read()
        
        # Preparar el prompt del sistema
        prompt_sistema = """Actúa como un asistente de laboratorio experto. Analiza esta imagen de receta médica y extrae la información en formato JSON estricto.

IMPORTANTE: Responde SOLO con un objeto JSON válido, sin texto adicional, sin markdown, sin explicaciones.

Formato requerido:
{
  "nombre_paciente": "string o 'DUDA' si no se puede leer",
  "edad": número entero o null si no se encuentra,
  "fecha_receta": "YYYY-MM-DD o 'DUDA' si no se puede leer",
  "estudios_detectados": ["lista", "de", "estudios", "encontrados"]
}

Si algún campo no se puede leer claramente, usa 'DUDA' para strings o null para números.
Para estudios_detectados, lista todos los nombres de estudios, análisis o pruebas que encuentres en la receta.
"""
        
        # Usar cliente centralizado google.genai
        from core.utils.gemini_client import get_gemini_client
        import base64
        client = get_gemini_client()

        # Codificar imagen como base64 para la API
        imagen_b64 = base64.b64encode(imagen_bytes).decode('utf-8')
        mime_type = imagen_file.content_type or 'image/jpeg'

        from google.genai import types as genai_types
        image_part = genai_types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type)

        # Generar contenido con Gemini (multimodal)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt_sistema, image_part],
        )
        
        # Extraer el texto de la respuesta
        texto_respuesta = response.text.strip()
        
        # Limpiar el texto (puede venir con markdown o código)
        if texto_respuesta.startswith('```json'):
            texto_respuesta = texto_respuesta[7:]
        if texto_respuesta.startswith('```'):
            texto_respuesta = texto_respuesta[3:]
        if texto_respuesta.endswith('```'):
            texto_respuesta = texto_respuesta[:-3]
        texto_respuesta = texto_respuesta.strip()
        
        # Parsear JSON
        try:
            datos_extraidos = json.loads(texto_respuesta)
        except json.JSONDecodeError as e:
            # Si falla el parseo, intentar extraer el JSON manualmente
            json_match = re.search(r'\{[^{}]*\}', texto_respuesta, re.DOTALL)
            if json_match:
                try:
                    datos_extraidos = json.loads(json_match.group())
                except json.JSONDecodeError:
                    return JsonResponse({
                        'error': f'Error al parsear respuesta de Gemini: {str(e)}. Respuesta recibida: {texto_respuesta[:200]}'
                    }, status=500)
            else:
                return JsonResponse({
                    'error': f'No se pudo extraer JSON de la respuesta: {texto_respuesta[:200]}'
                }, status=500)
        
        # Validar estructura básica
        estudios_detectados = datos_extraidos.get('estudios_detectados', [])
        
        # RECEPCIÓN AUTOMATIZADA: Buscar estudios en el catálogo y sugerirlos
        estudios_sugeridos = []
        if estudios_detectados:
            for nombre_estudio in estudios_detectados:
                if nombre_estudio and nombre_estudio != 'DUDA':
                    for row in search_lims_catalog(nombre_estudio, empresa=empresa, limit_analitos=3, limit_otros=2):
                        estudios_sugeridos.append({
                            'id': row.get('id'),
                            'codigo': row.get('codigo') or '',
                            'nombre': row.get('nombre') or '',
                            'precio': float(row.get('precio') or 0),
                            'indicaciones': row.get('indicaciones') or '',
                            'es_perfil': bool(row.get('es_perfil')),
                            'descripcion_interna': row.get('descripcion_interna') or '',
                            'coincidencia': nombre_estudio,
                        })
        
        # Eliminar duplicados (por ID)
        estudios_unicos = {}
        for est in estudios_sugeridos:
            if est['id'] not in estudios_unicos:
                estudios_unicos[est['id']] = est
        
        resultado = {
            'nombre_paciente': datos_extraidos.get('nombre_paciente', 'DUDA'),
            'edad': datos_extraidos.get('edad'),
            'fecha_receta': datos_extraidos.get('fecha_receta', 'DUDA'),
            'estudios_detectados': estudios_detectados,
            'estudios_sugeridos': list(estudios_unicos.values())  # Estudios del catálogo que coinciden
        }
        
        return JsonResponse({
            'exito': True,
            'datos': resultado
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'error': f'Error al procesar la receta: {str(e)}',
            'traceback': traceback.format_exc() if settings.DEBUG else None
        }, status=500)


@login_required
@require_http_methods(["POST"])
def escanear_identidad_ia(request):
    """
    RECEPCIÓN INTELIGENTE (OCR de Identidades)
    Jarvis-Vision: Lee INE/Pasaporte y devuelve JSON para autocompletar Paciente.
    """
    try:
        if not settings.GOOGLE_API_KEY:
            return JsonResponse(
                {"error": "GOOGLE_API_KEY no configurada. Configure la variable de entorno GOOGLE_API_KEY."},
                status=500,
            )

        # Control de acceso IA (solo roles operativos, y si el usuario tiene permiso)
        if not getattr(request.user, "puede_usar_ia", False):
            return JsonResponse({"error": "Acceso IA no habilitado para este usuario."}, status=403)

        # Usar cliente centralizado de Gemini Vision (API v1 estable)
        from core.utils.gemini_client import get_gemini_client, get_gemini_model

        try:
            client = get_gemini_client()
            model_name = get_gemini_model('gemini-2.0-flash')
        except Exception as e:
            return JsonResponse(
                {"error": f"Error al inicializar Gemini: {str(e)}"},
                status=500,
            )

        if "imagen" not in request.FILES:
            return JsonResponse({"error": "No se recibió ninguna imagen"}, status=400)

        imagen_file = request.FILES["imagen"]
        imagen_bytes = imagen_file.read()

        prompt_sistema = """Actúa como un asistente de recepción clínica experto. Analiza esta imagen de una identificación oficial (INE o Pasaporte) y extrae los datos en formato JSON estricto.

IMPORTANTE: Responde SOLO con un objeto JSON válido, sin texto adicional, sin markdown, sin explicaciones.

Formato requerido:
{
  "tipo_documento": "INE|PASAPORTE|OTRO|DUDA",
  "nombre_completo": "string o 'DUDA'",
  "fecha_nacimiento": "YYYY-MM-DD o 'DUDA'",
  "sexo": "M|F|DUDA",
  "curp": "string o ''",
  "numero_documento": "string o ''",
  "domicilio": "string o ''"
}

Reglas:
- Si no se puede leer con claridad, usa 'DUDA' para strings críticos (tipo_documento, nombre_completo, fecha_nacimiento, sexo).
- Para curp/numero_documento/domicilio usa '' si no se encuentra.
"""

        try:
            from PIL import Image

            Image.open(io.BytesIO(imagen_bytes)).verify()
        except Exception as e:
            return JsonResponse({"error": f"Error al procesar la imagen: {str(e)}"}, status=400)

        from google.genai import types as genai_types

        mime_type = imagen_file.content_type or "image/jpeg"
        image_part = genai_types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type)
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt_sistema, image_part],
        )
        texto_respuesta = (response.text or "").strip()

        # Limpieza defensiva (a veces viene con fences)
        if texto_respuesta.startswith("```json"):
            texto_respuesta = texto_respuesta[7:]
        if texto_respuesta.startswith("```"):
            texto_respuesta = texto_respuesta[3:]
        if texto_respuesta.endswith("```"):
            texto_respuesta = texto_respuesta[:-3]
        texto_respuesta = texto_respuesta.strip()

        try:
            datos_extraidos = json.loads(texto_respuesta)
        except json.JSONDecodeError:
            json_match = re.search(r"\{[\s\S]*\}", texto_respuesta)
            if not json_match:
                return JsonResponse({"error": f"No se pudo extraer JSON: {texto_respuesta[:200]}"}, status=500)
            datos_extraidos = json.loads(json_match.group())

        resultado = {
            "tipo_documento": (datos_extraidos.get("tipo_documento") or "DUDA"),
            "nombre_completo": (datos_extraidos.get("nombre_completo") or "DUDA"),
            "fecha_nacimiento": (datos_extraidos.get("fecha_nacimiento") or "DUDA"),
            "sexo": (datos_extraidos.get("sexo") or "DUDA"),
            "curp": (datos_extraidos.get("curp") or ""),
            "numero_documento": (datos_extraidos.get("numero_documento") or ""),
            "domicilio": (datos_extraidos.get("domicilio") or ""),
        }

        return JsonResponse({"exito": True, "datos": resultado})

    except Exception as e:
        import traceback

        return JsonResponse(
            {
                "error": f"Error al procesar la identificación: {str(e)}",
                "traceback": traceback.format_exc() if settings.DEBUG else None,
            },
            status=500,
        )


@login_required
def dashboard_pendientes(request):
    """
    DASHBOARD DE PENDIENTES: Real-time con alertas Jarvis por tiempo excedido.
    Muestra: Cultivos pendientes, folios sin validar, slides pendientes de revisión.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    ahora = timezone.now()
    
    # 1. ÓRDENES PENDIENTES DE VALIDACIÓN (Resultados listos pero no validados)
    ordenes_pendientes_validacion = OrdenDeServicio.objects.filter(
        empresa=empresa,
        estado='RESULTADOS_LISTOS'
    ).select_related('paciente', 'sucursal').order_by('-fecha_creacion')[:50]
    
    # Calcular tiempo transcurrido y alertas
    ordenes_con_alerta = []
    for orden in ordenes_pendientes_validacion:
        tiempo_transcurrido = ahora - orden.fecha_creacion
        horas_pendiente = tiempo_transcurrido.total_seconds() / 3600
        
        # Alerta roja si lleva más de 24 horas
        alerta_roja = horas_pendiente > 24
        # Alerta amarilla si lleva más de 12 horas
        alerta_amarilla = horas_pendiente > 12 and not alerta_roja
        
        ordenes_con_alerta.append({
            'orden': orden,
            'horas_pendiente': round(horas_pendiente, 1),
            'alerta_roja': alerta_roja,
            'alerta_amarilla': alerta_amarilla,
        })
    
    # 2. CULTIVOS PENDIENTES DE ENTREGA (hoy)
    from datetime import date
    # seccion es FK → filtrar por nombre del objeto relacionado, no icontains sobre FK
    cultivos_pendientes = OrdenDeServicio.objects.filter(
        empresa=empresa,
        estado__in=['EN_PROCESO', 'RESULTADOS_LISTOS'],
    ).filter(
        Q(detalles__analito__departamento__icontains='cultivo')
        | Q(detalles__analito__nombre__icontains='cultivo')
        | Q(detalles__descripcion_linea__icontains='cultivo')
    ).distinct().select_related('paciente').order_by('-fecha_creacion')[:20]
    
    # 3. FOLIOS SIN VALIDAR (detalles con resultado listo pero orden no validada)
    folios_sin_validar = DetalleOrden.objects.filter(
        orden__empresa=empresa,
        estado_procesamiento='RESULTADO_LISTO',
        orden__estado__in=['EN_PROCESO', 'RESULTADOS_LISTOS']
    ).select_related(
        'orden', 'orden__paciente', 'analito', 'perfil_lims', 'paquete_lims'
    ).order_by('-orden__fecha_creacion')[:30]
    
    # 4. SLIDES PENDIENTES DE REVISIÓN (si existe modelo de slides)
    # Nota: Ajustar según tu modelo específico de slides/microscopía
    
    # Estadísticas resumidas
    stats = {
        'total_ordenes_pendientes': len(ordenes_con_alerta),
        'ordenes_alerta_roja': sum(1 for o in ordenes_con_alerta if o['alerta_roja']),
        'ordenes_alerta_amarilla': sum(1 for o in ordenes_con_alerta if o['alerta_amarilla']),
        'cultivos_pendientes_hoy': cultivos_pendientes.count(),
        'folios_sin_validar': folios_sin_validar.count(),
    }
    
    return render(request, 'core/laboratorio/dashboard_pendientes.html', {
        'ordenes_con_alerta': ordenes_con_alerta,
        'cultivos_pendientes': cultivos_pendientes,
        'folios_sin_validar': folios_sin_validar,
        'stats': stats,
    })


@login_required
@require_http_methods(["POST"])
def api_bulk_validar(request):
    """
    Bulk-action: Valida múltiples ResultadoParametro de golpe (delega en ResultadosLimsService).
    Body JSON: {"ids": [1, 2, 3, ...]}
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa asignada'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)

    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    try:
        out = ResultadosLimsService.bulk_validar_por_ids(request, empresa, ids)
    except BusinessApiError as exc:
        return JsonResponse(
            {
                'status': 'error',
                'mensaje': exc.message,
                'codigo': exc.code,
                **exc.detail,
            },
            status=exc.status_code,
        )
    return JsonResponse(out['body'], status=out['http_status'])


@login_required
def api_bulk_imprimir(request):
    """
    Bulk-action: Retorna la URL de impresión para múltiples órdenes.
    GET: ?orden_ids=1,2,3
    Devuelve JSON con lista de URLs de PDF para que el frontend abra cada una.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa asignada'}, status=403)

    ids_raw = request.GET.get('orden_ids', '')
    try:
        ids = [int(i) for i in ids_raw.split(',') if i.strip().isdigit()]
    except ValueError:
        ids = []

    if not ids:
        return JsonResponse({'status': 'error', 'mensaje': 'No se recibieron orden_ids'}, status=400)

    # Verificar que las órdenes pertenecen a la empresa del usuario
    ordenes_validas = OrdenDeServicio.objects.filter(
        id__in=ids, empresa=empresa
    ).values_list('id', flat=True)

    urls = [
        {
            'orden_id': oid,
            'url': reverse('imprimir_resultados_pdf', args=[oid]) + '?modo=digital',
        }
        for oid in ordenes_validas
    ]

    return JsonResponse({'status': 'ok', 'urls': urls})


@login_required
def reporte_tiempos_proceso(request):
    """
    REPORTE DE TIEMPOS DE PROCESO: Muestra estudios que exceden el tiempo configurado.
    Integrado con Dashboard Pendientes para alertas en tiempo real.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    ahora = timezone.now()
    
    # Obtener todas las órdenes en proceso o con resultados listos
    ordenes_activas = OrdenDeServicio.objects.filter(
        empresa=empresa,
        estado__in=['PAGADO', 'EN_PROCESO', 'RESULTADOS_LISTOS']
    ).select_related('paciente', 'sucursal').prefetch_related(
        'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
    )
    
    estudios_excedidos = []
    
    for orden in ordenes_activas:
        tiempo_transcurrido = ahora - orden.fecha_creacion
        horas_transcurridas = tiempo_transcurrido.total_seconds() / 3600
        
        for detalle in orden.detalles.all():
            etiqueta = detalle_orden_etiqueta(detalle)
            estudio = SimpleNamespace(nombre=etiqueta)
            tiempo_proceso_estudio = '1 día'
            
            # Parsear tiempo_proceso (ej: "1 día", "2 horas", "3 días")
            horas_limite = parsear_tiempo_proceso(tiempo_proceso_estudio)
            
            if horas_limite and horas_transcurridas > horas_limite:
                # Calcular retraso
                horas_retraso = horas_transcurridas - horas_limite
                
                # Determinar nivel de alerta
                if horas_retraso > 24:
                    nivel_alerta = 'CRITICO'
                    clase_css = 'blink-critical'
                elif horas_retraso > 12:
                    nivel_alerta = 'ALTO'
                    clase_css = 'alert-danger'
                else:
                    nivel_alerta = 'MEDIO'
                    clase_css = 'alert-warning'
                
                estudios_excedidos.append({
                    'orden': orden,
                    'detalle': detalle,
                    'estudio': estudio,
                    'tiempo_configurado': tiempo_proceso_estudio,
                    'horas_limite': horas_limite,
                    'horas_transcurridas': round(horas_transcurridas, 1),
                    'horas_retraso': round(horas_retraso, 1),
                    'nivel_alerta': nivel_alerta,
                    'clase_css': clase_css,
                })
    
    # Ordenar por horas de retraso (mayor primero)
    estudios_excedidos.sort(key=lambda x: x['horas_retraso'], reverse=True)
    
    # Estadísticas
    stats = {
        'total_excedidos': len(estudios_excedidos),
        'criticos': len([e for e in estudios_excedidos if e['nivel_alerta'] == 'CRITICO']),
        'altos': len([e for e in estudios_excedidos if e['nivel_alerta'] == 'ALTO']),
        'medios': len([e for e in estudios_excedidos if e['nivel_alerta'] == 'MEDIO']),
    }
    
    return render(request, 'core/laboratorio/reporte_tiempos_proceso.html', {
        'estudios_excedidos': estudios_excedidos,
        'stats': stats,
    })


def parsear_tiempo_proceso(tiempo_str):
    """
    Parsea el string de tiempo_proceso a horas.
    Ejemplos: "1 día" -> 24, "2 horas" -> 2, "3 días" -> 72
    """
    if not tiempo_str:
        return None
    
    tiempo_str = tiempo_str.lower().strip()
    
    # Buscar días
    if 'día' in tiempo_str or 'dia' in tiempo_str:
        match = re.search(r'(\d+)', tiempo_str)
        if match:
            dias = int(match.group(1))
            return dias * 24
    
    # Buscar horas
    if 'hora' in tiempo_str:
        match = re.search(r'(\d+)', tiempo_str)
        if match:
            return int(match.group(1))
    
    # Por defecto, asumir 24 horas (1 día)
    return 24


# =============================================================================
# FASE 2-B: HISTORIAL FORENSE DE PAGOS + CANCELACIÓN
# =============================================================================

@login_required
@require_http_methods(["GET"])
def api_historial_pagos(request, orden_id):
    """Devuelve todos los pagos (activos y cancelados) de una OrdenDeServicio."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa'}, status=403)

    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    pagos = orden.pagos_realizados.select_related('usuario_registro', 'cancelado_por').all()
    resultado = []
    for p in pagos:
        resultado.append({
            'id': p.id,
            'fecha': timezone.localtime(p.fecha_pago).strftime('%d/%m/%Y %H:%M'),
            'usuario': p.usuario_registro.get_full_name() if p.usuario_registro else '—',
            'efectivo': float(p.monto_efectivo),
            'credito':  float(p.monto_credito),
            'debito':   float(p.monto_debito),
            'transferencia': float(p.monto_transferencia),
            'total': float(p.monto_bruto),
            'cancelado': p.cancelado,
            'cancelado_por': p.cancelado_por.get_full_name() if p.cancelado_por else None,
            'fecha_cancelacion': timezone.localtime(p.fecha_cancelacion).strftime('%d/%m/%Y %H:%M') if p.fecha_cancelacion else None,
            'motivo_cancelacion': p.motivo_cancelacion or '',
        })

    saldo_actual = max(
        orden.total - sum(
            Decimal(str(p.monto_bruto)) for p in pagos if not p.cancelado
        ),
        Decimal('0.00')
    )

    return JsonResponse({
        'status': 'success',
        'pagos': resultado,
        'total_orden': float(orden.total),
        'saldo_actual': float(saldo_actual),
        'anticipo_registrado': float(orden.anticipo),
    })


@login_required
@require_http_methods(["POST"])
def api_cancelar_pago(request, pago_id):
    """
    Cancela un PagoOrden y recalcula el anticipo de la OrdenDeServicio.
    Requiere rol con permiso (staff o admin).
    Después de cancelar, si el saldo > 0 el Candado Financiero se reactiva
    automáticamente (porque candado_financiero.py lee total-anticipo en tiempo real).
    """
    if not (request.user.is_staff or request.user.is_superuser or
            getattr(request.user, 'rol', '') in ['ADMIN', 'DIRECTOR', 'QUIMICO']):
        return JsonResponse({'ok': False, 'error': 'Sin permisos para cancelar pagos'}, status=403)

    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Sin empresa'}, status=403)

    try:
        pago = PagoOrden.objects.select_related('orden').get(
            id=pago_id, orden__empresa=empresa
        )
    except PagoOrden.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Pago no encontrado'}, status=404)

    if pago.cancelado:
        return JsonResponse({'ok': False, 'error': 'Este pago ya estaba cancelado'}, status=400)

    try:
        data = json.loads(request.body or '{}')
    except Exception:
        data = {}
    motivo = data.get('motivo', '').strip() or 'Sin motivo especificado'

    from django.db import transaction as _tx
    with _tx.atomic():
        pago.cancelado = True
        pago.cancelado_por = request.user
        pago.fecha_cancelacion = timezone.now()
        pago.motivo_cancelacion = motivo
        pago.save(update_fields=['cancelado', 'cancelado_por', 'fecha_cancelacion', 'motivo_cancelacion'])

        # Recalcular anticipo de la orden
        orden = pago.orden
        nuevo_anticipo = orden.pagos_realizados.filter(cancelado=False).aggregate(
            total=models.Sum(
                models.ExpressionWrapper(
                    models.F('monto_efectivo') + models.F('monto_tarjeta') + models.F('monto_transferencia'),
                    output_field=models.DecimalField()
                )
            )
        )['total'] or Decimal('0.00')

        orden.anticipo = nuevo_anticipo
        # Actualizar estado_pago
        saldo = max(orden.total - nuevo_anticipo, Decimal('0.00'))
        if saldo <= Decimal('0.01'):
            orden.estado_pago = 'PAGADO'
        elif nuevo_anticipo > 0:
            orden.estado_pago = 'PARCIAL'
        else:
            orden.estado_pago = 'PENDIENTE'
        orden.save(update_fields=['anticipo', 'estado_pago'])

    return JsonResponse({
        'ok': True,
        'mensaje': 'Pago cancelado correctamente. Saldo recalculado.',
        'nuevo_anticipo': float(nuevo_anticipo),
        'nuevo_saldo': float(saldo),
        'candado_activo': saldo > Decimal('0.01'),
    })


# =============================================================================
# FASE 4: EDICIÓN DUAL — DATOS GENERALES + ESTUDIOS
# =============================================================================

@login_required
@require_http_methods(["GET"])
def api_datos_orden(request, orden_id):
    """Devuelve los datos completos de una orden para el panel de edición."""
    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(
        OrdenDeServicio.objects.select_related('paciente', 'medico_referente')
                               .prefetch_related(
                                   'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
                               ),
        id=orden_id, empresa=empresa
    )
    estudios = []
    for d in orden.detalles.all():
        k = _lims_line_key_detalle(d)
        if k[0] is None:
            tid = f'legacy:{d.id}'
            estudios.append({
                'id': tid,
                'nombre': (d.descripcion_linea or 'Estudio legacy')[:300],
                'codigo': _detalle_codigo_lista(d),
                'precio': float(d.precio_momento or 0),
                'legacy': True,
            })
            continue
        tid = f'{k[0]}:{k[1]}'
        estudios.append({
            'id': tid,
            'nombre': detalle_orden_etiqueta(d),
            'codigo': _detalle_codigo_lista(d),
            'precio': float(d.precio_momento or 0),
        })
    return JsonResponse({
        'status': 'success',
        'orden': {
            'id': orden.id,
            'folio': orden.folio_orden or f'#{orden.id}',
            'paciente': orden.paciente.nombre_completo,
            'tipo_servicio': orden.tipo_servicio,
            'diagnostico': orden.diagnostico or '',
            'notas_internas': orden.notas_internas or '',
            'requiere_factura': orden.requiere_factura,
            'medico_id': orden.medico_referente_id,
            'medico_nombre': orden.medico_referente.nombre_completo if orden.medico_referente else '',
            'estudios': estudios,
            'total': float(orden.total),
            'anticipo': float(orden.anticipo),
            'saldo': float(max(orden.total - orden.anticipo, Decimal('0.00'))),
            'estado': orden.estado,
        }
    })


@login_required
@require_http_methods(["POST"])
def api_editar_datos_orden(request, orden_id):
    """
    Edición de Datos Generales (no financieros).
    Permite cambiar: médico, diagnóstico, notas, tipo_servicio, req_factura.
    NO recalcula el total ni afecta el saldo.
    """
    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    try:
        data = json.loads(request.body or '{}')
    except Exception:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    # Solo campos no financieros
    campos_actualizados = []
    if 'tipo_servicio' in data:
        orden.tipo_servicio = data['tipo_servicio']
        campos_actualizados.append('tipo_servicio')
    if 'diagnostico' in data:
        orden.diagnostico = data['diagnostico'] or None
        campos_actualizados.append('diagnostico')
    if 'notas_internas' in data:
        orden.notas_internas = data['notas_internas'] or None
        campos_actualizados.append('notas_internas')
    if 'requiere_factura' in data:
        orden.requiere_factura = bool(data['requiere_factura'])
        campos_actualizados.append('requiere_factura')
    if 'medico_id' in data:
        try:
            from core.models import Medico
            medico = Medico.objects.get(id=data['medico_id'], empresa=empresa) if data['medico_id'] else None
            orden.medico_referente = medico
            campos_actualizados.append('medico_referente')
        except Exception:
            pass

    if campos_actualizados:
        orden.save(update_fields=campos_actualizados)

    return JsonResponse({
        'ok': True,
        'mensaje': 'Datos de la orden actualizados correctamente.',
        'campos_actualizados': campos_actualizados,
    })


@login_required
@require_http_methods(["POST"])
def api_editar_estudios_orden(request, orden_id):
    """
    Edición de líneas LIMS (financiero).
    Elimina detalles sin resultado, conserva los que ya tienen captura y agrega
    líneas nuevas del carrito LIMS. Recalcula total y estado de pago.
    """
    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(
        OrdenDeServicio.objects.prefetch_related(
            'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
        ),
        id=orden_id, empresa=empresa
    )

    try:
        data = json.loads(request.body or '{}')
    except Exception:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    raw = data.get('estudio_ids') or data.get('lims_lineas') or []
    if isinstance(raw, (str, int)):
        raw = [raw]
    raw = [str(x).strip() for x in raw if str(x).strip()]

    legacy_detail_ids = set()
    lims_ids = []
    for item in raw:
        if item.startswith('legacy:'):
            try:
                legacy_detail_ids.add(int(item.split(':', 1)[1]))
            except (TypeError, ValueError):
                continue
        else:
            lims_ids.append(item)

    lineas = resolve_lims_cart_ids(lims_ids, empresa=empresa)
    if not lineas and not legacy_detail_ids:
        return JsonResponse(
            {'ok': False, 'error': 'Debe incluir al menos una línea de catálogo LIMS válida'},
            status=400,
        )

    convenio = _convenio_desde_tarifa(orden, empresa)
    precios_especiales = convenio_precio_map(convenio) if convenio else {}
    descuento_pct = (
        Decimal(str(convenio.descuento_porcentaje or 0)) if convenio else Decimal('0')
    )

    from django.db import transaction as _tx

    with _tx.atomic():
        orden = OrdenDeServicio.objects.select_for_update().get(id=orden_id, empresa=empresa)
        detalles_actuales = DetalleOrden.objects.filter(orden=orden)
        eliminables = detalles_actuales.filter(Q(resultado__isnull=True) | Q(resultado=''))
        if legacy_detail_ids:
            eliminables = eliminables.exclude(id__in=legacy_detail_ids)
        eliminables.delete()
        preserved = list(
            DetalleOrden.objects.filter(orden=orden).select_related(
                'analito', 'perfil_lims', 'paquete_lims'
            )
        )
        nuevo_total = sum((d.precio_momento for d in preserved), Decimal('0.00'))
        existing_keys = {_lims_line_key_detalle(d) for d in preserved}

        for row in lineas:
            k = _lims_line_key_row(row)
            if k[0] is None or k in existing_keys:
                continue
            precio_momento = aplicar_precio_convenio(
                row['precio_base'], row['precio_key'], precios_especiales, descuento_pct
            )
            desc = (row.get('descripcion_linea') or '')[:300]
            DetalleOrden.objects.create(
                orden=orden,
                analito=row['analito'],
                perfil_lims=row['perfil_lims'],
                paquete_lims=row['paquete_lims'],
                descripcion_linea=desc,
                precio_momento=precio_momento,
            )
            existing_keys.add(k)
            nuevo_total += precio_momento

        orden.total = nuevo_total
        saldo = max(nuevo_total - orden.anticipo, Decimal('0.00'))
        if saldo <= Decimal('0.01'):
            orden.estado_pago = 'PAGADO'
        elif orden.anticipo > 0:
            orden.estado_pago = 'PARCIAL'
        else:
            orden.estado_pago = 'PENDIENTE'
        orden.save(update_fields=['total', 'estado_pago'])

    return JsonResponse({
        'ok': True,
        'mensaje': 'Líneas LIMS actualizadas. El total ha sido recalculado.',
        'nuevo_total': float(nuevo_total),
        'anticipo': float(orden.anticipo),
        'nuevo_saldo': float(saldo),
        'candado_activo': saldo > Decimal('0.01'),
        'alerta_saldo': (
            f'El total ha cambiado. Se requiere cubrir el nuevo saldo de '
            f'${saldo:.2f} para liberar resultados.'
            if saldo > Decimal('0.01') else None
        ),
    })


# ─────────────────────────────────────────────────────────────────────────────
# HISTORIAL DE PACIENTE — CONTEXTO LABORATORIO
# Solo muestra datos de laboratorio: visitas, órdenes y resultados de estudios.
# No expone historia clínica, consultas médicas ni notas SOAP (eso es Consultorio).
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# FLUJO TOMA DE MUESTRA — CUBÍCULO (Preparación + Extracción + Audio PRIS)
# ─────────────────────────────────────────────────────────────────────────────

# Orden estándar de extracción por color de tubo (NOM-007 / CLSI GP41)
ORDEN_EXTRACCION_TUBOS = ['AZUL', 'AMARILLO', 'ROJO', 'VERDE', 'MORADO', 'GRIS', 'NEGRO']

TUBO_INFO = {
    'ROJO':    {'label': 'Rojo',    'subtitulo': 'Suero',       'hex': '#e53935'},
    'MORADO':  {'label': 'Morado',  'subtitulo': 'EDTA',        'hex': '#8e24aa'},
    'AZUL':    {'label': 'Azul',    'subtitulo': 'Citrato Na',   'hex': '#1e88e5'},
    'VERDE':   {'label': 'Verde',   'subtitulo': 'Heparina Li',  'hex': '#43a047'},
    'GRIS':    {'label': 'Gris',    'subtitulo': 'Fluoruro Na',  'hex': '#757575'},
    'AMARILLO':{'label': 'Amarillo','subtitulo': 'Gel/Suero',    'hex': '#f9a825'},
    'NEGRO':   {'label': 'Negro',   'subtitulo': 'VSG/ESR',      'hex': '#212121'},
}


@login_required
def preparacion_toma(request, orden_id):
    """
    Consola de trabajo del flebotomista antes de iniciar la extracción.
    Muestra: datos del paciente, guía visual de tubos, checklist de seguridad.
    Al pulsar INICIAR TOMA el frontend llama api_iniciar_toma vía fetch.
    """
    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    # Verificar que la orden aún es elegible (PAGADO o ya en extracción)
    if orden.estado not in ('PAGADO',) and orden.estado_clinico not in ('PENDIENTE_TOMA', 'EN_EXTRACCION'):
        from django.contrib import messages as _msg
        _msg.warning(request, 'Esta orden ya no está en estado de toma de muestra.')
        return redirect('toma_muestra_index')

    detalles = (
        orden.detalles
        .select_related('analito', 'perfil_lims', 'paquete_lims')
        .filter(estado_procesamiento='PENDIENTE_TOMA')
    )

    tubos_dict = {}
    for det in detalles:
        color = 'ROJO'
        if color not in tubos_dict:
            tubos_dict[color] = {
                **TUBO_INFO.get(color, {'label': color, 'subtitulo': '', 'hex': '#9e9e9e'}),
                'color': color,
                'estudios': [],
            }
        tubos_dict[color]['estudios'].append(detalle_orden_etiqueta(det))

    # Ordenar tubos según estándar CLSI
    tubos_guia = sorted(
        tubos_dict.values(),
        key=lambda t: ORDEN_EXTRACCION_TUBOS.index(t['color'])
        if t['color'] in ORDEN_EXTRACCION_TUBOS else 99
    )

    # Estado actual de la toma (si ya se inició en sesión previa)
    toma_existente = getattr(orden, 'toma_muestra', None)
    ya_iniciada = (
        toma_existente is not None and
        toma_existente.hora_inicio_extraccion is not None and
        toma_existente.hora_fin_extraccion is None
    )

    # Verificar si hay consentimiento firmado
    consentimiento_firmado = False
    try:
        from core.models import ConsentimientoInformado
        consentimiento_firmado = ConsentimientoInformado.objects.filter(
            orden=orden, firmado=True
        ).exists()
    except Exception:
        pass

    return render(request, 'core/preparacion_toma.html', {
        'orden': orden,
        'paciente': orden.paciente,
        'tubos_guia': tubos_guia,
        'detalles': detalles,
        'ya_iniciada': ya_iniciada,
        'toma': toma_existente,
        'consentimiento_firmado': consentimiento_firmado,
    })


@login_required
@require_http_methods(["POST"])
def api_iniciar_toma(request, orden_id):
    """
    Marca el inicio de la extracción:
    - Crea o recupera el registro TomaMuestra
    - Registra hora_inicio_extraccion
    - Cambia estado_clinico → EN_EXTRACCION
    - Devuelve timestamp para el cronómetro frontend
    """
    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        data = {}

    identidad = data.get('identidad_verificada', False)
    ayuno = data.get('ayuno_confirmado', False)
    consentimiento = data.get('consentimiento_firmado', False)

    with transaction.atomic():
        toma, _ = TomaMuestra.objects.get_or_create(
            orden=orden,
            defaults={
                'empresa': empresa,
                'sucursal': getattr(request.user, 'sucursal', None),
                'tomada_por': request.user,
            }
        )
        ahora = timezone.now()
        toma.hora_inicio_extraccion = ahora
        toma.hora_fin_extraccion = None
        toma.identidad_verificada = identidad
        toma.ayuno_confirmado = ayuno
        toma.consentimiento_firmado = consentimiento
        toma.save(update_fields=[
            'hora_inicio_extraccion', 'hora_fin_extraccion',
            'identidad_verificada', 'ayuno_confirmado', 'consentimiento_firmado',
        ])

        orden.estado_clinico = 'EN_EXTRACCION'
        orden.save(update_fields=['estado_clinico'])

    logger.info("TOMA INICIADA orden=%s usuario=%s", orden_id, request.user.username)

    return JsonResponse({
        'ok': True,
        'toma_id': toma.id,
        'timestamp_inicio': ahora.isoformat(),
    })


@login_required
@require_http_methods(["POST"])
def api_finalizar_toma(request, orden_id):
    """
    Cierra la sesión de extracción:
    - Registra hora_fin_extraccion y duracion
    - Guarda audio cifrado (si se envió como base64)
    - Guarda transcripción / notas PRIS
    - Cambia estado_clinico → TOMA_REALIZADA
    - Cambia estado_procesamiento de detalles → TOMA_REALIZADA
    """
    from core.models import AudioTomaMuestra
    import hashlib, base64

    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'ok': False, 'error': 'Cuerpo JSON inválido'}, status=400)

    audio_b64 = data.get('audio_b64', '')       # base64 del audio WebM
    transcripcion = data.get('transcripcion', '')
    notas_ia = data.get('notas_ia', '')
    checklist_final = data.get('checklist_final') or {}

    toma = getattr(orden, 'toma_muestra', None)
    if not toma:
        return JsonResponse({'ok': False, 'error': 'No existe registro de inicio de toma'}, status=400)

    ahora = timezone.now()
    duracion = 0
    if toma.hora_inicio_extraccion:
        duracion = int((ahora - toma.hora_inicio_extraccion).total_seconds())

    with transaction.atomic():
        toma.hora_fin_extraccion = ahora
        toma.duracion_extraccion_seg = duracion
        toma.notas_ia = notas_ia or transcripcion
        # Sincronizar checklist de seguridad con el cierre (fuente de verdad: sesión completa)
        if checklist_final:
            toma.identidad_verificada = bool(checklist_final.get('IDENTIDAD', toma.identidad_verificada))
            toma.ayuno_confirmado = bool(checklist_final.get('AYUNO', toma.ayuno_confirmado))
            toma.consentimiento_firmado = bool(checklist_final.get('CONSENTIMIENTO', toma.consentimiento_firmado))
        toma.save(update_fields=[
            'hora_fin_extraccion', 'duracion_extraccion_seg', 'notas_ia',
            'identidad_verificada', 'ayuno_confirmado', 'consentimiento_firmado',
        ])

        # Cifrar y guardar audio si fue enviado
        if audio_b64:
            try:
                audio_bytes = base64.b64decode(audio_b64)
                sha = hashlib.sha256(audio_bytes).hexdigest()

                # Cifrado Fernet si FERNET_KEY está configurada
                cifrado = audio_bytes  # fallback: sin cifrar
                try:
                    from cryptography.fernet import Fernet
                    from django.conf import settings as _cfg
                    fernet_key = getattr(_cfg, 'FERNET_KEY', None)
                    if fernet_key:
                        f = Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
                        cifrado = f.encrypt(audio_bytes)
                except Exception as e_fernet:
                    logger.warning("Fernet no disponible para audio toma: %s", e_fernet)

                audio_rec, _ = AudioTomaMuestra.objects.get_or_create(toma=toma)
                audio_rec.audio_cifrado = cifrado
                audio_rec.hash_sha256 = sha
                audio_rec.duracion_segundos = duracion
                audio_rec.transcripcion_ia = transcripcion
                audio_rec.timestamp_inicio = toma.hora_inicio_extraccion
                audio_rec.timestamp_fin = ahora
                audio_rec.ip_origen = request.META.get('REMOTE_ADDR', '')
                audio_rec.save()
            except Exception as e_audio:
                logger.error("Error guardando audio toma orden=%s: %s", orden_id, e_audio)

        # Actualizar estado clínico de la orden
        orden.estado_clinico = 'TOMA_REALIZADA'
        orden.fecha_toma_muestra = ahora
        orden.usuario_tomo_muestra = request.user
        orden.save(update_fields=['estado_clinico', 'fecha_toma_muestra', 'usuario_tomo_muestra'])

        # Actualizar detalles pendientes
        orden.detalles.filter(estado_procesamiento='PENDIENTE_TOMA').update(
            estado_procesamiento='TOMA_REALIZADA'
        )

    logger.info("TOMA FINALIZADA orden=%s duracion=%ss usuario=%s", orden_id, duracion, request.user.username)

    return JsonResponse({
        'ok': True,
        'duracion_segundos': duracion,
        'redirect_url': f'/laboratorio/lista-trabajo/',
    })


@login_required
def lista_pacientes_lab(request):
    """
    Listado de pacientes filtrado al contexto de Laboratorio.
    El link de cada paciente va al historial de estudios (no al expediente clínico).
    Acceso: roles LABORATORIO, RECEPCION, QUIMICO, Superusuario.
    """
    empresa = getattr(request.user, 'empresa', None)
    query = request.GET.get('q', '').strip()

    qs = Paciente.objects.filter(empresa=empresa, activo=True).order_by('nombre_completo')
    if query:
        qs = qs.filter(
            Q(nombre_completo__icontains=query) |
            Q(telefono__icontains=query) |
            Q(curp__icontains=query)
        )

    from django.core.paginator import Paginator
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'core/lab_pacientes/lista.html', {
        'pacientes': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'query': query,
    })


@login_required
def historial_lab_paciente(request, paciente_id):
    """
    Historial de laboratorio de un paciente: visitas, órdenes y resultados.
    EXCLUSIVO contexto laboratorio — sin historia clínica ni consultas médicas.
    Acceso: roles LABORATORIO, RECEPCION, QUIMICO, MEDICO (como referencia), Superusuario.
    """
    empresa = getattr(request.user, 'empresa', None)
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

    # Todas las órdenes del paciente ordenadas por fecha descendente
    ordenes = (
        OrdenDeServicio.objects
        .filter(paciente=paciente, empresa=empresa)
        .prefetch_related('detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims')
        .order_by('-fecha_creacion')
    )

    total_visitas = ordenes.count()
    ultima_visita = ordenes.first()

    from collections import Counter

    _det_labels = []
    for d in DetalleOrden.objects.filter(
        orden__paciente=paciente, orden__empresa=empresa
    ).select_related('analito', 'perfil_lims', 'paquete_lims')[:800]:
        lab = detalle_orden_etiqueta(d).strip()
        if lab:
            _det_labels.append(lab)
    estudios_frecuentes = [
        {'linea_label': lab, 'veces': n}
        for lab, n in Counter(_det_labels).most_common(5)
    ]

    return render(request, 'core/lab_pacientes/historial.html', {
        'paciente': paciente,
        'ordenes': ordenes[:50],   # Últimas 50 órdenes
        'total_visitas': total_visitas,
        'ultima_visita': ultima_visita,
        'estudios_frecuentes': estudios_frecuentes,
    })
