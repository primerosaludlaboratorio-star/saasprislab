"""
Vistas de Devoluciones de Farmacia
Incluye: historial de devoluciones, búsqueda de venta para devolución, procesamiento de devoluciones
"""

import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger('farmacia.devoluciones')

from core.models import (
    Venta, DetalleVenta, Pago, SalesReturn, DevolucionVenta, Empresa
)
from core.utils.empresa_request import get_empresa_usuario


def _empresa_desde_request(request):
    """Empresa efectiva: EmpresaIdentityMiddleware (fallback principal) o FK del usuario."""
    return getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)


# ==============================================================================
# HISTORIAL DE DEVOLUCIONES
# ==============================================================================

@login_required
def historial_devoluciones(request):
    """Vista para historial de devoluciones."""
    empresa = _empresa_desde_request(request)
    if not empresa:
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
        'fecha_seleccionada_str': fecha_seleccionada.strftime('%Y-%m-%d')
    })


# ==============================================================================
# BUSCAR VENTA PARA DEVOLUCIÓN
# ==============================================================================

@login_required
def buscar_venta_devolucion(request):
    """API para buscar venta para devolución."""
    busqueda = request.GET.get('busqueda', '').strip() or request.GET.get('folio', '').strip()
    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    if not busqueda:
        return JsonResponse({'status': 'error', 'mensaje': 'Proporcione un folio o término de búsqueda'}, status=400)
    try:
        venta = Venta.objects.select_related('paciente', 'usuario').prefetch_related('detalles__producto').get(
            folio_operacion=busqueda, empresa=empresa
        )
        cliente = ''
        if venta.paciente:
            cliente = getattr(venta.paciente, 'nombre_completo', '') or ''
        if not cliente and venta.paciente_nombre:
            cliente = venta.paciente_nombre
        if not cliente:
            cliente = 'Público General'
        cajero_original = getattr(venta.usuario, 'get_full_name', lambda: '')() or venta.usuario.username
        detalles = []
        for d in venta.detalles.all():
            detalles.append({
                'id': d.id,
                'producto': d.producto.nombre,
                'cantidad': d.cantidad,
                'precio_unitario': float(d.precio_unitario),
                'subtotal': float(d.subtotal),
                'lote': d.lote_vendido.numero_lote if d.lote_vendido else '',
            })
        
        return JsonResponse({
            'status': 'success',
            'venta': {
                'id': venta.id,
                'folio': venta.folio_operacion,
                'fecha': venta.fecha.strftime('%Y-%m-%d %H:%M'),
                'cliente': cliente,
                'cajero': cajero_original,
                'total': float(venta.total),
                'detalles': detalles,
            }
        })
    except Venta.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Venta no encontrada'}, status=404)


# ==============================================================================
# PROCESAR DEVOLUCIÓN DE VENTA
# ==============================================================================

@login_required
def procesar_devolucion_venta(request):
    """Procesa una devolución de venta."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)
    
    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    
    try:
        data = json.loads(request.body)
        venta_id = data.get('venta_id')
        motivo = data.get('motivo', '').strip()
        items_devolver = data.get('items', [])
        
        if not venta_id:
            return JsonResponse({'status': 'error', 'mensaje': 'Venta ID requerido'}, status=400)
        if not motivo:
            return JsonResponse({'status': 'error', 'mensaje': 'Motivo requerido'}, status=400)
        if not items_devolver:
            return JsonResponse({'status': 'error', 'mensaje': 'No hay items para devolver'}, status=400)
        
        venta = get_object_or_404(Venta, id=venta_id, empresa=empresa)
        
        # Validar que la venta esté completada
        if venta.estado != 'COMPLETADA':
            return JsonResponse({'status': 'error', 'mensaje': 'Solo se pueden devolver ventas completadas'}, status=400)
        
        # Validar que la venta no tenga más de 7 días (política de devolución)
        dias_venta = (timezone.now() - venta.fecha).days
        if dias_venta > 7:
            return JsonResponse({'status': 'error', 'mensaje': 'Solo se pueden devolver ventas de los últimos 7 días'}, status=400)
        
        with transaction.atomic():
            # Crear DevolucionVenta
            devolucion = DevolucionVenta(
                empresa=empresa,
                venta=venta,
                usuario=request.user,
                motivo=motivo,
                fecha_devolucion=timezone.now(),
                monto_total=Decimal('0.00'),
            )
            devolucion.save()
            
            total_devuelto = Decimal('0.00')
            
            # Procesar cada item
            for item in items_devolver:
                detalle_id = item.get('detalle_id')
                cantidad_devolver = Decimal(str(item.get('cantidad', 0)))
                
                if not detalle_id or cantidad_devolver <= 0:
                    continue
                
                detalle = get_object_or_404(DetalleVenta, id=detalle_id, venta=venta)
                
                # Validar que no se devuelva más de lo vendido
                if cantidad_devolver > detalle.cantidad:
                    return JsonResponse({
                        'status': 'error',
                        'mensaje': f'No se puede devolver más de {detalle.cantidad} unidades de {detalle.producto.nombre}'
                    }, status=400)
                
                # Crear SalesReturn
                sales_return = SalesReturn(
                    empresa=empresa,
                    venta=venta,
                    devolucion=devolucion,
                    producto=detalle.producto,
                    lote=detalle.lote_vendido,
                    cantidad=cantidad_devolver,
                    precio_unitario=detalle.precio_unitario,
                    subtotal=detalle.precio_unitario * cantidad_devolver,
                    motivo=motivo,
                    usuario=request.user,
                )
                sales_return.save()
                
                total_devuelto += sales_return.subtotal
                
                # Reponer stock (usar servicio de inventario)
                try:
                    from core.services.inventario.movimiento_inventario_service import MovimientoInventarioService
                    MovimientoInventarioService.reponer_stock_devolucion(
                        empresa=empresa,
                        producto=detalle.producto,
                        lote=detalle.lote_vendido,
                        cantidad=cantidad_devolver,
                        usuario=request.user,
                        referencia=f'Devolución VTA-{venta.id}',
                    )
                except Exception as e:
                    logger.error(f'Error al reponer stock en devolución: {str(e)}')
            
            # Actualizar monto total de la devolución
            devolucion.monto_total = total_devuelto
            devolucion.save()
            
            # Registrar en AuditLog
            try:
                from core.services.audit_service import registrar_auditoria
                registrar_auditoria(
                    accion='CREATE',
                    modelo='DevolucionVenta',
                    objeto_id=str(devolucion.id),
                    datos_nuevos={
                        'venta_id': venta.id,
                        'folio_venta': venta.folio_operacion,
                        'motivo': motivo,
                        'monto_total': str(total_devuelto),
                    },
                    request=request,
                )
            except Exception as e:
                logger.error(f'Error al registrar auditoría de devolución: {str(e)}')
            
            return JsonResponse({
                'status': 'success',
                'mensaje': f'Devolución procesada exitosamente. Total devuelto: ${total_devuelto:,.2f}',
                'devolucion_id': devolucion.id,
                'monto_devuelto': float(total_devuelto),
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
    except Exception as e:
        logger.error(f'Error al procesar devolución: {str(e)}')
        return JsonResponse({'status': 'error', 'mensaje': f'Error al procesar devolución: {str(e)}'}, status=500)


# ==============================================================================
# DETALLE DE DEVOLUCIÓN
# ==============================================================================

@login_required
def detalle_devolucion(request, devolucion_id):
    """Vista para ver el detalle de una devolución."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    devolucion = get_object_or_404(DevolucionVenta, id=devolucion_id, empresa=empresa)
    sales_returns = SalesReturn.objects.filter(devolucion=devolucion).select_related('producto', 'lote')
    
    return render(request, 'core/detalle_devolucion.html', {
        'empresa': empresa,
        'devolucion': devolucion,
        'sales_returns': sales_returns,
    })
