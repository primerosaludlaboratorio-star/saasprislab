"""
Vistas de Compras y Abastecimiento Express para Farmacia
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction, DatabaseError, IntegrityError
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import json

from core.models import Producto, Lote
from core.utils.sucursal_helpers import get_user_primary_sucursal
from farmacia.models import MovimientoInventario, Proveedor
from farmacia.forms import RegistrarCompraForm, DetalleCompraForm


@login_required
@permission_required('farmacia.add_movimientoinventario', raise_exception=True)
def registrar_compra(request):
    """
    Vista para registrar compras a proveedores con cálculo de CPP.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada. Contacte al administrador.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        accion = request.POST.get('accion', 'guardar')
        
        if accion == 'guardar_completo':
            try:
                with transaction.atomic():
                    proveedor_id = request.POST.get('proveedor')
                    documento_compra = request.POST.get('documento_compra')
                    fecha_compra_str = request.POST.get('fecha_compra')
                    
                    proveedor = get_object_or_404(Proveedor, id=proveedor_id, empresa=empresa)
                    items_compra = request.session.get('items_compra_temp', [])
                    
                    if not items_compra:
                        messages.error(request, '⚠️ No hay productos en la compra. Agrega al menos uno.')
                        return redirect('farmacia:registrar_compra')
                    
                    total_productos = 0
                    total_valor = Decimal('0.00')
                    
                    for item in items_compra:
                        producto = get_object_or_404(Producto, id=item['producto_id'], empresa=empresa)
                        cantidad = Decimal(str(item['cantidad']))
                        costo_unitario = Decimal(str(item['costo_unitario']))
                        numero_lote = item['numero_lote']
                        fecha_caducidad = datetime.strptime(item['fecha_caducidad'], '%Y-%m-%d').date()
                        marca = item.get('marca', '')
                        
                        if marca and marca != producto.marca_laboratorio:
                            producto.marca_laboratorio = marca
                            producto.save(update_fields=['marca_laboratorio'])
                        
                        lote, lote_creado = Lote.objects.get_or_create(
                            producto=producto,
                            numero_lote=numero_lote,
                            defaults={
                                'fecha_caducidad': fecha_caducidad,
                                'cantidad': Decimal('0'),
                                'costo_adquisicion': costo_unitario
                            }
                        )
                        
                        if not lote_creado:
                            cantidad_anterior = lote.cantidad
                            if cantidad_anterior > 0:
                                lote.costo_adquisicion = (
                                    (cantidad_anterior * lote.costo_adquisicion + cantidad * costo_unitario) /
                                    (cantidad_anterior + cantidad)
                                )
                        
                        movimiento = MovimientoInventario(
                            empresa=empresa,
                            sucursal=get_user_primary_sucursal(request.user),
                            producto=producto,
                            lote=lote,
                            tipo_movimiento='ENTRADA_COMPRA',
                            cantidad=cantidad,
                            costo_unitario=costo_unitario,
                            usuario_responsable=request.user,
                            proveedor=proveedor,
                            observaciones=f"Compra a {proveedor.razon_social}. Doc: {documento_compra}",
                            documento_referencia=documento_compra
                        )
                        movimiento.save()
                        
                        total_productos += 1
                        total_valor += cantidad * costo_unitario
                    
                    request.session['items_compra_temp'] = []
                    
                    from core.models import AuditLog
                    AuditLog.objects.create(
                        empresa=empresa,
                        usuario=request.user,
                        accion=AuditLog.ACCION_CREATE,
                        modelo_afectado='Compra',
                        objeto_id='0',
                        datos_anteriores=None,
                        datos_nuevos={
                            'proveedor': proveedor.razon_social,
                            'documento': documento_compra,
                            'total_productos': total_productos,
                            'total_valor': str(total_valor),
                            'fecha_compra': fecha_compra_str
                        },
                        sucursal=get_user_primary_sucursal(request.user),
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                    )
                    
                    messages.success(
                        request,
                        f'✅ Compra registrada exitosamente. '
                        f'{total_productos} productos agregados al inventario. '
                        f'Valor total: ${total_valor:,.2f}'
                    )
                    return redirect('farmacia:kardex_list')
                    
            except (DatabaseError, ValueError, TypeError, InvalidOperation, ValidationError) as e:
                messages.error(request, f'❌ Error al registrar compra: {str(e)}')
                return redirect('farmacia:registrar_compra')
    
    form_compra = RegistrarCompraForm(empresa=empresa)
    form_detalle = DetalleCompraForm(empresa=empresa)
    
    items_temp = request.session.get('items_compra_temp', [])
    total_temp = sum(
        Decimal(str(item['cantidad'])) * Decimal(str(item['costo_unitario']))
        for item in items_temp
    )
    
    return render(request, 'farmacia/registrar_compra.html', {
        'form_compra': form_compra,
        'form_detalle': form_detalle,
        'items_temp': items_temp,
        'total_temp': total_temp
    })


@login_required
def api_agregar_producto_compra(request):
    """
    API para agregar productos a la compra temporal (en sesion).
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            producto_id = data.get('producto_id')
            cantidad = Decimal(str(data.get('cantidad', 0)))
            costo_unitario = Decimal(str(data.get('costo_unitario', 0)))
            numero_lote = data.get('numero_lote', '').strip().upper()
            fecha_caducidad = data.get('fecha_caducidad')
            marca = data.get('marca', '').strip()
            
            if not all([producto_id, cantidad > 0, costo_unitario > 0, numero_lote, fecha_caducidad]):
                return JsonResponse({
                    'status': 'error',
                    'mensaje': 'Todos los campos son obligatorios'
                }, status=400)
            
            producto = get_object_or_404(Producto, id=producto_id, empresa=getattr(request.user, 'empresa', None))
            
            if 'items_compra_temp' not in request.session:
                request.session['items_compra_temp'] = []
            
            item = {
                'producto_id': producto.id,
                'producto_nombre': producto.nombre,
                'cantidad': str(cantidad),
                'costo_unitario': str(costo_unitario),
                'subtotal': str(cantidad * costo_unitario),
                'numero_lote': numero_lote,
                'fecha_caducidad': fecha_caducidad,
                'marca': marca or producto.marca_laboratorio or 'GENERICO'
            }
            
            request.session['items_compra_temp'].append(item)
            request.session.modified = True
            
            return JsonResponse({
                'status': 'success',
                'mensaje': f'Lote {numero_lote} de {producto.nombre} agregado',
                'item': item,
                'total_items': len(request.session['items_compra_temp'])
            })
            
        except (DatabaseError, ValueError, TypeError, InvalidOperation, ValidationError) as e:
            return JsonResponse({
                'status': 'error',
                'mensaje': f'Error: {str(e)}'
            }, status=500)
    
    return JsonResponse({'status': 'error', 'mensaje': 'Metodo no permitido'}, status=405)


@login_required
def api_agregar_multi_lote(request):
    """
    API para agregar multiples lotes de un mismo producto a la compra temporal.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            producto_id = data.get('producto_id')
            lotes = data.get('lotes', [])
            
            if not producto_id or not lotes:
                return JsonResponse({
                    'status': 'error',
                    'mensaje': 'Se requiere producto_id y al menos un lote'
                }, status=400)
            
            producto = get_object_or_404(Producto, id=producto_id, empresa=getattr(request.user, 'empresa', None))
            
            if 'items_compra_temp' not in request.session:
                request.session['items_compra_temp'] = []
            
            items_agregados = []
            for lote_data in lotes:
                cantidad = Decimal(str(lote_data.get('cantidad', 0)))
                costo_unitario = Decimal(str(lote_data.get('costo_unitario', 0)))
                numero_lote = lote_data.get('numero_lote', '').strip().upper()
                fecha_caducidad = lote_data.get('fecha_caducidad')
                marca = lote_data.get('marca', '').strip()
                
                if not all([cantidad > 0, costo_unitario > 0, numero_lote, fecha_caducidad]):
                    continue
                
                item = {
                    'producto_id': producto.id,
                    'producto_nombre': producto.nombre,
                    'cantidad': str(cantidad),
                    'costo_unitario': str(costo_unitario),
                    'subtotal': str(cantidad * costo_unitario),
                    'numero_lote': numero_lote,
                    'fecha_caducidad': fecha_caducidad,
                    'marca': marca or producto.marca_laboratorio or 'GENERICO'
                }
                
                request.session['items_compra_temp'].append(item)
                items_agregados.append(item)
            
            request.session.modified = True
            
            return JsonResponse({
                'status': 'success',
                'mensaje': f'{len(items_agregados)} lote(s) de {producto.nombre} agregados',
                'items': items_agregados,
                'total_items': len(request.session['items_compra_temp'])
            })
            
        except (DatabaseError, ValueError, TypeError, InvalidOperation, ValidationError) as e:
            return JsonResponse({
                'status': 'error',
                'mensaje': f'Error: {str(e)}'
            }, status=500)
    
    return JsonResponse({'status': 'error', 'mensaje': 'Metodo no permitido'}, status=405)


@login_required
def api_eliminar_producto_compra(request, index):
    """
    API para eliminar un producto de la compra temporal.
    """
    try:
        items = request.session.get('items_compra_temp', [])
        if 0 <= index < len(items):
            item_eliminado = items.pop(index)
            request.session['items_compra_temp'] = items
            request.session.modified = True
            
            return JsonResponse({
                'status': 'success',
                'mensaje': f'Producto {item_eliminado["producto_nombre"]} eliminado'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Índice inválido'
            }, status=400)
    except (TypeError, ValueError, KeyError, IndexError) as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error: {str(e)}'
        }, status=500)


@login_required
def entrada_express(request):
    """
    Ingreso rápido de mercancía por AJAX.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
        
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
        
        codigo_barras = data.get('codigo_barras', '').strip()
        try:
            cantidad = int(data.get('cantidad', 0))
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'error': 'Cantidad debe ser un número entero válido.'}, status=400)
        numero_lote = data.get('numero_lote', '').strip()
        fecha_caducidad = data.get('fecha_caducidad')
        try:
            precio_compra = Decimal(str(data.get('precio_compra', '0.00')))
        except (ValueError, TypeError, InvalidOperation):
            precio_compra = Decimal('0.00')
        
        if not codigo_barras or cantidad <= 0 or not numero_lote or not fecha_caducidad:
            return JsonResponse({
                'success': False,
                'error': 'Datos incompletos. Se requiere: código, cantidad, lote y caducidad.'
            }, status=400)
        
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return JsonResponse({'success': False, 'error': 'Usuario sin empresa asignada.'}, status=403)
        producto = Producto.objects.filter(codigo_barras=codigo_barras, empresa=empresa).first()
        
        if not producto:
            return JsonResponse({
                'success': False,
                'error': f'Producto con código {codigo_barras} no encontrado. Debe registrarlo primero.'
            }, status=404)
        
        fecha_caducidad_dt = datetime.strptime(fecha_caducidad, '%Y-%m-%d').date()
        
        with transaction.atomic():
            costo = precio_compra if precio_compra > 0 else (producto.precio_compra or Decimal('0.01'))
            
            lote, created = Lote.objects.get_or_create(
                producto=producto,
                numero_lote=numero_lote,
                defaults={
                    'fecha_caducidad': fecha_caducidad_dt,
                    'fecha_fabricacion': date.today(),
                    'cantidad': 0,
                    'costo_adquisicion': costo,
                }
            )
            
            if not created and lote.fecha_caducidad != fecha_caducidad_dt:
                return JsonResponse({
                    'success': False,
                    'error': f'El lote {numero_lote} ya existe con fecha de caducidad diferente.'
                }, status=400)
            
            MovimientoInventario.objects.create(
                empresa=getattr(request.user, 'empresa', None),
                sucursal=get_user_primary_sucursal(request.user),
                producto=producto,
                lote=lote,
                tipo_movimiento='ENTRADA_COMPRA',
                cantidad=Decimal(str(cantidad)),
                costo_unitario=costo,
                usuario_responsable=request.user,
                observaciones=f'Entrada Express (Restock Rápido) - Usuario: {request.user.username}',
            )
        
        return JsonResponse({
            'success': True,
            'message': f'{cantidad} unidades de {producto.nombre} agregadas al stock.',
            'producto': {
                'nombre': producto.nombre,
                'stock_total': producto.stock,
                'lote': numero_lote,
                'caducidad': fecha_caducidad,
            }
        })
        
    except (DatabaseError, ValueError, TypeError, InvalidOperation, ValidationError) as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar entrada: {str(e)}'
        }, status=500)
