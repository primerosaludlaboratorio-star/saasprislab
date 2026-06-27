"""
Punto de entrada de captura, lista de trabajo, guardado, preview, bulk actions.
"""
import json
import logging
from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Value, IntegerField

from core.models import (
    OrdenDeServicio, DetalleOrden, ResultadoParametro,
)
from core.decorators import role_required
from core.api_contracts.errors import BusinessApiError
from core.services.lims import ResultadosLimsService
from lims.models import Analito

from ._helpers import _detalle_codigo_lista

logger = logging.getLogger('core')


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
        # CONSERVADO INTENCIONALMENTE — Blindaje P0 del endpoint de entrada de resultados.
        # Captura cualquier fallo inesperado (ORM, render, middleware) para garantizar
        # que el operador nunca reciba un 500 durante captura de resultados clínicos.
        # Equivalente al handler de último recurso en pris_ia/views.py L204.
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
    except (EmptyPage, PageNotInteger):
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

    from django.urls import reverse
    urls = [
        {
            'orden_id': oid,
            'url': reverse('imprimir_resultados_pdf', args=[oid]) + '?modo=digital',
        }
        for oid in ordenes_validas
    ]

    return JsonResponse({'status': 'ok', 'urls': urls})
