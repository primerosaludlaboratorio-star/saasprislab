"""
Recepción, dashboard, APIs de búsqueda/catálogo, creación de orden.
"""
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q

from core.models import (
    Empresa, Paciente, OrdenDeServicio,
    DetalleOrden, Medico, Convenio, PagoOrden,
)
from core.lims_cart import (
    convenio_precio_map,
    detalle_orden_etiqueta,
    search_lims_catalog,
)
from core.services.lims import OrdenServicioLims
from lims.models import Analito

from ._helpers import _detalle_codigo_lista

logger = logging.getLogger('core')


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
            Analito.objects.filter(empresa=empresa, activo=True).exclude(departamento='').values_list(
                'departamento', flat=True
            )
        )
    )[:80]
    categorias = [{'id': d, 'nombre': d} for d in deps]

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
    except (ImportError, AttributeError, LookupError):
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
    except (AttributeError, ValueError):
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
        except (ValueError, ZeroDivisionError, AttributeError):
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
    except (ImportError, AttributeError):
        logger.warning('Dashboard Lab: error cargando widget reactivos_stock_bajo', exc_info=True)

    controles_hoy = []
    try:
        from core.models import ControlCalidad
        controles_hoy = list(
            ControlCalidad.objects.filter(
                empresa=empresa,
                fecha_registro__range=(inicio_dia, timezone.now()),
            ).order_by('-fecha_registro')[:10]
        )
    except (ImportError, AttributeError):
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
    except (ImportError, AttributeError, LookupError, ValueError, TypeError):
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
