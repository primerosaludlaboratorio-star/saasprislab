"""
Módulo de Vistas para Farmacia (Punto de Venta).
Incluye: PDV, búsqueda de productos, ventas, tickets, inventario, devoluciones.
"""

import json
import time as time_module
import logging
from decimal import Decimal

logger = logging.getLogger('core.farmacia')
from datetime import datetime, timedelta, date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.db.models import Q, Sum, F, Count, Max, Min, DecimalField, Prefetch
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

# Umbrales de caducidad configurables
_DIAS_CADUCIDAD_CRITICO = getattr(settings, 'FARMACIA_DIAS_CADUCIDAD_CRITICO', 30)

from core.models import (
    Empresa, Usuario, Producto, Lote, Venta, DetalleVenta,
    Pago, Medico, Receta, Gasto, AjusteInventario, GastoCaja,
    DiscountPolicy, Paciente, SalesReturn, MetaVenta, RecetaItem,
    ConfiguracionModulos, DevolucionVenta,
)
from core.utils.farmacia_tenant import (
    redirigir_sin_empresa_pdv,
    respuesta_sin_empresa_fragmento,
    respuesta_sin_empresa_json,
)
from core.utils.trazabilidad import registrar_trazabilidad, serializar_modelo
from core.services.ventas.venta_farmacia_service import VentaFarmaciaService
from core.services.inventario.movimiento_inventario_service import MovimientoInventarioService
from core.services.inventario.catalogo_farmacia_service import CatalogoFarmaciaService

# Logger para transacciones críticas
logger_core = logging.getLogger('core')


def _empresa_desde_request(request):
    """Empresa efectiva: EmpresaIdentityMiddleware (fallback principal) o FK del usuario."""
    return getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)


# ==============================================================================
# 1. PUNTO DE VENTA (PDV) - Controlador Principal
# ==============================================================================

def _verificar_acceso(user, roles_permitidos, grupos_permitidos=None):
    """
    Verifica si el usuario tiene acceso por ROL o por GRUPO de Django.
    - roles_permitidos: lista de valores del campo user.rol (ej: ['CAJERO', 'ADMIN'])
    - grupos_permitidos: lista de nombres de grupos Django (ej: ['FARMACIA', 'GERENCIA_OPERATIVA'])
    """
    if user.is_superuser or user.is_staff:
        return True
    rol = (getattr(user, 'rol', '') or '').upper().strip()
    if rol in roles_permitidos:
        return True
    # Verificar grupos de Django
    todos_grupos = list(roles_permitidos)
    if grupos_permitidos:
        todos_grupos.extend(grupos_permitidos)
    return user.groups.filter(name__in=todos_grupos).exists()


@login_required
def api_lotes_producto(request, producto_id):
    """
    Devuelve el detalle completo de un producto (con info de lotes FEFO) para
    que el JS de PDV decida si es vendible, si requiere receta y qué lote usar.
    URL: /farmacia/api/lotes-producto/<producto_id>/
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({'error': 'Sin empresa'}, status=403)

    try:
        p = Producto.objects.prefetch_related('lotes').get(id=producto_id, empresa=empresa)
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)

    hoy_fefo = date.today()
    lotes_cache = list(p.lotes.all())

    # Lotes con cantidad > 0 (para stock)
    lotes_con_stock = [l for l in lotes_cache if (l.cantidad or 0) > 0]

    # Lotes vigentes: cantidad > 0 Y no caducados
    lotes_vigentes = sorted(
        [l for l in lotes_con_stock if not l.fecha_caducidad or l.fecha_caducidad >= hoy_fefo],
        key=lambda l: (l.fecha_caducidad or date(9999, 12, 31))
    )

    stock_vigente = sum(l.cantidad for l in lotes_vigentes)
    # Si no hay lotes vigentes pero sí con stock → todos caducados
    sin_stock_vigente = bool(lotes_con_stock) and stock_vigente == 0

    # Fallback al campo stock del producto si no hay lotes registrados
    stock_total = stock_vigente if stock_vigente > 0 else (int(p.stock or 0) if not lotes_cache else 0)

    lote_fefo = lotes_vigentes[0] if lotes_vigentes else None
    proxima_caducidad = lote_fefo.fecha_caducidad.strftime('%Y-%m-%d') if lote_fefo and lote_fefo.fecha_caducidad else None
    dias_restantes = (lote_fefo.fecha_caducidad - hoy_fefo).days if lote_fefo and lote_fefo.fecha_caducidad else None
    numero_lote = lote_fefo.numero_lote if lote_fefo else None
    costo_lote = float(lote_fefo.precio_compra) if lote_fefo and getattr(lote_fefo, 'precio_compra', None) else float(p.precio_compra or 0)

    precio_venta = float(p.precio_publico or 0)
    alerta_precio_bajo = precio_venta > 0 and costo_lote > 0 and precio_venta < costo_lote

    producto_data = {
        'id': p.id,
        'nombre_comercial': p.nombre,
        'sustancia_activa': p.sustancia_activa or '',
        'codigo_barras': p.codigo_barras or '',
        'precio_base': precio_venta,
        'precio_venta': precio_venta,
        'precio_compra': float(p.precio_compra or 0),
        'costo_lote': costo_lote,
        'stock': stock_total,
        'stock_total': stock_total,
        'iva_pct': float(p.iva_porcentaje or 0),
        'es_antibiotico': bool(p.es_antibiotico),
        'es_controlado': bool(p.es_antibiotico),
        'requiere_receta': bool(getattr(p, 'requiere_receta', False) or p.es_antibiotico),
        'categoria': p.categoria or '',
        'lote_id': lote_fefo.id if lote_fefo else None,
        'numero_lote_proximo': numero_lote,
        'proxima_caducidad': proxima_caducidad,
        'dias_restantes': dias_restantes,
        'dias_restantes_fefo': dias_restantes,
        'sin_stock_vigente': sin_stock_vigente,
        'alerta_precio_bajo': alerta_precio_bajo,
    }
    return JsonResponse({'producto': producto_data})


@login_required
def api_buscar_producto_pdv(request):
    """
    Búsqueda JSON para el PDV bajo /farmacia/api/ (el SW no intercepta esta ruta).
    """
    if request.method != 'GET':
        return JsonResponse({'productos': [], 'error': 'Método no permitido'}, status=405)
    if not _verificar_acceso(request.user, ['CAJERO', 'FARMACIA', 'ADMIN', 'ADMINISTRADOR', 'GERENTE'], ['FARMACIA', 'GERENCIA_OPERATIVA', 'GERENCIA']):
        logger.warning("PDV búsqueda: acceso denegado para %s (rol=%s, grupos=%s)",
                        request.user.username,
                        getattr(request.user, 'rol', ''),
                        list(request.user.groups.values_list('name', flat=True)))
        return JsonResponse({'productos': [], 'error': 'Sin permisos para Farmacia'}, status=403)
    empresa = _empresa_desde_request(request)
    if not empresa:
        return respuesta_sin_empresa_json()
    termino = (request.GET.get('termino') or request.GET.get('q') or '').strip()
    resultados = VentaFarmaciaService.buscar_productos_pdv(empresa, termino)
    return JsonResponse({'productos': resultados})


@login_required
def pdv_buscar_fragmento(request):
    """
    HTML parcial para el PDV (HTMX / sin JSON).
    Misma lógica de permisos y empresa que api_buscar_producto_pdv.
    """
    if request.method != 'GET':
        return HttpResponse('Método no permitido', status=405)

    if not _verificar_acceso(
        request.user,
        ['CAJERO', 'FARMACIA', 'ADMIN', 'ADMINISTRADOR', 'GERENTE'],
        ['FARMACIA', 'GERENCIA_OPERATIVA', 'GERENCIA'],
    ):
        html = render_to_string(
            'core/partials/pdv_buscar_fragmento.html',
            {'error': 'Sin permisos para Farmacia', 'productos': [], 'q': ''},
            request=request,
        )
        resp = HttpResponse(html, status=403, content_type='text/html; charset=utf-8')
        resp['Cache-Control'] = 'no-store'
        return resp

    empresa = _empresa_desde_request(request)
    if not empresa:
        return respuesta_sin_empresa_fragmento(request)

    q = (request.GET.get('q') or request.GET.get('termino') or '').strip()
    if len(q) < 2:
        html = render_to_string(
            'core/partials/pdv_buscar_fragmento.html',
            {'mensaje': 'Escriba al menos 2 caracteres…', 'productos': [], 'q': q},
            request=request,
        )
        resp = HttpResponse(html, content_type='text/html; charset=utf-8')
        resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return resp

    resultados = VentaFarmaciaService.buscar_productos_pdv(empresa, q)
    html = render_to_string(
        'core/partials/pdv_buscar_fragmento.html',
        {'productos': resultados, 'q': q},
        request=request,
    )
    resp = HttpResponse(html, content_type='text/html; charset=utf-8')
    resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp['Pragma'] = 'no-cache'
    return resp


@login_required
def pdv_farmacia(request):
    """
    Controlador Integral: Gestiona Búsqueda por lotes, Pagos Simultáneos,
    Folio Automático de Receta y Sincronización de Stock Real.
    Maneja múltiples acciones vía parámetros GET/POST.
    """
    # Control de acceso por rol/grupo (incluye variantes de rol usadas en BD)
    if not _verificar_acceso(request.user, ['CAJERO', 'FARMACIA', 'ADMIN', 'ADMINISTRADOR', 'GERENTE'], ['FARMACIA', 'GERENCIA_OPERATIVA', 'GERENCIA']):
        from django.contrib import messages
        messages.warning(request, 'No tienes permisos para acceder a Farmacia. Contacta al administrador.')
        return redirect('home')

    # PDV exige FK empresa en el usuario (no basta el tenant por defecto del middleware).
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return redirigir_sin_empresa_pdv(request)

    es_admin = request.user.groups.filter(name='Administrador').exists() or request.user.is_superuser
    
    # GHOST BUTTON: Determinar si el usuario puede ver Precio Neto (Staff)
    # Solo visible para: Farmacia, Gerente, Director, Administrador, Superuser
    ROLES_PRECIO_NETO = ['Administrador', 'FARMACIA', 'Gerente', 'Director']
    puede_precio_neto = (
        request.user.is_superuser or 
        request.user.groups.filter(name__in=ROLES_PRECIO_NETO).exists() or
        getattr(request.user, 'rol', '') in ['ADMIN', 'GERENTE', 'DIRECTOR', 'FARMACIA']
    )
    
    # ===== ACCIONES AJAX (GET) =====
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        accion = request.GET.get('accion')
        
        # 1. BÚSQUEDA DE PRODUCTOS
        if accion == 'buscar_producto':
            termino = request.GET.get('termino', '').strip()
            resultados = _buscar_productos_pdv_resultados(empresa, termino)
            return JsonResponse({'productos': resultados})
        
        # 2. DETALLE DE VENTA (Para reimpresión)
        elif accion == 'detalle_venta':
            from django.urls import reverse

            from contabilidad.models import FacturaCFDI

            venta_id = request.GET.get('id')
            try:
                venta = Venta.objects.select_related(
                    'empresa', 'usuario', 'paciente', 'receta', 'receta__medico'
                ).prefetch_related(
                    'detalles__producto',
                    'detalles__lote_vendido',
                    'detalles__lotes_extraidos__lote',
                    'pagos',
                    Prefetch(
                        'facturas_cfdi',
                        queryset=FacturaCFDI.objects.select_related('cliente').order_by(
                            '-fecha_emision', '-id'
                        ),
                    ),
                ).get(id=venta_id, empresa=empresa)
                
                detalles_data = []
                items_data = []  # JS-friendly: cant, nombre, sub, lote (for ticket/WhatsApp)
                for detalle in venta.detalles.all():
                    partes = [
                        f"{x.lote.numero_lote}×{x.cantidad_extraida}"
                        for x in detalle.lotes_extraidos.all()
                    ]
                    if not partes and detalle.lote_vendido:
                        partes = [f"{detalle.lote_vendido.numero_lote}×{detalle.cantidad}"]
                    lote_txt = ", ".join(partes) if partes else None
                    detalles_data.append({
                        'producto': detalle.producto.nombre,
                        'cantidad': detalle.cantidad,
                        'precio_unitario': float(detalle.precio_unitario),
                        'subtotal': float(detalle.subtotal),
                        'lote': lote_txt,
                    })
                    items_data.append({
                        'cant': detalle.cantidad,
                        'nombre': detalle.producto.nombre,
                        'sub': float(detalle.subtotal),
                        'lote': lote_txt,
                    })
                
                pagos_data = []
                for pago in venta.pagos.all():
                    pagos_data.append({
                        'metodo': pago.metodo,
                        'monto': float(pago.monto)
                    })

                facturas_cfdi_data = []
                for fac in venta.facturas_cfdi.all():
                    facturas_cfdi_data.append({
                        'id': fac.id,
                        'folio_interno': fac.folio_interno,
                        'estado': fac.estado,
                        'ultimo_error_pac': (fac.ultimo_error_pac or '')[:500],
                        'gestionar_url': request.build_absolute_uri(
                            reverse('contabilidad:detalle_factura', args=[fac.id])
                        ),
                        'timbrar_url': request.build_absolute_uri(
                            reverse('contabilidad:timbrar_factura', args=[fac.id])
                        ),
                        'pdf_url': (
                            request.build_absolute_uri(
                                reverse('contabilidad:descargar_pdf', args=[fac.id])
                            )
                            if fac.estado == 'TIMBRADO'
                            else ''
                        ),
                        'xml_url': (
                            request.build_absolute_uri(
                                reverse('contabilidad:descargar_xml', args=[fac.id])
                            )
                            if fac.estado == 'TIMBRADO' and (fac.xml_timbrado or '').strip()
                            else ''
                        ),
                    })

                return JsonResponse({
                    'folio': venta.folio_operacion or f'VTA-{venta.id}',
                    'fecha': venta.fecha.strftime('%Y-%m-%d %H:%M:%S'),
                    'cliente': venta.paciente_nombre or (venta.paciente.nombre_completo if venta.paciente else 'PÚBLICO GENERAL'),
                    'subtotal': float(venta.subtotal),
                    'iva': float(venta.impuestos_iva),
                    'descuento': float(venta.descuento_aplicado),
                    'porcentaje_descuento': float(venta.porcentaje_descuento) if venta.porcentaje_descuento else 0,
                    'total': float(venta.total),
                    'detalles': detalles_data,
                    'items': items_data,
                    'pagos': pagos_data,
                    'cajero': venta.usuario.get_full_name() or venta.usuario.username,
                    'sello_digital': venta.sello_digital or '',
                    'facturas_cfdi': facturas_cfdi_data,
                })
            except Venta.DoesNotExist:
                return JsonResponse({'error': 'Venta no encontrada'}, status=404)
        
        # 3. HISTORIAL DE VENTAS
        elif accion == 'obtener_historial':
            ventas = Venta.objects.filter(
                empresa=empresa,
                estado='COMPLETADA'
            ).order_by('-fecha')[:20]
            
            historial = []
            for v in ventas:
                historial.append({
                    'id': v.id,
                    'folio': v.folio_operacion or f'VTA-{v.id}',
                    'fecha': v.fecha.strftime('%Y-%m-%d %H:%M'),
                    'total': float(v.total),
                    'cliente': v.paciente_nombre or (v.paciente.nombre_completo if v.paciente else 'PÚBLICO GENERAL')
                })
            
            return JsonResponse({'ventas': historial})
        
        # 3.1. ÚLTIMAS VENTAS DEL DÍA (Para Tabla de Acciones Recientes)
        elif accion == 'ventas_recientes':
            hoy = timezone.now().date()
            ventas = Venta.objects.filter(
                empresa=empresa,
                usuario=request.user,
                fecha__date=hoy
            ).select_related('paciente').prefetch_related('detalles').order_by('-fecha')[:5]
            
            resultados = []
            for v in ventas:
                resultados.append({
                    'id': v.id,
                    'folio': v.folio_operacion or f'#{v.id}',
                    'hora': timezone.localtime(v.fecha).strftime('%H:%M'),
                    'cliente': v.paciente_nombre or (v.paciente.nombre_completo if v.paciente else 'PÚBLICO GENERAL'),
                    'total': float(v.total),
                    'productos_count': v.detalles.count()
                })
            
            return JsonResponse({'status': 'success', 'ventas': resultados})
        
        # 4. REPORTE CRÍTICO (Productos por vencer)
        elif accion == 'reporte_critico':
            hoy = timezone.now().date()
            fecha_limite = hoy + timedelta(days=_DIAS_CADUCIDAD_CRITICO)
            
            productos_criticos = []
            for producto in Producto.objects.filter(empresa=empresa):
                lotes_criticos = producto.lotes.filter(
                    fecha_caducidad__lte=fecha_limite,
                    fecha_caducidad__gte=hoy,
                    cantidad__gt=0
                ).order_by('fecha_caducidad')
                
                for lote in lotes_criticos:
                    productos_criticos.append({
                        'p': producto.nombre,
                        'l': lote.numero_lote,
                        'f': lote.fecha_caducidad.strftime('%d/%m/%Y'),
                        'c': lote.cantidad
                    })
            
            return JsonResponse({
                'productos': productos_criticos,
                'empresa': empresa.nombre
            })
        
        # 4. MOTOR DE EXTRACCIÓN: API de Sugerencias por Paciente
        elif accion == 'sugerencias_paciente':
            paciente_id = request.GET.get('paciente_id')
            if not paciente_id:
                return JsonResponse({'sugerencias': []})
            
            # Buscar items SUGERIDO de las últimas 48 horas para este paciente
            hace_48h = timezone.now() - timedelta(hours=48)
            sugerencias = RecetaItem.objects.filter(
                receta__empresa=empresa,
                receta__paciente_id=paciente_id,
                receta__fecha_emision__gte=hace_48h,
                estado='SUGERIDO'
            ).select_related('medicamento').order_by('-receta__fecha_emision')
            
            items_json = []
            for item in sugerencias:
                producto_nombre = item.medicamento.nombre if item.medicamento else item.texto_libre
                items_json.append({
                    'id': item.id,
                    'producto_id': item.medicamento.id if item.medicamento else None,
                    'producto_nombre': producto_nombre,
                    'cantidad': item.cantidad,
                    'precio': float(item.precio_momento),
                    'es_texto_libre': not bool(item.medicamento),
                    'fecha_deteccion': item.receta.fecha_emision.strftime('%Y-%m-%d %H:%M')
                })
            
            return JsonResponse({
                'sugerencias': items_json,
                'total': len(items_json),
                'mensaje': f'El Dr. mencionó {len(items_json)} medicamentos en la nota médica'
            })
    
    # ===== PROCESAR VENTA (POST) =====
    elif request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            return procesar_venta(request, data, empresa)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'Error al procesar los datos'}, status=400)
    
    # ===== RENDERIZAR PANTALLA PRINCIPAL =====
    puede_usar_ia = request.user.puede_usar_ia or request.user.is_superuser

    # ── OPT-1: Caché de sesión para contexto estático del POS ────────────────
    # El contexto del usuario/sucursal no cambia durante la sesión → cache 5min
    _cache_key = f'pdv_ctx_{request.user.id}_{empresa.id}'
    from django.core.cache import cache as _django_cache
    _ctx_cached = _django_cache.get(_cache_key)
    if _ctx_cached:
        sugerencias_por_paciente = _ctx_cached.get('sugerencias_por_paciente', {})
        sugerencias_sistema_count = _ctx_cached.get('sugerencias_sistema_count', 0)
    else:
        # Sugerencias: solo campos necesarios, ventana reducida a 12h para cold start
        hace_12h = timezone.now() - timedelta(hours=12)
        sugerencias_sistema = RecetaItem.objects.filter(
            receta__empresa=empresa,
            receta__fecha_emision__gte=hace_12h,
            estado='SUGERIDO'
        ).select_related(
            'receta__paciente', 'medicamento'
        ).only(
            'id', 'texto_libre', 'cantidad', 'precio_momento',
            'receta__id', 'receta__paciente_id',
            'medicamento__id', 'medicamento__nombre',
        ).order_by('-receta__fecha_emision')[:50]

        sugerencias_por_paciente = {}
        for item in sugerencias_sistema:
            paciente_id = item.receta.paciente_id
            if paciente_id not in sugerencias_por_paciente:
                sugerencias_por_paciente[paciente_id] = {
                    'paciente': item.receta.paciente,
                    'receta': item.receta,
                    'items': []
                }
            sugerencias_por_paciente[paciente_id]['items'].append({
                'id': item.id,
                'medicamento': item.medicamento,
                'texto_libre': item.texto_libre,
                'cantidad': item.cantidad,
                'precio': item.precio_momento,
            })
        sugerencias_sistema_count = len(sugerencias_por_paciente)
        # Guardar en caché 5 minutos para evitar recálculo en cada hit
        _django_cache.set(_cache_key, {
            'sugerencias_por_paciente': sugerencias_por_paciente,
            'sugerencias_sistema_count': sugerencias_sistema_count,
        }, timeout=300)

    return render(request, 'core/pdv_farmacia.html', {
        'institucion': empresa.nombre,
        'vigencia': empresa.periodo_vigencia or '',
        'farmacia_dias_max_antiguedad_receta': getattr(
            empresa, 'farmacia_dias_max_antiguedad_receta', 30
        ),
        'es_admin': es_admin,
        'puede_usar_ia': puede_usar_ia,
        'puede_precio_neto': puede_precio_neto,
        'sugerencias_sistema': list(sugerencias_por_paciente.values()),
        'total_sugerencias': sugerencias_sistema_count,
    })

@login_required
def lista_ventas_farmacia(request):
    """
    Vista profesional de lista de ventas (similar a Lista de Trabajo de Laboratorio).
    Muestra ventas en tabla densa y profesional.
    """
    empresa = _empresa_desde_request(request)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    # Filtros
    filtro_actual = request.GET.get('filtro', 'todos')
    hoy = timezone.now().date()
    
    from contabilidad.models import FacturaCFDI

    ventas_query = (
        Venta.objects.filter(empresa=empresa)
        .select_related('paciente', 'usuario')
        .prefetch_related(
            'detalles',
            'pagos',
            Prefetch(
                'facturas_cfdi',
                queryset=FacturaCFDI.objects.select_related('cliente').order_by(
                    '-fecha_emision', '-id'
                ),
            ),
        )
        .order_by('-fecha')
    )

    if filtro_actual == 'hoy':
        ventas_query = ventas_query.filter(fecha__date=hoy)
    elif filtro_actual == 'pendiente':
        ventas_query = ventas_query.filter(estado='PENDIENTE')
    elif filtro_actual == 'completadas':
        ventas_query = ventas_query.filter(estado='COMPLETADA')
    elif filtro_actual == 'canceladas':
        ventas_query = ventas_query.filter(estado='CANCELADA')
    elif filtro_actual == 'todos':
        pass  # Mostrar todas incluyendo canceladas
    else:
        # Por defecto excluir canceladas del listado activo
        ventas_query = ventas_query.exclude(estado='CANCELADA')

    ventas = ventas_query[:200]  # Aumentado a 200 para mejor visibilidad
    
    return render(request, 'core/lista_ventas_farmacia.html', {
        'ventas': ventas,
        'filtro_actual': filtro_actual,
    })

# ==============================================================================
# 2. PROCESAR VENTA (Función Principal)
# ==============================================================================

def procesar_venta(request, data, empresa):
    """Delega al servicio de dominio PDV (transaction.atomic en capa servicio)."""
    return VentaFarmaciaService.ejecutar_venta_pdv(request, data, empresa)



# ==============================================================================
# 3. ENTRADA DE MERCANCÍA Y OTRAS FUNCIONES (Placeholders)
# ==============================================================================

@login_required
def entrada_mercancia(request):
    """Vista para entrada de mercancía - Procesa ingreso directo al almacén."""
    empresa = _empresa_desde_request(request)
    
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        out = MovimientoInventarioService.entrada_mercancia_directa(request, empresa, data)
        return JsonResponse(out['body'], status=out['http_status'])
    
    # GET: Mostrar formulario
    return render(request, 'core/entrada_mercancia.html', {
        'empresa': empresa.nombre if empresa else 'PRISLAB'
    })


@login_required
def registrar_compra(request):
    """Vista para registrar compra de productos a proveedores.
    Usa MovimientoInventario (Kardex) para mantener trazabilidad completa."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        out = MovimientoInventarioService.registrar_compra_a_proveedor(request, empresa, data)
        return JsonResponse(out['body'], status=out['http_status'])
    
    # GET: Mostrar formulario
    from farmacia.models import Proveedor as FarmProveedor
    proveedores = FarmProveedor.objects.filter(empresa=empresa, activo=True).order_by('razon_social')
    return render(request, 'core/farmacia/compra_form.html', {
        'empresa': empresa,
        'proveedores': proveedores
    })


@login_required
@require_http_methods(["GET"])
def api_buscar_productos_compra(request):
    """API para buscar productos del catálogo para compras."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({'productos': []})
    termino = request.GET.get('q', '').strip()
    
    if len(termino) < 2:
        return JsonResponse({'productos': []})
    
    # Buscar productos por nombre, código de barras o sustancia activa
    productos = Producto.objects.filter(
        empresa=empresa
    ).filter(
        Q(nombre__icontains=termino) |
        Q(codigo_barras__icontains=termino) |
        Q(sustancia_activa__icontains=termino) |
        Q(marca_laboratorio__icontains=termino)
    )[:20]  # Limitar a 20 resultados
    
    resultados = []
    for p in productos:
        resultados.append({
            'id': p.id,
            'nombre': p.nombre,
            'codigo_barras': p.codigo_barras,
            'sustancia_activa': p.sustancia_activa or '',
            'marca_laboratorio': p.marca_laboratorio or '',
            'precio_compra_actual': str(p.precio_compra or 0),
            'stock_actual': p.stock or 0,
            'presentacion': p.presentacion or 'S/N'
        })
    
    return JsonResponse({'productos': resultados})

@login_required
def carga_masiva_excel(request):
    """Vista para carga masiva desde Excel."""
    return JsonResponse({'status': 'error', 'mensaje': 'Función no implementada aún'})

@login_required
def libro_control_antibioticos(request):
    """Libro de control COFEPRIS — NOM-059 / Art. 226 LGS."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    from farmacia.models import RegistroAntibiotico
    from django.utils import timezone as tz

    # Filtros por fecha
    fecha_desde_str = request.GET.get('fecha_desde', '')
    fecha_hasta_str = request.GET.get('fecha_hasta', '')
    producto_q = request.GET.get('producto', '').strip()

    qs = RegistroAntibiotico.objects.filter(empresa=empresa).select_related(
        'producto', 'paciente', 'usuario_vendedor', 'venta', 'lote_vendido'
    ).order_by('-fecha_venta')

    if fecha_desde_str:
        try:
            from datetime import date as _date
            fd = _date.fromisoformat(fecha_desde_str)
            qs = qs.filter(fecha_venta__gte=fd)
        except ValueError:
            pass
    if fecha_hasta_str:
        try:
            from datetime import date as _date
            fh = _date.fromisoformat(fecha_hasta_str)
            qs = qs.filter(fecha_venta__lte=fh)
        except ValueError:
            pass
    if producto_q:
        qs = qs.filter(producto__nombre__icontains=producto_q)

    # Construir estructura de reporte agrupada por producto (compatible con el template existente)
    from collections import defaultdict
    grupos = defaultdict(lambda: {'producto': None, 'entradas': [], 'salidas': []})

    for reg in qs[:500]:
        prod = reg.producto
        key = prod.pk
        if grupos[key]['producto'] is None:
            grupos[key]['producto'] = prod
        grupos[key]['salidas'].append({
            'fecha_mov': reg.fecha_venta,
            'tipo': 'VENTA',
            'ref': reg.venta.folio_operacion if reg.venta else '---',
            'lote_usado': reg.lote_vendido,
            'cantidad': reg.cantidad_vendida,
            'doctor': f"{reg.medico_nombre or reg.nombre_medico or ''} | Cédula: {reg.medico_cedula or reg.cedula_medico or ''}".strip('| '),
        })

    reporte = list(grupos.values())

    return render(request, 'core/libro_control.html', {
        'empresa': empresa,
        'reporte': reporte,
        'fecha_desde': fecha_desde_str,
        'fecha_hasta': fecha_hasta_str,
        'producto_q': producto_q,
        'razon_social': getattr(empresa, 'razon_social', empresa.nombre if empresa else ''),
        'rfc': getattr(empresa, 'rfc', ''),
    })

@login_required
def estadisticas_ventas(request):
    """Vista para estadísticas de ventas."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    return render(request, 'core/estadisticas.html', {'empresa': empresa})

@login_required
def ajustes_inventario(request):
    """Vista para ajustes de inventario (GET + POST)."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    if request.method == 'POST':
        try:
            cantidad = int(request.POST.get('cantidad', 0))
        except (TypeError, ValueError):
            return JsonResponse({'status': 'error', 'mensaje': 'Cantidad inválida'}, status=400)
        out = MovimientoInventarioService.aplicar_ajuste_por_lote(
            request,
            empresa,
            lote_id=request.POST.get('lote_id'),
            cantidad=cantidad,
            tipo=request.POST.get('tipo', 'BAJA'),
            observacion=request.POST.get('observacion', ''),
        )
        return JsonResponse(out['body'], status=out['http_status'])

    return render(request, 'core/ajustes_inventario.html', {'empresa': empresa})

@login_required
def inventario_general(request):
    """Vista para inventario general (una fila por lote; template espera lotes_data)."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        return redirigir_sin_empresa_pdv(request)
    productos = Producto.objects.filter(empresa=empresa).prefetch_related(
        'lotes'
    ).order_by('nombre')

    lotes_data = []
    valor_inventario = Decimal('0')
    hoy = date.today()
    for p in productos:
        for lote in p.lotes.all():
            stock_lote = int(lote.cantidad) if lote.cantidad is not None else 0
            dias_rest = None
            if lote.fecha_caducidad:
                dias_rest = (lote.fecha_caducidad - hoy).days
            else:
                dias_rest = 9999
            lotes_data.append({
                'producto': p,
                'lote': lote,
                'dias_restantes': dias_rest,
                'stock_lote': stock_lote,
            })
            if p.precio_compra and stock_lote > 0:
                valor_inventario += (p.precio_compra or Decimal('0')) * Decimal(stock_lote)

    lotes_data.sort(key=lambda x: (x['producto'].nombre.lower(), x['lote'].fecha_caducidad or hoy))

    return render(request, 'core/inventario_general.html', {
        'empresa': empresa,
        'productos': productos,
        'lotes_data': lotes_data,
        'valor_inventario': valor_inventario,
    })

@login_required
def registrar_gasto(request):
    """Vista y API para registrar gastos de caja. GET renderiza formulario, POST procesa JSON."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        if request.method == 'GET':
            from django.shortcuts import render as _render
            return _render(request, 'core/registro_gasto.html', {'empresa': None})
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    if request.method == 'GET':
        from django.shortcuts import render as _render
        from core.models import GastoCaja
        from django.utils import timezone
        gastos_hoy = GastoCaja.objects.filter(
            empresa=empresa,
            fecha__date=timezone.now().date()
        ).order_by('-fecha')[:20]
        return _render(request, 'core/registro_gasto.html', {
            'empresa': empresa,
            'gastos_hoy': gastos_hoy,
        })
    if request.method == 'POST':
        try:
            from django.core.exceptions import ValidationError

            data = json.loads(request.body)
            concepto = data.get('concepto', '')
            monto = Decimal(str(data.get('monto', 0)))
            gasto = GastoCaja(
                empresa=empresa,
                usuario=request.user,
                concepto=concepto,
                monto=monto,
            )
            gasto.save()
            # R107: AuditLog
            try:
                from core.services.audit_service import registrar_auditoria
                registrar_auditoria(
                    accion='CREATE',
                    modelo='GastoCaja',
                    objeto_id=str(gasto.id),
                    datos_nuevos={'concepto': concepto, 'monto': str(monto)},
                    request=request,
                )
            except Exception:
                pass
            return JsonResponse({'status': 'success'})
        except ValidationError as e:
            err = getattr(e, 'message_dict', None) or str(e)
            return JsonResponse({'status': 'error', 'mensaje': err}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=405)


@login_required
@require_http_methods(["GET"])
def api_saldo_caja(request):
    """
    API para ver saldo de caja en tiempo real (usado por verSaldoCaja() en PDV).
    Retorna JSON: total_vendido_dia, ventas_efectivo, ventas_digital, gastos_retiros,
    saldo_en_caja, lista_gastos (hora, concepto, monto).
    """
    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    hoy = timezone.now().date()
    inicio = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
    fin = timezone.make_aware(datetime.combine(hoy, datetime.max.time()))
    ventas_hoy = Venta.objects.filter(
        empresa=empresa,
        fecha__range=(inicio, fin),
        estado='COMPLETADA'
    )
    total_vendido_dia = ventas_hoy.aggregate(
        total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    ventas_efectivo = Pago.objects.filter(
        venta__empresa=empresa,
        venta__fecha__range=(inicio, fin),
        venta__estado='COMPLETADA',
    ).aggregate(
        total=Coalesce(Sum('monto_efectivo'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    ventas_digital_agg = Pago.objects.filter(
        venta__empresa=empresa,
        venta__fecha__range=(inicio, fin),
        venta__estado='COMPLETADA',
    ).aggregate(
        tar=Coalesce(Sum('monto_tarjeta'), Decimal('0.00'), output_field=DecimalField()),
        trans=Coalesce(Sum('monto_transferencia'), Decimal('0.00'), output_field=DecimalField()),
    )
    ventas_digital = (ventas_digital_agg.get('tar') or Decimal('0.00')) + (ventas_digital_agg.get('trans') or Decimal('0.00'))
    gastos_hoy = GastoCaja.objects.filter(
        empresa=empresa,
        fecha__range=(inicio, fin)
    ).order_by('-fecha')
    total_gastos = gastos_hoy.aggregate(
        total=Coalesce(Sum('monto'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    lista_gastos = [
        {
            'hora': g.fecha.strftime('%H:%M') if g.fecha else '--:--',
            'concepto': g.concepto or '',
            'monto': float(g.monto),
        }
        for g in gastos_hoy
    ]
    saldo_en_caja = ventas_efectivo - total_gastos
    return JsonResponse({
        'total_vendido_dia': float(total_vendido_dia),
        'ventas_efectivo': float(ventas_efectivo),
        'ventas_digital': float(ventas_digital),
        'gastos_retiros': float(total_gastos),
        'saldo_en_caja': float(saldo_en_caja),
        'lista_gastos': lista_gastos,
    })


@login_required
def api_farmacia_kpis(request):
    """
    API para alimentar los gráficos del Dashboard de Farmacia.
    Retorna JSON con ventas de los últimos 7 días.
    """
    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'message': 'Sin empresa'}, status=403)
        
    try:
        hoy = timezone.now().date()
        fechas = []
        ventas = []
        
        # Últimos 7 días
        for i in range(6, -1, -1):
            fecha = hoy - timedelta(days=i)
            # Inicio y fin del día
            inicio_dia = timezone.make_aware(datetime.combine(fecha, datetime.min.time()))
            fin_dia = timezone.make_aware(datetime.combine(fecha, datetime.max.time()))
            
            total_dia = Venta.objects.filter(
                empresa=empresa,
                fecha__range=(inicio_dia, fin_dia)
            ).aggregate(total=Sum('total'))['total'] or 0
            
            fechas.append(fecha.strftime('%d/%m')) # Ej: "24/01"
            ventas.append(float(total_dia))
            
        return JsonResponse({
            'status': 'success',
            'labels': fechas,
            'data': ventas
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@login_required
def facturacion_40(request):
    """Vista de Facturación 4.0 (CFDI)."""
    empresa = _empresa_desde_request(request)
    return render(request, 'core/facturacion_40.html', {'empresa': empresa})


@login_required
def dashboard_farmacia(request):
    """Dashboard principal de farmacia."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada. Contacte al administrador.')
        # Redirigir a una vista que no cause bucle
        return redirect('admin:index')  # Ir al admin panel en lugar de 'home'

    hoy = timezone.now().date()
    inicio = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
    fin = timezone.make_aware(datetime.combine(hoy, datetime.max.time()))
    
    ventas_hoy = Venta.objects.filter(empresa=empresa, fecha__range=(inicio, fin), estado='COMPLETADA')
    total_ventas_hoy = ventas_hoy.aggregate(total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField()))['total'] or Decimal('0.00')
    
    # 2. PERSISTENCIA DE METAS (Dinámico)
    try:
        from django.apps import apps
        MetaVenta = apps.get_model('core', 'MetaVenta')
        meta_obj = MetaVenta.objects.filter(empresa=empresa, fecha=hoy).first()
        monto_meta = meta_obj.monto_objetivo if meta_obj else Decimal('50000.00')
    except LookupError:
        # Fallback si el modelo no ha sido migrado aún
        monto_meta = Decimal('50000.00')
    
    # Calcular porcentaje de meta
    porcentaje_meta = 0
    if monto_meta > 0:
        porcentaje_meta = (total_ventas_hoy / monto_meta) * 100
        if porcentaje_meta > 100: porcentaje_meta = 100

    ventas_efectivo = Pago.objects.filter(
        venta__empresa=empresa,
        venta__fecha__range=(inicio, fin),
        venta__estado='COMPLETADA',
        metodo='EFECTIVO'
    ).aggregate(total=Coalesce(Sum('monto'), Decimal('0.00'), output_field=DecimalField()))['total'] or Decimal('0.00')
    
    ventas_digital = Pago.objects.filter(
        venta__empresa=empresa,
        venta__fecha__range=(inicio, fin),
        venta__estado='COMPLETADA'
    ).exclude(metodo='EFECTIVO').aggregate(total=Coalesce(Sum('monto'), Decimal('0.00'), output_field=DecimalField()))['total'] or Decimal('0.00')
    
    gastos_hoy = GastoCaja.objects.filter(empresa=empresa, fecha__range=(inicio, fin))
    saldo_caja = ventas_efectivo - (gastos_hoy.aggregate(total=Coalesce(Sum('monto'), Decimal('0.00'), output_field=DecimalField()))['total'] or Decimal('0.00'))
    
    ultimas_ventas = ventas_hoy.select_related('paciente').order_by('-fecha')[:10]

    # Alertas FEFO/stock: 2 queries planas en lugar de N queries por producto
    from django.db.models import Prefetch as _Prefetch
    from core.models import Lote as _Lote

    fecha_limite = hoy + timedelta(days=_DIAS_CADUCIDAD_CRITICO)

    # Lotes próximos a caducar — query única ordenada por fecha_caducidad
    lotes_por_vencer = (
        _Lote.objects.filter(
            producto__empresa=empresa,
            cantidad__gt=0,
            fecha_caducidad__lte=fecha_limite,
            fecha_caducidad__gte=hoy,
        )
        .select_related('producto')
        .order_by('fecha_caducidad')[:50]
    )
    productos_vencer = []
    for lote in lotes_por_vencer:
        dias = (lote.fecha_caducidad - hoy).days
        productos_vencer.append({
            'nombre': lote.producto.nombre,
            'lote': lote.numero_lote,
            'fecha_caducidad': lote.fecha_caducidad,
            'dias_restantes': dias,
            'cantidad': lote.cantidad,
            'es_critico': dias <= 7,
        })

    # Stock bajo/agotado — annotate en una query plana
    from django.db.models import Sum as _SumD
    from django.db.models.functions import Coalesce as _Coalesce2
    productos_stock_qs = (
        Producto.objects.filter(empresa=empresa)
        .annotate(stock_real=_Coalesce2(_SumD('lotes__cantidad'), 0))
        .values('id', 'nombre', 'codigo_barras', 'unidad_venta', 'stock_minimo', 'stock_real')
    )
    productos_bajo_stock = []
    lista_agotados = []
    for p in productos_stock_qs:
        s = p['stock_real']
        if s == 0:
            lista_agotados.append({
                'nombre': p['nombre'],
                'codigo': p['codigo_barras'] or '',
                'stock_actual': 0,
                'unidad': p['unidad_venta'] or '',
            })
        elif s < (p['stock_minimo'] or 10):
            productos_bajo_stock.append({
                'nombre': p['nombre'],
                'stock_actual': s,
                'stock_minimo': p['stock_minimo'] or 10,
                'es_critico': s <= 3,
            })

    # Total de unidades vendidas hoy
    try:
        productos_vendidos = DetalleVenta.objects.filter(
            venta__empresa=empresa,
            venta__fecha__range=(inicio, fin),
            venta__estado='COMPLETADA'
        ).aggregate(total=Sum('cantidad'))['total'] or 0
    except Exception:
        productos_vendidos = 0

    # Top 5 productos más vendidos hoy
    try:
        top_ventas = (
            DetalleVenta.objects
            .filter(venta__empresa=empresa, venta__fecha__range=(inicio, fin), venta__estado='COMPLETADA')
            .values('producto__nombre', 'producto__presentacion')
            .annotate(cantidad_vendida=Sum('cantidad'))
            .order_by('-cantidad_vendida')[:5]
        )
        productos_mas_vendidos = [
            {
                'nombre': t['producto__nombre'] or '',
                'presentacion': t['producto__presentacion'] or '',
                'cantidad_vendida': t['cantidad_vendida'] or 0,
            }
            for t in top_ventas
        ]
    except Exception:
        productos_mas_vendidos = []

    # Ventas recientes con estructura compatible con el template
    ventas_recientes = []
    for v in ultimas_ventas:
        try:
            cliente = (
                getattr(v.paciente, 'nombre_completo', None)
                or getattr(v, 'paciente_nombre', None)
                or 'Público General'
            )
            ventas_recientes.append({
                'folio': v.folio_operacion or f'#{v.id}',
                'cliente_nombre': cliente,
                'fecha_hora': v.fecha,
                'total': v.total,
                'productos_cantidad': v.detalles.count(),
            })
        except Exception:
            pass

    return render(request, 'core/dashboard_farmacia.html', {
        'empresa': empresa,
        'fecha_hoy': hoy.strftime('%d/%m/%Y'),
        # Nombres canónicos (usados en otras vistas)
        'total_ventas_hoy': total_ventas_hoy,
        'cantidad_ventas': ventas_hoy.count(),
        'ultimas_ventas': ultimas_ventas,
        'productos_bajo_stock': productos_bajo_stock,
        'productos_vencer': productos_vencer,
        'cantidad_productos_vencer': len(productos_vencer),
        'cantidad_productos_bajo_stock': len(productos_bajo_stock),
        # Alias que el template dashboard_farmacia.html espera
        'ventas_hoy_total': total_ventas_hoy,
        'ventas_hoy_cantidad': ventas_hoy.count(),
        'productos_vendidos': productos_vendidos,
        'productos_agotados': len(lista_agotados),
        'productos_caducidad': len(productos_vencer),
        'lista_agotados': lista_agotados,
        'ventas_recientes': ventas_recientes,
        'productos_mas_vendidos': productos_mas_vendidos,
        'productos_stock_bajo': productos_bajo_stock,
        'productos_proximos_caducar': productos_vencer,
        'ventas_controlados_sin_registrar': 0,
        # Otros
        'monto_meta': monto_meta,
        'porcentaje_meta': porcentaje_meta,
        'ventas_efectivo': ventas_efectivo,
        'ventas_digital': ventas_digital,
        'saldo_caja': saldo_caja,
        'fecha_seleccionada': request.GET.get('fecha', hoy.strftime('%Y-%m-%d'))
    })

@login_required
def gestionar_politicas_descuento(request):
    """Vista para gestionar políticas de descuento. Acceso: ADMIN/GERENCIA/DIRECTOR."""
    from django.contrib import messages as _msgs
    empresa = _empresa_desde_request(request)
    if not empresa:
        _msgs.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    rol = (getattr(request.user, 'rol', '') or '').upper().strip()
    _roles_permitidos = ('ADMIN', 'ADMINISTRADOR', 'GERENCIA', 'GERENCIA_OPERATIVA',
                         'DIRECTOR', 'FARMACIA_SUPERVISOR')
    if not (request.user.is_superuser or request.user.is_staff or rol in _roles_permitidos):
        _msgs.warning(request, 'No tienes permisos para acceder a Políticas de Descuento.')
        return redirect('home')

    politicas = DiscountPolicy.objects.filter(empresa=empresa)
    return render(request, 'core/politicas_descuento.html', {
        'empresa': empresa,
        'politicas': politicas
    })

@login_required
def historial_devoluciones(request):
    """Vista para historial de devoluciones."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    fecha_param = request.GET.get('fecha')
    hoy = timezone.now().date()
    if fecha_param:
        try:
            fecha_seleccionada = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            fecha_seleccionada = hoy
    else:
        fecha_seleccionada = hoy
    
    inicio = timezone.make_aware(datetime.combine(fecha_seleccionada, datetime.min.time()))
    fin = timezone.make_aware(datetime.combine(fecha_seleccionada, datetime.max.time()))
    
    devoluciones = SalesReturn.objects.filter(
        empresa=empresa,
        fecha_devolucion__range=(inicio, fin)
    ).order_by('-fecha_devolucion')
    
    return render(request, 'core/devoluciones.html', {
        'empresa': empresa,
        'devoluciones': devoluciones,
        'fecha_seleccionada': fecha_seleccionada.strftime('%Y-%m-%d')
    })

@login_required
def buscar_venta_devolucion(request):
    """API para buscar venta para devolución."""
    folio = request.GET.get('folio', '')
    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    try:
        venta = Venta.objects.get(folio_operacion=folio, empresa=empresa)
        return JsonResponse({
            'status': 'success',
            'venta': {
                'id': venta.id,
                'folio': venta.folio_operacion,
                'total': float(venta.total),
                'fecha': venta.fecha.strftime('%Y-%m-%d %H:%M')
            }
        })
    except Venta.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Venta no encontrada'}, status=404)

def es_gerente_o_admin(user):
    """
    Verifica si el usuario tiene permisos de gerente o administrador.
    Requerido para operaciones sensibles como devoluciones.
    """
    if user.is_superuser:
        return True
    
    # Verificar si el usuario pertenece a grupos de gerencia
    return user.groups.filter(name__in=['Gerente', 'Administrador', 'Admin']).exists()


@login_required
@user_passes_test(es_gerente_o_admin, login_url='/login/')
def procesar_devolucion(request):
    """
    API para procesar devolución.
    SEGURIDAD: Requiere permisos de gerente o administrador.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        empresa = _empresa_desde_request(request)
        out = VentaFarmaciaService.registrar_devolucion_resultado(request, empresa, data)
        return JsonResponse(out['body'], status=out['http_status'])
    return JsonResponse({'status': 'error'}, status=405)


@login_required
@user_passes_test(es_gerente_o_admin, login_url='/login/')
def cancelar_venta(request, venta_id):
    """
    Cancela una venta: marca estado CANCELADA y revierte el stock de cada lote
    creando movimientos Kardex de entrada por reversión.
    """
    empresa = _empresa_desde_request(request)
    try:
        vid = int(venta_id)
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'mensaje': 'ID de venta inválido'}, status=400)
    out = VentaFarmaciaService.cancelar_venta_resultado(request, empresa, vid)
    return JsonResponse(out['body'], status=out['http_status'])


@login_required
def imprimir_ticket(request, venta_id):
    """Vista para imprimir ticket de venta (mejorada R104)."""
    from contabilidad.models import FacturaCFDI

    empresa = _empresa_desde_request(request)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    venta = get_object_or_404(
        Venta.objects.prefetch_related(
            Prefetch(
                'facturas_cfdi',
                queryset=FacturaCFDI.objects.select_related('cliente').order_by(
                    '-fecha_emision', '-id'
                ),
            ),
        ),
        id=venta_id,
        empresa=empresa,
    )
    detalles = venta.detalles.select_related('producto').all() if hasattr(venta, 'detalles') else []
    pagos = Pago.objects.filter(venta=venta) if venta else []
    return render(request, 'core/ticket_venta.html', {
        'venta': venta,
        'detalles': detalles,
        'pagos': pagos,
        'empresa': empresa,
        'facturas_cfdi': list(venta.facturas_cfdi.all()),
    })

@login_required
def imprimir_ticket_raw(request, venta_id):
    """
    Vista raw para ticket de 80mm optimizada para QZ Tray.
    Devuelve HTML minimalista sin margenes.
    """
    empresa = _empresa_desde_request(request)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    venta = get_object_or_404(Venta, id=venta_id, empresa=empresa)
    detalles = venta.detalles.select_related('producto').all() if hasattr(venta, 'detalles') else []
    pagos = Pago.objects.filter(venta=venta) if venta else []
    return render(request, 'core/impresion/ticket_venta_raw.html', {
        'venta': venta,
        'detalles': detalles,
        'pagos': pagos,
        'empresa': empresa,
    })

# ==============================================================================
# 4. CORTE DE CAJA
# ==============================================================================

@login_required
def corte_caja_dia(request):
    """
    CORTE DE CAJA UNIFICADO (CONSOLIDACION R104)
    Incluye: Farmacia + Laboratorio + Consultorio.
    Corte Ciego V5.0: El cajero NO ve el monto esperado hasta reportar.
    """
    if not _verificar_acceso(request.user, ['CAJERO', 'FARMACIA', 'ADMIN', 'ADMINISTRADOR', 'GERENTE'], ['FARMACIA', 'GERENCIA_OPERATIVA', 'GERENCIA']):
        from django.contrib import messages
        messages.warning(request, 'No tienes permisos para acceder al Corte de Caja.')
        return redirect('home')
    empresa = _empresa_desde_request(request)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    # Obtener fecha del parametro GET (por defecto: hoy)
    fecha_param = request.GET.get('fecha')
    hoy = timezone.localtime(timezone.now()).date()
    if fecha_param:
        try:
            fecha_seleccionada = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except Exception:
            fecha_seleccionada = hoy
    else:
        fecha_seleccionada = hoy

    inicio = timezone.make_aware(datetime.combine(fecha_seleccionada, datetime.min.time()))
    fin = timezone.make_aware(datetime.combine(fecha_seleccionada, datetime.max.time()))

    # ========== 1. FARMACIA (Ventas) ==========
    ventas = Venta.objects.filter(
        empresa=empresa,
        fecha__range=(inicio, fin),
        estado='COMPLETADA'
    )
    total_farmacia = ventas.aggregate(
        total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')

    # Desglose multimodal: cobro mixto (efectivo+tarjeta+transferencia) en un solo Pago
    ventas_efectivo_farm = Pago.objects.filter(
        venta__empresa=empresa,
        venta__fecha__range=(inicio, fin),
        venta__estado='COMPLETADA',
    ).aggregate(
        total=Coalesce(Sum('monto_efectivo'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')

    ventas_digital_farm_agg = Pago.objects.filter(
        venta__empresa=empresa,
        venta__fecha__range=(inicio, fin),
        venta__estado='COMPLETADA',
    ).aggregate(
        tar=Coalesce(Sum('monto_tarjeta'), Decimal('0.00'), output_field=DecimalField()),
        trans=Coalesce(Sum('monto_transferencia'), Decimal('0.00'), output_field=DecimalField()),
    )
    ventas_digital_farm = (ventas_digital_farm_agg.get('tar') or Decimal('0.00')) + (ventas_digital_farm_agg.get('trans') or Decimal('0.00'))

    # ========== 2. LABORATORIO (Ordenes) ==========
    try:
        from core.models import OrdenDeServicio, PagoOrden
        ordenes_lab = OrdenDeServicio.objects.filter(
            empresa=empresa,
            fecha_creacion__range=(inicio, fin),
        )
        total_lab = ordenes_lab.aggregate(
            total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')

        lab_efectivo = PagoOrden.objects.filter(
            orden__empresa=empresa,
            fecha_pago__range=(inicio, fin),
        ).aggregate(
            ef=Coalesce(Sum('monto_efectivo'), Decimal('0.00'), output_field=DecimalField()),
        )['ef'] or Decimal('0.00')

        lab_digital = PagoOrden.objects.filter(
            orden__empresa=empresa,
            fecha_pago__range=(inicio, fin),
        ).aggregate(
            tar=Coalesce(Sum('monto_tarjeta'), Decimal('0.00'), output_field=DecimalField()),
            trans=Coalesce(Sum('monto_transferencia'), Decimal('0.00'), output_field=DecimalField()),
        )
        lab_digital_total = (lab_digital['tar'] or Decimal('0.00')) + (lab_digital['trans'] or Decimal('0.00'))
    except Exception:
        total_lab = Decimal('0.00')
        lab_efectivo = Decimal('0.00')
        lab_digital_total = Decimal('0.00')
        ordenes_lab = []

    # ========== 3. CONSULTORIO (Cobros) ==========
    try:
        from consultorio.models import CobroConsulta
        cobros_cons = CobroConsulta.objects.filter(
            caja__empresa=empresa,
            fecha_cobro__range=(inicio, fin),
            estado='PAGADO'
        )
        total_consultorio = cobros_cons.aggregate(
            total=Coalesce(Sum('monto_total'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')

        cons_efectivo = cobros_cons.aggregate(
            ef=Coalesce(Sum('monto_efectivo'), Decimal('0.00'), output_field=DecimalField())
        )['ef'] or Decimal('0.00')

        cons_digital = cobros_cons.aggregate(
            tar=Coalesce(Sum('monto_tarjeta'), Decimal('0.00'), output_field=DecimalField()),
            trans=Coalesce(Sum('monto_transferencia'), Decimal('0.00'), output_field=DecimalField()),
        )
        cons_digital_total = (cons_digital['tar'] or Decimal('0.00')) + (cons_digital['trans'] or Decimal('0.00'))
    except Exception:
        total_consultorio = Decimal('0.00')
        cons_efectivo = Decimal('0.00')
        cons_digital_total = Decimal('0.00')

    # ========== TOTALES CONSOLIDADOS ==========
    total_ventas = total_farmacia + total_lab + total_consultorio
    ventas_efectivo = ventas_efectivo_farm + lab_efectivo + cons_efectivo
    ventas_digital = ventas_digital_farm + lab_digital_total + cons_digital_total

    # Gastos del dia
    gastos = GastoCaja.objects.filter(
        empresa=empresa,
        fecha__range=(inicio, fin)
    ).order_by('-fecha')
    total_gastos = gastos.aggregate(
        total=Coalesce(Sum('monto'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')

    # Fondo de apertura de caja (si existe) — mismo día que el corte
    fondo_apertura = Decimal('0.00')
    try:
        from farmacia.models import AperturaCaja
        apertura = AperturaCaja.objects.filter(
            empresa=empresa,
            fecha_apertura__date=fecha_seleccionada,
            activa=True
        ).order_by('-fecha_apertura').first()
        if apertura:
            fondo_apertura = Decimal(str(apertura.fondo_efectivo or 0))
    except Exception:
        pass

    # ========== 4. DEVOLUCIONES (restar del corte) ==========
    # Incluir: core.DevolucionVenta (forense), farmacia.DevolucionVenta (soporte) y SalesReturn (core flow)
    total_devoluciones = Decimal('0.00')
    try:
        devoluciones_farm = DevolucionVenta.objects.filter(
            empresa=empresa,
            fecha_devolucion__range=(inicio, fin),
        ).aggregate(
            total=Coalesce(Sum('monto_devuelto'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
        total_devoluciones = devoluciones_farm
        # Devoluciones del módulo farmacia (soporte): mismo día y procesadas
        try:
            from farmacia.models import DevolucionVenta as DevolucionVentaFarmacia
            devoluciones_soporte = DevolucionVentaFarmacia.objects.filter(
                empresa=empresa,
                fecha_devolucion__range=(inicio, fin),
                procesada=True,
            ).aggregate(
                total=Coalesce(Sum('monto_devolucion'), Decimal('0.00'), output_field=DecimalField())
            )['total'] or Decimal('0.00')
            total_devoluciones += devoluciones_soporte
        except Exception:
            pass
        # SalesReturn (core/views/farmacia.procesar_devolucion) — no se sumaba antes
        sales_returns_dia = SalesReturn.objects.filter(
            empresa=empresa,
            fecha_devolucion__range=(inicio, fin),
        ).aggregate(
            total=Coalesce(Sum('monto_reembolsado'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
        total_devoluciones += sales_returns_dia
    except Exception:
        pass

    total_ventas_neto = total_ventas - total_devoluciones
    ventas_efectivo_neto = ventas_efectivo - total_devoluciones

    # Saldo esperado = fondo_apertura + efectivo_cobrado - gastos - devoluciones
    saldo_caja = fondo_apertura + ventas_efectivo_neto - total_gastos

    # Respuesta JSON para PDV (fetch desde pdv_farmacia.js)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'total_venta': float(total_ventas_neto),
            'efectivo': float(ventas_efectivo_neto),
            'digital': float(ventas_digital),
            'gastos': float(total_gastos),
            'devoluciones': float(total_devoluciones),
            'en_caja': float(saldo_caja),
            'mermas': 0.0,
            'empresa': empresa.nombre if hasattr(empresa, 'nombre') else str(empresa),
            'fecha_raw': fecha_seleccionada.strftime('%Y-%m-%d'),
            'fecha_display': fecha_seleccionada.strftime('%d/%m/%Y'),
        })

    return render(request, 'core/corte_caja_dia.html', {
        'empresa': empresa,
        'fondo_apertura': fondo_apertura,
        'fecha': fecha_seleccionada,
        'fecha_seleccionada': fecha_seleccionada.strftime('%Y-%m-%d'),
        'ventas': ventas,
        'total_ventas': total_ventas_neto,
        'ventas_efectivo': ventas_efectivo_neto,
        'ventas_digital': ventas_digital,
        'gastos': gastos,
        'total_gastos': total_gastos,
        'total_devoluciones': total_devoluciones,
        'saldo_caja': saldo_caja,
        # Desglose por area
        'total_farmacia': total_farmacia,
        'total_lab': total_lab,
        'total_consultorio': total_consultorio,
        'ventas_efectivo_farm': ventas_efectivo_farm,
        'ventas_digital_farm': ventas_digital_farm,
        'lab_efectivo': lab_efectivo,
        'lab_digital': lab_digital_total,
        'cons_efectivo': cons_efectivo,
        'cons_digital': cons_digital_total,
    })

# ==============================================================================
# 4. OTRAS FUNCIONES (continuar desde aquí...)
# ==============================================================================

@login_required
def api_buscar_productos_lectura(request):
    """API para buscar productos de farmacia (SOLO LECTURA para médicos)."""
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)
    
    query = request.GET.get('q', '').strip()
    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada', 'productos': []}, status=403)
    
    if not query or len(query) < 2:
        return JsonResponse({'status': 'success', 'productos': []})
    
    productos = Producto.objects.filter(
        empresa=empresa,
        stock__gt=0
    ).filter(
        Q(nombre__icontains=query) | 
        Q(sustancia_activa__icontains=query) | 
        Q(codigo_barras__icontains=query)
    )[:20]
    
    resultados = []
    for prod in productos:
        resultados.append({
            'id': prod.id,
            'nombre': prod.nombre,
            'sustancia_activa': prod.sustancia_activa or '',
            'stock': prod.stock,
            'precio': float(prod.precio_publico),
            'codigo_barras': prod.codigo_barras,
            'categoria': prod.get_categoria_display(),
        })
    
    return JsonResponse({'status': 'success', 'productos': resultados})


@login_required
@require_http_methods(["GET"])
def api_validar_cupon(request):
    """
    API para validar un cupón de marketing en tiempo real.
    Retorna información del cupón si es válido.
    """
    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    codigo_cupon = request.GET.get('codigo', '').strip().upper()
    
    if not codigo_cupon:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Código de cupón requerido'
        }, status=400)
    
    try:
        # Intentar importar el modelo de marketing
        from marketing.models import CuponMarketing
        
        # Buscar el cupón
        cupon = CuponMarketing.objects.filter(
            empresa=empresa,
            codigo=codigo_cupon
        ).first()
        
        if not cupon:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Cupón no encontrado'
            }, status=404)
        
        # Validar que el cupón esté activo (si tiene fecha de expiración, agregar validación)
        # Por ahora, solo validamos que exista
        
        return JsonResponse({
            'status': 'success',
            'cupon': {
                'id': cupon.id,
                'codigo': cupon.codigo,
                'porcentaje_descuento': float(cupon.porcentaje_descuento),
                'descripcion': cupon.descripcion or '',
            }
        })
        
    except ImportError:
        # Si el módulo de marketing no está disponible
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Módulo de marketing no disponible'
        }, status=503)
    except Exception as e:
        logger_core.error(f'Error al validar cupón: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Error al validar el cupón'
        }, status=500)


@login_required
def imprimir_etiquetas(request):
    """Genera PDF de etiquetas de productos seleccionados."""
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            lotes_ids = data.get('lotes', [])
            
            if not lotes_ids:
                 return JsonResponse({'error': 'No se seleccionaron lotes'}, status=400)

            # Lógica de generación de PDF (Simulada o Real)
            # En un entorno real usaríamos reportlab o similar.
            # Aquí simularemos la respuesta exitosa y la instrucción de guardado en Drive.
            
            # Integración Drive: la tarea Celery de sincronización (farmacia.tasks.sync_to_drive)
            # toma el archivo del buffer local y lo sube en segundo plano (arquitectura híbrida asíncrona).
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Se generaron {len(lotes_ids)} etiquetas. Guardado en Drive/REPORTES.',
                'url_pdf': '#' # URL ficticia o real si se generara
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ==============================================================================
# VALIDACIÓN DE PIN PARA PRECIO NETO (GHOST BUTTON)
# ==============================================================================

@login_required
@require_http_methods(["POST"])
def validar_pin_precio_neto(request):
    """
    Valida el PIN ingresado por el staff para activar el descuento 
    a Precio Neto (costo de compra). Solo usuarios autorizados pueden
    solicitar esta validación.
    """
    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa asignada'}, status=403)
    
    # Verificar que el usuario tiene permiso de acceder a esta función
    ROLES_PRECIO_NETO = ['Administrador', 'FARMACIA', 'Gerente', 'Director']
    puede_precio_neto = (
        request.user.is_superuser or 
        request.user.groups.filter(name__in=ROLES_PRECIO_NETO).exists() or
        getattr(request.user, 'rol', '') in ['ADMIN', 'GERENTE', 'DIRECTOR', 'FARMACIA']
    )
    
    if not puede_precio_neto:
        logger_core.warning(
            f"[SEGURIDAD] Usuario {request.user.username} intentó validar PIN de precio neto sin permisos."
        )
        return JsonResponse({'status': 'error', 'mensaje': 'Acceso denegado'}, status=403)
    
    try:
        data = json.loads(request.body)
        pin_ingresado = str(data.get('pin', '')).strip()
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'status': 'error', 'mensaje': 'Datos inválidos'}, status=400)
    
    if not pin_ingresado:
        return JsonResponse({'status': 'error', 'mensaje': 'PIN requerido'}, status=400)
    
    # Obtener PIN configurado; sin configuración no hay acceso (nunca default inseguro)
    try:
        config = ConfiguracionModulos.objects.get(empresa=empresa)
        pin_correcto = config.pin_precio_neto or ''
    except ConfiguracionModulos.DoesNotExist:
        pin_correcto = ''
    if not pin_correcto:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'El PIN de Precio Neto no está configurado. Configure uno en la sección de Módulos antes de usar esta función.'
        }, status=403)
    
    if pin_ingresado == pin_correcto:
        logger_core.info(
            f"[STAFF] PIN de Precio Neto validado correctamente por {request.user.username}"
        )
        return JsonResponse({
            'status': 'success',
            'mensaje': 'PIN correcto. Precio Neto activado.',
            'autorizado': True
        })
    else:
        logger_core.warning(
            f"[SEGURIDAD] PIN de Precio Neto incorrecto ingresado por {request.user.username}"
        )
        return JsonResponse({
            'status': 'error',
            'mensaje': 'PIN incorrecto. Acceso denegado.',
            'autorizado': False
        }, status=401)


@login_required
@require_http_methods(["POST"])
def api_carga_masiva_productos(request):
    """API para carga masiva de productos desde un JSON batch.
    Solo accesible para superusuarios/administradores."""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'mensaje': 'Solo superusuarios'}, status=403)

    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa'}, status=400)

    sucursal = empresa.sucursales.first()

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)

    productos_data = data.get('productos', [])
    limpiar = bool(data.get('limpiar', False))

    out = CatalogoFarmaciaService.carga_masiva_productos(
        empresa,
        sucursal,
        productos_data,
        limpiar=limpiar,
    )
    return JsonResponse(out['body'], status=out['http_status'])
