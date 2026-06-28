"""
Módulo de Transferencias entre Sucursales - PRISLAB
Gestión de transferencias de inventario entre sucursales.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
from datetime import datetime

from core.models import Empresa, Sucursal, Producto, Lote, Usuario
from logistica.models import TransferenciaInventario, DetalleTransferencia
from core.utils.trazabilidad import registrar_trazabilidad, serializar_modelo
import logging
@login_required
def lista_transferencias(request):
    """Lista de transferencias de inventario."""
    empresa = getattr(request.user, 'empresa', None)
    
    # Filtros
    estado = request.GET.get('estado', '')
    sucursal_origen_id = request.GET.get('sucursal_origen', '')
    sucursal_destino_id = request.GET.get('sucursal_destino', '')
    
    transferencias = TransferenciaInventario.objects.filter(empresa=empresa).select_related(
        'sucursal_origen', 'sucursal_destino', 'solicitado_por'
    ).order_by('-fecha_creacion')
    
    if estado:
        transferencias = transferencias.filter(estado=estado)
    if sucursal_origen_id:
        transferencias = transferencias.filter(sucursal_origen_id=sucursal_origen_id)
    if sucursal_destino_id:
        transferencias = transferencias.filter(sucursal_destino_id=sucursal_destino_id)
    
    # Paginación
    paginator = Paginator(transferencias, 20)
    page = request.GET.get('page')
    transferencias_pag = paginator.get_page(page)
    
    sucursales = Sucursal.objects.filter(empresa=empresa, activa=True)
    
    return render(request, 'core/transferencias/lista_transferencias.html', {
        'empresa': empresa,
        'transferencias': transferencias_pag,
        'sucursales': sucursales,
        'estado': estado,
        'sucursal_origen_id': sucursal_origen_id,
        'sucursal_destino_id': sucursal_destino_id,
    })


@login_required
@require_http_methods(["GET", "POST"])
def crear_transferencia(request):
    """Crear una nueva transferencia de inventario."""
    empresa = getattr(request.user, 'empresa', None)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Generar folio
                timestamp = timezone.localtime(timezone.now()).strftime('%Y%m%d%H%M%S')
                folio = f'TRF-{timestamp}'
                
                # Crear transferencia
                transferencia = TransferenciaInventario.objects.create(
                    empresa=empresa,
                    sucursal_origen_id=request.POST.get('sucursal_origen'),
                    sucursal_destino_id=request.POST.get('sucursal_destino'),
                    motivo=request.POST.get('observaciones', '').strip(),
                    solicitado_por=request.user,
                    estado='BORRADOR'
                )
                
                # Procesar detalles
                productos_data = request.POST.getlist('productos[]')
                cantidades_data = request.POST.getlist('cantidades[]')
                lotes_data = request.POST.getlist('lotes[]')
                
                for idx, producto_id in enumerate(productos_data):
                    if not producto_id:
                        continue
                    
                    producto = get_object_or_404(Producto, id=producto_id, empresa=empresa)
                    cantidad = int(cantidades_data[idx] if idx < len(cantidades_data) else 0)
                    lote_id = lotes_data[idx] if idx < len(lotes_data) else None
                    
                    if cantidad <= 0:
                        continue
                    
                    # Verificar stock disponible en sucursal origen
                    if producto.sucursal != transferencia.sucursal_origen:
                        messages.warning(request, f'El producto {producto.nombre} no está disponible en la sucursal origen')
                        continue
                    
                    if producto.stock < cantidad:
                        messages.warning(request, f'Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}')
                        continue
                    
                    lote_obj = None
                    if lote_id:
                        lote_obj = get_object_or_404(Lote, id=lote_id, producto=producto)
                    
                    DetalleTransferencia.objects.create(
                        transferencia=transferencia,
                        producto=producto,
                        cantidad_solicitada=cantidad,
                        lote=lote_obj
                    )
                
                # Registrar trazabilidad
                registrar_trazabilidad(
                    tipo_operacion='TRANSFERENCIA',
                    modulo='TRANSFERENCIAS',
                    referencia_id=transferencia.id,
                    referencia_tipo='TransferenciaInventario',
                    accion='CREAR',
                    descripcion=f'Transferencia creada: {transferencia.sucursal_origen} → {transferencia.sucursal_destino}',
                    usuario=request.user,
                    empresa=empresa,
                    sucursal=transferencia.sucursal_origen,
                    datos_nuevos=serializar_modelo(transferencia),
                    request=request,
                )
                
                messages.success(request, f'Transferencia {transferencia.folio} creada exitosamente')
                return redirect('ver_transferencia', transferencia_id=transferencia.id)
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en crear_transferencia (transferencias.py)")
            messages.error(request, f'Error al crear transferencia: {str(e)}')
    
    # GET: Mostrar formulario
    sucursales = Sucursal.objects.filter(empresa=empresa, activa=True)
    productos = Producto.objects.filter(empresa=empresa, stock__gt=0).select_related('sucursal')
    
    return render(request, 'core/transferencias/crear_transferencia.html', {
        'empresa': empresa,
        'sucursales': sucursales,
        'productos': productos,
    })


@login_required
def ver_transferencia(request, transferencia_id):
    """Ver detalle de una transferencia."""
    empresa = getattr(request.user, 'empresa', None)
    transferencia = get_object_or_404(TransferenciaInventario, id=transferencia_id, empresa=empresa)
    detalles = transferencia.detalles.all().select_related('producto', 'lote')
    
    return render(request, 'core/transferencias/ver_transferencia.html', {
        'empresa': empresa,
        'transferencia': transferencia,
        'detalles': detalles,
    })


@login_required
@require_http_methods(["POST"])
def enviar_transferencia(request, transferencia_id):
    """Enviar una transferencia (marcar como en tránsito y descontar stock)."""
    empresa = getattr(request.user, 'empresa', None)
    transferencia = get_object_or_404(TransferenciaInventario, id=transferencia_id, empresa=empresa)
    
    if transferencia.estado != 'BORRADOR':
        messages.error(request, 'Solo se pueden enviar transferencias en estado Borrador')
        return redirect('ver_transferencia', transferencia_id=transferencia.id)
    
    try:
        with transaction.atomic():
            # Descontar stock de sucursal origen
            for detalle in transferencia.detalles.all():
                producto = detalle.producto
                
                # Verificar que el producto esté en la sucursal origen
                if producto.sucursal != transferencia.sucursal_origen:
                    messages.error(request, f'El producto {producto.nombre} no está en la sucursal origen')
                    return redirect('ver_transferencia', transferencia_id=transferencia.id)
                
                # Descontar stock
                cantidad_a_enviar = detalle.cantidad_solicitada or 0
                if producto.stock < cantidad_a_enviar:
                    messages.error(request, f'Stock insuficiente para {producto.nombre}')
                    return redirect('ver_transferencia', transferencia_id=transferencia.id)

                producto.stock -= cantidad_a_enviar
                producto.save()
                detalle.cantidad_enviada = cantidad_a_enviar
                detalle.save(update_fields=['cantidad_enviada'])

                # Si hay lote específico, descontar del lote
                if detalle.lote:
                    if detalle.lote.cantidad < cantidad_a_enviar:
                        messages.error(request, f'Cantidad insuficiente en lote {detalle.lote.numero_lote}')
                        return redirect('ver_transferencia', transferencia_id=transferencia.id)
                    detalle.lote.cantidad -= cantidad_a_enviar
                    detalle.lote.save()
            
            # Actualizar estado
            transferencia.estado = 'EN_TRANSITO'
            transferencia.fecha_envio = timezone.now()
            transferencia.enviado_por = request.user
            transferencia.save()
            
            # Registrar trazabilidad
            registrar_trazabilidad(
                tipo_operacion='TRANSFERENCIA',
                modulo='TRANSFERENCIAS',
                referencia_id=transferencia.id,
                referencia_tipo='TransferenciaInventario',
                accion='ENVIAR',
                descripcion=f'Transferencia enviada: {transferencia.sucursal_origen} → {transferencia.sucursal_destino}',
                usuario=request.user,
                empresa=empresa,
                sucursal=transferencia.sucursal_origen,
                datos_nuevos=serializar_modelo(transferencia),
                request=request,
            )
            
            messages.success(request, f'Transferencia {transferencia.folio} enviada exitosamente')
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en enviar_transferencia (transferencias.py)")
        messages.error(request, f'Error al enviar transferencia: {str(e)}')
    
    return redirect('ver_transferencia', transferencia_id=transferencia.id)


@login_required
@require_http_methods(["POST"])
def recibir_transferencia(request, transferencia_id):
    """Recibir una transferencia (marcar como recibida y agregar stock a destino)."""
    empresa = getattr(request.user, 'empresa', None)
    transferencia = get_object_or_404(TransferenciaInventario, id=transferencia_id, empresa=empresa)
    
    if transferencia.estado != 'EN_TRANSITO':
        messages.error(request, 'Solo se pueden recibir transferencias en estado EN_TRANSITO')
        return redirect('ver_transferencia', transferencia_id=transferencia.id)
    
    try:
        with transaction.atomic():
            # Agregar stock a sucursal destino
            for detalle in transferencia.detalles.all():
                producto = detalle.producto
                
                # Actualizar o crear producto en sucursal destino
                producto_destino, created = Producto.objects.get_or_create(
                    codigo_barras=producto.codigo_barras,
                    empresa=empresa,
                    defaults={
                        'nombre': producto.nombre,
                        'precio_publico': producto.precio_publico,
                        'precio_compra': producto.precio_compra,
                        'sucursal': transferencia.sucursal_destino,
                        'stock': 0,
                    }
                )
                
                qty = detalle.cantidad_recibida or detalle.cantidad_enviada or detalle.cantidad_solicitada or 0
                if not created:
                    producto_destino.stock += qty
                    producto_destino.sucursal = transferencia.sucursal_destino
                    producto_destino.save()
                else:
                    producto_destino.stock = qty
                    producto_destino.save()

                if not detalle.cantidad_recibida:
                    detalle.cantidad_recibida = qty
                    detalle.save(update_fields=['cantidad_recibida'])
            
            # Actualizar estado
            transferencia.estado = 'RECIBIDA'
            transferencia.fecha_recepcion = timezone.now()
            transferencia.recibido_por = request.user
            transferencia.save()
            
            # Registrar trazabilidad
            registrar_trazabilidad(
                tipo_operacion='TRANSFERENCIA',
                modulo='TRANSFERENCIAS',
                referencia_id=transferencia.id,
                referencia_tipo='TransferenciaInventario',
                accion='RECIBIR',
                descripcion=f'Transferencia recibida: {transferencia.sucursal_origen} → {transferencia.sucursal_destino}',
                usuario=request.user,
                empresa=empresa,
                sucursal=transferencia.sucursal_destino,
                datos_nuevos=serializar_modelo(transferencia),
                request=request,
            )
            
            messages.success(request, f'Transferencia {transferencia.folio} recibida exitosamente')
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en recibir_transferencia (transferencias.py)")
        messages.error(request, f'Error al recibir transferencia: {str(e)}')
    
    return redirect('ver_transferencia', transferencia_id=transferencia.id)


@login_required
def api_buscar_productos_transferencia(request):
    """API para buscar productos disponibles en una sucursal."""
    empresa = getattr(request.user, 'empresa', None)
    sucursal_id = request.GET.get('sucursal_id', '')
    query = request.GET.get('q', '').strip()
    
    productos = Producto.objects.filter(empresa=empresa, stock__gt=0)
    
    if sucursal_id:
        productos = productos.filter(sucursal_id=sucursal_id)
    
    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) |
            Q(codigo_barras__icontains=query)
        )[:20]
    
    resultados = [{
        'id': p.id,
        'nombre': p.nombre,
        'codigo_barras': p.codigo_barras,
        'stock': p.stock,
        'precio_compra': float(p.precio_compra),
        'lotes': [{
            'id': l.id,
            'numero_lote': l.numero_lote,
            'cantidad': l.cantidad,
            'fecha_caducidad': l.fecha_caducidad.strftime('%Y-%m-%d') if l.fecha_caducidad else None,
        } for l in p.lotes.filter(cantidad__gt=0)[:5]]
    } for p in productos]
    
    return JsonResponse({'productos': resultados})