"""
Vistas del Punto de Venta (PDV) de Farmacia
Incluye: búsqueda de productos, procesamiento de ventas, historial, reportes críticos
"""

import json
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal

from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.db.models import Q, Sum, F, Prefetch
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger('farmacia.pdv')

# Umbrales de caducidad configurables
_DIAS_CADUCIDAD_CRITICO = getattr(settings, 'FARMACIA_DIAS_CADUCIDAD_CRITICO', 30)

from core.models import (
    Producto, Lote, Venta, DetalleVenta, Pago, Medico, Receta,
    Paciente, RecetaItem, ConfiguracionModulos, Empresa
)
from core.utils.farmacia_tenant import (
    redirigir_sin_empresa_pdv,
    respuesta_sin_empresa_fragmento,
    respuesta_sin_empresa_json,
)
from core.utils.empresa_request import get_empresa_usuario
from core.services.ventas.venta_farmacia_service import VentaFarmaciaService


def _empresa_desde_request(request):
    """Empresa efectiva: EmpresaIdentityMiddleware (fallback principal) o FK del usuario."""
    return getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)


def _verificar_acceso(user, roles_permitidos, grupos_permitidos=None):
    """
    Verifica si el usuario tiene acceso por ROL o por GRUPO de Django.
    - roles_permitidos: lista de valores del campo user.rol (ej: ['CAJERO', 'ADMIN'])
    - grupos_permitidos: lista de nombres de grupos Django (ej: ['FARMACIA', 'GERENCIA_OPERATIVA'])
    """
    if not get_empresa_usuario(user):
        return False
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


# ==============================================================================
# API: LOTES DE PRODUCTO
# ==============================================================================

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

    VentaFarmaciaService.materializar_lote_operativo_si_falta(p, empresa)
    p = Producto.objects.prefetch_related('lotes').get(id=producto_id, empresa=empresa)

    hoy_fefo = date.today()
    lotes_cache = list(p.lotes.all())

    # Lotes con cantidad > 0 (para stock)
    lotes_con_stock = [l for l in lotes_cache if (l.cantidad or 0) > 0]
    lotes_data = []
    for lote in sorted(lotes_con_stock, key=lambda l: (l.fecha_caducidad or date(9999, 12, 31))):
        dias_lote = (lote.fecha_caducidad - hoy_fefo).days if lote.fecha_caducidad else None
        es_vencido = bool(lote.fecha_caducidad and lote.fecha_caducidad < hoy_fefo)
        lotes_data.append({
            'id': lote.id,
            'numero_lote': lote.numero_lote,
            'fecha_caducidad': lote.fecha_caducidad.strftime('%Y-%m-%d') if lote.fecha_caducidad else None,
            'cantidad': float(lote.cantidad or 0),
            'costo_adquisicion': float(lote.costo_adquisicion or 0),
            'dias_restantes': dias_lote,
            'es_vencido': es_vencido,
        })

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

    # stock_total_fisico: suma de TODOS los lotes (incluidos caducados) — para conteo físico ERP
    stock_total_fisico = sum(l.cantidad for l in lotes_con_stock) if lotes_con_stock else float(p.stock or 0)

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
        'stock_total_fisico': float(stock_total_fisico),
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
    return JsonResponse({'producto': producto_data, 'lotes': lotes_data})


# ==============================================================================
# API: BUSCAR PRODUCTO PDV
# ==============================================================================

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


# ==============================================================================
# FRAGMENTO: BUSCAR PRODUCTO PDV
# ==============================================================================

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


# ==============================================================================
# PDV FARMACIA - CONTROLADOR PRINCIPAL
# ==============================================================================

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
        sugerencias_por_paciente = {}
        sugerencias_sistema_count = 0
    
    context = {
        'empresa': empresa,
        'usuario': request.user,
        'puede_precio_neto': puede_precio_neto,
        'puede_usar_ia': puede_usar_ia,
        'sugerencias_por_paciente': sugerencias_por_paciente,
        'sugerencias_sistema_count': sugerencias_sistema_count,
        'es_admin': es_admin,
    }
    
    return render(request, 'core/pdv_farmacia.html', context)


# ==============================================================================
# PROCESAR VENTA
# ==============================================================================

def procesar_venta(request, data, empresa):
    """Delega al servicio de dominio PDV (transaction.atomic en capa servicio)."""
    return VentaFarmaciaService.ejecutar_venta_pdv(request, data, empresa)


# ==============================================================================
# HELPER: BUSCAR PRODUCTOS PDV
# ==============================================================================

def _buscar_productos_pdv_resultados(empresa, termino):
    """Helper para buscar productos en el PDV."""
    return VentaFarmaciaService.buscar_productos_pdv(empresa, termino)
