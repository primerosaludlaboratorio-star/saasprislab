"""
Vistas de Devoluciones y Cancelaciones de Farmacia
"""
import json
import logging
from decimal import Decimal
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction, DatabaseError
from django.db.models import Q, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone

from core.models import Venta, DetalleVenta, SalesReturn, Pago
from core.utils.empresa_request import get_empresa_usuario
from core.utils.sucursal_helpers import get_request_sucursal
from farmacia.models import MermaFarmacia, MovimientoInventario, DevolucionVenta

logger = logging.getLogger('farmacia.devoluciones')


def _empresa_desde_request(request):
    """Empresa efectiva: EmpresaIdentityMiddleware o FK del usuario."""
    return getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)


def _total_devuelto_core(venta):
    return venta.devoluciones.aggregate(
        total=Coalesce(Sum('monto_reembolsado'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')


def _total_devuelto_erp(venta):
    return venta.devoluciones_farmacia.aggregate(
        total=Coalesce(Sum('monto_devolucion'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')


def _serializar_venta_para_devolucion(venta):
    total_devuelto_core = _total_devuelto_core(venta)
    total_devuelto_erp = _total_devuelto_erp(venta)
    total_devuelto = total_devuelto_core + total_devuelto_erp
    return {
        'venta': {
            'id': venta.id,
            'folio': venta.folio_operacion or str(venta.id),
            'fecha': venta.fecha.strftime('%Y-%m-%d %H:%M'),
            'total': str(venta.total),
            'cliente': venta.paciente.nombre_completo if venta.paciente else 'Cliente General',
            'vendedor': venta.usuario.get_full_name(),
            'cajero_original': venta.usuario.get_full_name(),
            'tiene_devoluciones': total_devuelto > Decimal('0.00'),
            'total_devuelto': str(total_devuelto),
            'disponible_devolver': str(venta.total - total_devuelto),
        },
        'detalles': [
            {
                'producto': detalle.producto.nombre,
                'cantidad': str(detalle.cantidad),
                'precio_unitario': str(detalle.precio_unitario),
                'subtotal': str(detalle.subtotal),
            }
            for detalle in venta.detalles.all()
        ],
    }


def _es_gerente_o_admin(user):
    """Requerido para procesar devoluciones (solo gerente/admin con empresa válida)."""
    if not get_empresa_usuario(user):
        return False
    if user.is_superuser or user.is_staff:
        return True
    rol = (getattr(user, 'rol', '') or '').upper().strip()
    if rol in ('ADMIN', 'ADMINISTRADOR', 'GERENTE'):
        return True
    return user.groups.filter(name__in=['Gerente', 'Administrador', 'Admin']).exists()


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
# BUSCAR VENTA PARA DEVOLUCIÓN (NUEVO API)
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
                'producto_nombre': d.producto.nombre,
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
                'cajero_original': cajero_original,
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
        
        if venta.estado != 'COMPLETADA':
            return JsonResponse({'status': 'error', 'mensaje': 'Solo se pueden devolver ventas completadas'}, status=400)
        
        dias_venta = (timezone.now() - venta.fecha).days
        if dias_venta > 7:
            return JsonResponse({'status': 'error', 'mensaje': 'Solo se pueden devolver ventas de los últimos 7 días'}, status=400)
        
        with transaction.atomic():
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
            
            for item in items_devolver:
                detalle_id = item.get('detalle_id')
                cantidad_devolver = Decimal(str(item.get('cantidad', 0)))
                
                if not detalle_id or cantidad_devolver <= 0:
                    continue
                
                detalle = get_object_or_404(DetalleVenta, id=detalle_id, venta=venta)
                
                if cantidad_devolver > detalle.cantidad:
                    return JsonResponse({
                        'status': 'error',
                        'mensaje': f'No se puede devolver más de {detalle.cantidad} unidades de {detalle.producto.nombre}'
                    }, status=400)
                
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
                
                try:
                    from core.services.inventario.movimiento_inventario_service import MovimientoInventarioService
                    MovimientoInventarioService.reponer_stock_devolucion(
                        empresa=empresa,
                        producto=detalle.producto,
                        lote=detalle.lote_vendido,
                        relative_path=None,
                        cantidad=cantidad_devolver,
                        usuario=request.user,
                        referencia=f'Devolución VTA-{venta.id}',
                    )
                except (DatabaseError, ValueError, TypeError) as e:
                    logger.error(f'Error al reponer stock en devolución: {str(e)}')
            
            devolucion.monto_total = total_devuelto
            devolucion.save()
            
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
                # Justificación: Auditoría secundaria no bloqueante.
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
        # Justificación: Boundary top-level de API para evitar crash de la solicitud.
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


# ==============================================================================
# BUSCAR VENTA PARA DEVOLUCIÓN
# ==============================================================================
@login_required
@require_http_methods(["GET", "POST"])
def buscar_venta_para_devolucion(request):
    """
    Busca una venta por folio para iniciar proceso de devolución.
    """
    if request.method == 'POST':
        try:
            folio = request.POST.get('folio', '').strip()
            empresa = getattr(request.user, 'empresa', None)
            if not empresa:
                return JsonResponse({
                    'success': False,
                    'error': 'Usuario sin empresa asignada'
                }, status=403)
            if not folio:
                return JsonResponse({
                    'success': False,
                    'error': 'Folio requerido'
                }, status=400)
            
            venta = Venta.objects.filter(empresa=empresa, folio_operacion=folio).first()
            
            if not venta:
                return JsonResponse({
                    'success': False,
                    'error': f'No se encontró venta con folio {folio}'
                }, status=404)
            
            payload = _serializar_venta_para_devolucion(venta)
            payload['success'] = True
            return JsonResponse(payload)
            
        except Exception as e:
            # Justificación: Boundary top-level de API para buscar venta en soporte.
            logger.error(f"Error buscando venta: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Error al buscar venta: {str(e)}'
            }, status=500)
    
    empresa = getattr(request.user, 'empresa', None)
    venta_prefill = None
    detalles_prefill = None
    folio_prefill = ''
    if empresa:
        venta_id = request.GET.get('venta_id')
        folio = (request.GET.get('folio') or '').strip()
        venta = None
        if venta_id:
            venta = Venta.objects.filter(empresa=empresa, id=venta_id).first()
        elif folio:
            venta = Venta.objects.filter(empresa=empresa, folio_operacion=folio).first()
        if venta:
            payload = _serializar_venta_para_devolucion(venta)
            venta_prefill = payload['venta']
            detalles_prefill = payload['detalles']
            folio_prefill = venta_prefill['folio']
    return render(request, 'farmacia/devoluciones/buscar_venta.html', {
        'venta_prefill': venta_prefill,
        'detalles_prefill': detalles_prefill,
        'folio_prefill': folio_prefill,
    })


# ==============================================================================
# PROCESAR DEVOLUCIÓN
# ==============================================================================
@login_required
@user_passes_test(_es_gerente_o_admin, login_url='/login/')
@require_POST
def procesar_devolucion(request):
    """
    Procesa una devolución parcial o total.
    Detecta automáticamente si la petición viene de la ruta core (PDV) o ERP.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'success': False, 'status': 'error', 'error': 'Usuario sin empresa asignada'}, status=403)
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'status': 'error', 'error': 'JSON inválido'}, status=400)

        venta_id = data.get('venta_id')
        if not venta_id:
            return JsonResponse({'success': False, 'status': 'error', 'error': 'Datos incompletos'}, status=400)

        venta = get_object_or_404(Venta, id=venta_id, empresa=empresa)

        sucursal = getattr(venta, 'sucursal', None) or get_request_sucursal(request)
        if not sucursal and venta.empresa:
            sucursal = venta.empresa.sucursales.filter(activa=True).first()
        if not sucursal:
            return JsonResponse({
                'success': False,
                'status': 'error',
                'error': 'No hay sucursal asignada a la venta ni al usuario. Configure una sucursal.'
            }, status=400)

        disponible = venta.total - _total_devuelto_core(venta) - _total_devuelto_erp(venta)

        es_erp = request.path.startswith('/farmacia/erp/')
        if es_erp:
            return _procesar_devolucion_erp(request, data, empresa, venta, sucursal, disponible)
        return _procesar_devolucion_core(request, data, empresa, venta, sucursal, disponible)

    except Exception as e:
        # Justificación: Boundary top-level de API para procesar devolución.
        logger.error(f"Error procesando devolución: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'status': 'error',
            'error': f'Error al procesar devolución: {str(e)}'
        }, status=500)


def _procesar_devolucion_core(request, data, empresa, venta, sucursal, disponible):
    """Ruta PDV/core: usa SalesReturn con los nombres de campo del frontend."""
    tipo_devolucion = (data.get('tipo_devolucion') or 'TOTAL').upper()
    monto_reembolsado = Decimal(data.get('monto_reembolsado', '0.00'))
    motivo_error = data.get('motivo_error', '')
    accion_stock = (data.get('accion_stock') or 'REINGRESAR').upper()
    productos = data.get('productos') or data.get('productos_devueltos') or []

    if not tipo_devolucion or not motivo_error:
        return JsonResponse({'status': 'error', 'error': 'Datos incompletos'}, status=400)

    if tipo_devolucion == 'PARCIAL' and not productos:
        return JsonResponse({
            'status': 'error',
            'error': 'La devolución parcial requiere productos devueltos.',
            'codigo': 'DEVOLUCION_PARCIAL_REQUIERE_DETALLE',
        }, status=400)

    if monto_reembolsado > disponible:
        return JsonResponse({
            'status': 'error',
            'error': f'Monto excede lo disponible para devolución (${disponible})'
        }, status=400)

    accion_stock_model = 'RETORNO_ALMACEN' if accion_stock == 'REINGRESAR' else 'MERMA_DESECHO'
    observaciones = ''
    if productos:
        observaciones = 'productos_devueltos: ' + json.dumps(productos)

    with transaction.atomic():
        venta = Venta.objects.select_for_update().get(id=venta.id, empresa=empresa)
        disponible = venta.total - _total_devuelto_core(venta) - _total_devuelto_erp(venta)
        if monto_reembolsado > disponible:
            return JsonResponse({
                'status': 'error',
                'error': f'Monto excede lo disponible para devolución (${disponible})'
            }, status=400)

        devolucion = SalesReturn.objects.create(
            empresa=empresa,
            venta_original=venta,
            tipo_devolucion=tipo_devolucion,
            monto_reembolsado=monto_reembolsado,
            motivo_error=motivo_error,
            usuario_error_origen=request.user,
            usuario_autorizo=request.user,
            accion_stock=accion_stock_model,
            observaciones=observaciones,
        )

        if accion_stock_model == 'RETORNO_ALMACEN':
            for detalle in venta.detalles.all():
                try:
                    lote = getattr(detalle, 'lote_vendido', None) or getattr(detalle, 'lote', None)
                    costo = detalle.precio_unitario or getattr(detalle.producto, 'precio_compra', None) or Decimal('0.01')
                    MovimientoInventario.objects.create(
                        empresa=venta.empresa,
                        sucursal=sucursal,
                        producto=detalle.producto,
                        lote=lote,
                        tipo_movimiento='ENTRADA_DEVOLUCION',
                        cantidad=Decimal(str(detalle.cantidad)),
                        costo_unitario=costo,
                        usuario_responsable=request.user,
                        observaciones=f'Reingreso por devolución core {devolucion.id}: {motivo_error}'
                    )
                except (DatabaseError, ValueError, TypeError) as e_mov:
                    logger.warning(f"Kardex reingreso falló para {detalle.producto}: {e_mov}. Ajuste manual.")
                    detalle.producto.stock += detalle.cantidad
                    detalle.producto.save(update_fields=['stock'])
            logger.info(f"Mercancía de devolución core {devolucion.id} reingresada al stock")
        else:
            for detalle in venta.detalles.all():
                lote = getattr(detalle, 'lote_vendido', None) or getattr(detalle, 'lote', None)
                if not lote:
                    lote = detalle.producto.lotes.filter(cantidad__gt=0).order_by('fecha_caducidad').first()
                if not lote:
                    logger.warning(
                        f"Devolución core {devolucion.id}: detalle sin lote para {detalle.producto.nombre}; "
                        "omitiendo merma (sin stock en lotes)."
                    )
                    continue
                MermaFarmacia.objects.create(
                    empresa=venta.empresa,
                    sucursal=sucursal,
                    producto=detalle.producto,
                    lote=lote,
                    cantidad=detalle.cantidad,
                    motivo='DEVOLUCION_CLIENTE',
                    justificacion_qc=f'Devolución core {devolucion.id}: {motivo_error}',
                    usuario_reporta=request.user
                )

        return JsonResponse({
            'status': 'success',
            'success': True,
            'devolucion_id': devolucion.id,
            'message': 'Devolución procesada correctamente.'
        })


def _procesar_devolucion_erp(request, data, empresa, venta, sucursal, disponible):
    """Ruta ERP: usa farmacia.models.DevolucionVenta con sus nombres de campo."""
    tipo = data.get('tipo')
    monto = Decimal(data.get('monto', '0.00'))
    motivo = data.get('motivo')
    motivo_detallado = data.get('motivo_detallado', '')
    reingresar_stock = data.get('reingresar_stock', True)

    if not tipo or not motivo:
        return JsonResponse({'success': False, 'error': 'Datos incompletos'}, status=400)

    if monto > disponible:
        return JsonResponse({
            'success': False,
            'error': f'Monto excede lo disponible para devolución (${disponible})'
        }, status=400)

    if tipo == 'PARCIAL':
        return JsonResponse({
            'success': False,
            'error': (
                'La devolución parcial aún requiere captura por producto/cantidad. '
                'Use devolución TOTAL o espere la captura detallada.'
            ),
            'codigo': 'DEVOLUCION_PARCIAL_REQUIERE_DETALLE',
        }, status=400)

    with transaction.atomic():
        venta = Venta.objects.select_for_update().get(id=venta.id, empresa=empresa)
        disponible = venta.total - _total_devuelto_core(venta) - _total_devuelto_erp(venta)
        if monto > disponible:
            return JsonResponse({
                'success': False,
                'error': f'Monto excede lo disponible para devolución (${disponible})'
            }, status=400)

        devolucion = DevolucionVenta.objects.create(
            empresa=venta.empresa,
            sucursal=sucursal,
            venta_original=venta,
            tipo=tipo,
            motivo=motivo,
            motivo_detallado=motivo_detallado,
            monto_devolucion=monto,
            reingresar_a_stock=reingresar_stock,
            usuario_procesa=request.user
        )
        try:
            from core.services.audit_service import registrar_auditoria
            registrar_auditoria(
                accion='CREATE',
                modelo='DevolucionVenta',
                objeto_id=str(devolucion.id),
                datos_anteriores=None,
                datos_nuevos={
                    'folio': getattr(devolucion, 'folio', ''),
                    'tipo': tipo,
                    'motivo': motivo,
                    'monto_devolucion': str(monto),
                    'reingresar_a_stock': reingresar_stock,
                    'venta_id': venta.id,
                },
                request=request,
            )
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en _procesar_devolucion_erp (devoluciones.py)")
            # Justificación: Auditoría secundaria no bloqueante.
            pass

        if devolucion.requiere_autorizacion:
            return JsonResponse({
                'success': True,
                'requiere_autorizacion': True,
                'folio': devolucion.folio,
                'message': f'Devolución {devolucion.folio} creada. Requiere autorización gerencial (monto > $500).'
            })

        devolucion.autorizado = True
        devolucion.save(update_fields=['autorizado'])

        if reingresar_stock:
            for detalle in venta.detalles.all():
                try:
                    lote = getattr(detalle, 'lote_vendido', None) or getattr(detalle, 'lote', None)
                    costo = detalle.precio_unitario or getattr(detalle.producto, 'precio_compra', None) or Decimal('0.01')
                    MovimientoInventario.objects.create(
                        empresa=venta.empresa,
                        sucursal=sucursal,
                        producto=detalle.producto,
                        lote=lote,
                        tipo_movimiento='ENTRADA_DEVOLUCION',
                        cantidad=Decimal(str(detalle.cantidad)),
                        costo_unitario=costo,
                        usuario_responsable=request.user,
                        observaciones=f'Reingreso por devolución {devolucion.folio}: {motivo_detallado}'
                    )
                except (DatabaseError, ValueError, TypeError) as e_mov:
                    logger.warning(f"Kardex reingreso falló para {detalle.producto}: {e_mov}. Ajuste manual.")
                    detalle.producto.stock += detalle.cantidad
                    detalle.producto.save(update_fields=['stock'])
            logger.info(f"Mercancía de {devolucion.folio} reingresada al stock")
        else:
            for detalle in venta.detalles.all():
                lote = getattr(detalle, 'lote_vendido', None) or getattr(detalle, 'lote', None)
                if not lote:
                    lote = detalle.producto.lotes.filter(cantidad__gt=0).order_by('fecha_caducidad').first()
                if not lote:
                    logger.warning(
                        f"Devolución {devolucion.folio}: detalle sin lote para {detalle.producto.nombre}; "
                        "omitiendo merma (sin stock en lotes)."
                    )
                    continue
                MermaFarmacia.objects.create(
                    empresa=venta.empresa,
                    sucursal=sucursal,
                    producto=detalle.producto,
                    lote=lote,
                    cantidad=detalle.cantidad,
                    motivo='DEVOLUCION_CLIENTE',
                    justificacion_qc=f'Devolución {devolucion.folio}: {motivo_detallado}',
                    usuario_reporta=request.user
                )

        devolucion.procesada = True
        devolucion.save(update_fields=['procesada'])

        return JsonResponse({
            'success': True,
            'folio': devolucion.folio,
            'message': f'Devolución {devolucion.folio} procesada correctamente.'
        })


# ==============================================================================
# DASHBOARD DEVOLUCIONES
# ==============================================================================
@login_required
def dashboard_devoluciones(request):
    """
    Dashboard para gestión de devoluciones.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return render(request, 'farmacia/devoluciones/dashboard.html', {'pendientes': [], 'procesadas': []})
    sucursal = get_request_sucursal(request)
    
    pendientes = DevolucionVenta.objects.filter(
        empresa=empresa,
        sucursal=sucursal,
        requiere_autorizacion=True,
        autorizado=False
    ).select_related('venta_original', 'usuario_procesa').order_by('-fecha_devolucion')
    
    procesadas = DevolucionVenta.objects.filter(
        empresa=empresa,
        sucursal=sucursal,
        procesada=True
    ).select_related('venta_original', 'usuario_procesa').order_by('-fecha_devolucion')[:50]
    
    context = {
        'pendientes': pendientes,
        'procesadas': procesadas,
    }
    
    return render(request, 'farmacia/devoluciones/dashboard.html', context)


# ==============================================================================
# AUTORIZAR DEVOLUCIÓN
# ==============================================================================
@login_required
@require_POST
def autorizar_devolucion(request, devolucion_id):
    """
    Autoriza una devolución que requiere aprobación gerencial.
    Solo accesible para DIRECTOR.
    """
    if not request.user.groups.filter(name='DIRECTOR').exists():
        return JsonResponse({
            'success': False,
            'error': 'Sin permisos para autorizar devoluciones'
        }, status=403)
    
    try:
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return JsonResponse({'success': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        devolucion = get_object_or_404(DevolucionVenta, id=devolucion_id, empresa=empresa)
        
        if not devolucion.requiere_autorizacion:
            return JsonResponse({
                'success': False,
                'error': 'Esta devolución no requiere autorización'
            }, status=400)
        
        if devolucion.autorizado:
            return JsonResponse({
                'success': False,
                'error': 'Esta devolución ya fue autorizada'
            }, status=400)
        
        with transaction.atomic():
            devolucion.autorizado = True
            devolucion.autorizado_por = request.user
            devolucion.save(update_fields=['autorizado', 'autorizado_por'])
            devolucion.procesar_devolucion()
        
        return JsonResponse({
            'success': True,
            'message': f'Devolución {devolucion.folio} autorizada and procesada.'
        })
        
    except Exception as e:
        # Justificación: Boundary top-level de API para autorización de devoluciones.
        logger.error(f"Error autorizando devolución: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error: {str(e)}'
        }, status=500)