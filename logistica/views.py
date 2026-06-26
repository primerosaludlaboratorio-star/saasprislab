from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Count
from decimal import Decimal
import logging

from .models import RutaRecoleccion, VisitaDomicilio, TransferenciaInventario, DetalleTransferencia, LogTransferencia
from core.models import Producto, Lote, Sucursal


@login_required
def mapa_rutas(request):
    """
    MVP: listado de rutas/visitas. El mapa real se integra después (Google Maps).
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    rutas = RutaRecoleccion.objects.filter(empresa=empresa).order_by("-hora_salida")[:50]
    visitas = VisitaDomicilio.objects.filter(empresa=empresa).select_related("ruta").order_by("-fecha_creacion")[:200]
    return render(request, "logistica/mapa_rutas.html", {"rutas": rutas, "visitas": visitas})


@login_required
def asignar_visita(request, visita_id: int):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    visita = get_object_or_404(VisitaDomicilio, id=visita_id, empresa=empresa)

    rutas = RutaRecoleccion.objects.filter(empresa=empresa).order_by("-hora_salida")[:200]

    if request.method == "POST":
        ruta_id = request.POST.get("ruta_id")
        ruta = RutaRecoleccion.objects.filter(id=ruta_id, empresa=empresa).first() if ruta_id else None
        visita.ruta = ruta
        if ruta:
            visita.estatus = VisitaDomicilio.ESTATUS_ASIGNADA
        visita.save(update_fields=["ruta", "estatus"])
        return redirect("logistica:mapa_rutas")

    return render(request, "logistica/asignar_visita.html", {"visita": visita, "rutas": rutas})


@login_required
def monitor_rutas(request):
    """Alias estable del monitor de rutas para conservar compatibilidad de navegación."""
    return mapa_rutas(request)


# ==============================================================================
# SISTEMA DE TRASPASOS/TRANSFERENCIAS
# ==============================================================================

@login_required
def lista_transferencias(request):
    """
    Lista de transferencias con filtros.
    Muestra tanto transferencias salientes como entrantes.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    sucursal_usuario = getattr(request.user, 'sucursal', None)
    
    # Filtros
    estado = request.GET.get('estado', '')
    direccion = request.GET.get('direccion', 'todas')  # todas, salientes, entrantes
    
    # Query base
    if direccion == 'salientes' and sucursal_usuario:
        transferencias = TransferenciaInventario.objects.filter(
            empresa=empresa,
            sucursal_origen=sucursal_usuario
        )
    elif direccion == 'entrantes' and sucursal_usuario:
        transferencias = TransferenciaInventario.objects.filter(
            empresa=empresa,
            sucursal_destino=sucursal_usuario
        )
    else:
        transferencias = TransferenciaInventario.objects.filter(empresa=empresa)
    
    # Filtro por estado
    if estado:
        transferencias = transferencias.filter(estado=estado)
    
    transferencias = transferencias.select_related(
        'sucursal_origen', 'sucursal_destino', 
        'solicitado_por', 'enviado_por', 'recibido_por'
    ).prefetch_related('detalles').order_by('-fecha_creacion')
    
    # Estadísticas
    stats = {
        'total': transferencias.count(),
        'borradores': transferencias.filter(estado='BORRADOR').count(),
        'en_transito': transferencias.filter(estado__in=['ENVIADA', 'EN_TRANSITO']).count(),
        'completadas': transferencias.filter(estado='COMPLETADA').count(),
    }
    
    return render(request, 'logistica/lista_transferencias.html', {
        'transferencias': transferencias,
        'stats': stats,
        'estado_actual': estado,
        'direccion_actual': direccion,
    })


@login_required
def crear_transferencia(request):
    """
    Crear nueva transferencia entre sucursales.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                sucursal_origen_id = request.POST.get('sucursal_origen')
                sucursal_destino_id = request.POST.get('sucursal_destino')
                motivo = request.POST.get('motivo', '')
                
                # Validar que origen y destino sean diferentes
                if sucursal_origen_id == sucursal_destino_id:
                    messages.error(request, 'La sucursal de origen y destino deben ser diferentes')
                    return redirect('logistica:crear_transferencia')
                
                # Validar sucursales de la empresa
                sucursal_origen = get_object_or_404(Sucursal, id=sucursal_origen_id, empresa=empresa, activa=True)
                sucursal_destino = get_object_or_404(Sucursal, id=sucursal_destino_id, empresa=empresa, activa=True)
                
                # Crear transferencia
                transferencia = TransferenciaInventario.objects.create(
                    empresa=empresa,
                    sucursal_origen=sucursal_origen,
                    sucursal_destino=sucursal_destino,
                    solicitado_por=request.user,
                    motivo=motivo,
                    estado='BORRADOR'
                )
                
                # Registrar en log
                LogTransferencia.objects.create(
                    transferencia=transferencia,
                    usuario=request.user,
                    estado_nuevo='BORRADOR',
                    comentario='Transferencia creada',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'Transferencia {transferencia.folio} creada exitosamente')
                return redirect('logistica:detalle_transferencia', transferencia.id)
                
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en crear_transferencia (views.py)")
            messages.error(request, f'Error al crear transferencia: {str(e)}')
            return redirect('logistica:crear_transferencia')
    
    # GET: Mostrar formulario
    sucursales = Sucursal.objects.filter(empresa=empresa, activa=True).order_by('nombre')
    
    return render(request, 'logistica/crear_transferencia.html', {
        'sucursales': sucursales,
    })


@login_required
def detalle_transferencia(request, transferencia_id):
    """
    Vista detallada de una transferencia con opciones de gestión.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    transferencia = get_object_or_404(
        TransferenciaInventario, 
        id=transferencia_id, 
        empresa=empresa
    )
    
    detalles = transferencia.detalles.select_related('producto', 'lote').all()
    logs = transferencia.logs.select_related('usuario').all()
    
    # Calcular estadísticas
    total_items = detalles.count()
    total_valor = sum(d.subtotal() for d in detalles)
    
    return render(request, 'logistica/detalle_transferencia.html', {
        'transferencia': transferencia,
        'detalles': detalles,
        'logs': logs,
        'total_items': total_items,
        'total_valor': total_valor,
    })


@login_required
def agregar_producto_transferencia(request, transferencia_id):
    """
    API para agregar productos a una transferencia en borrador.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)
    transferencia = get_object_or_404(
        TransferenciaInventario, 
        id=transferencia_id, 
        empresa=empresa,
        estado='BORRADOR'
    )
    
    try:
        producto_id = request.POST.get('producto_id')
        try:
            cantidad = Decimal(request.POST.get('cantidad', '0'))
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en agregar_producto_transferencia (views.py)")
            return JsonResponse({'error': 'Cantidad inválida'}, status=400)
        lote_id = request.POST.get('lote_id')

        if cantidad <= 0:
            return JsonResponse({'error': 'La cantidad debe ser mayor a 0'}, status=400)
        
        producto = get_object_or_404(Producto, id=producto_id, empresa=empresa)
        lote = None
        if lote_id:
            lote = get_object_or_404(Lote, id=lote_id, producto=producto)
        
        # Crear detalle
        detalle = DetalleTransferencia.objects.create(
            transferencia=transferencia,
            producto=producto,
            lote=lote,
            cantidad_solicitada=cantidad,
            costo_unitario=producto.precio_compra or Decimal('0'),
            orden=transferencia.detalles.count() + 1
        )
        
        messages.success(request, f'Producto {producto.nombre} agregado')
        return JsonResponse({
            'success': True,
            'mensaje': 'Producto agregado',
            'detalle_id': detalle.id
        })
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en agregar_producto_transferencia (views.py)")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@permission_required('logistica.add_transferenciainventario', raise_exception=True)
def enviar_transferencia(request, transferencia_id):
    """
    Enviar una transferencia (cambiar estado de BORRADOR a ENVIADA).
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    transferencia = get_object_or_404(
        TransferenciaInventario, 
        id=transferencia_id, 
        empresa=empresa
    )
    
    if not transferencia.puede_enviar():
        messages.error(request, 'Esta transferencia no puede ser enviada')
        return redirect('logistica:detalle_transferencia', transferencia.id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Actualizar cantidades enviadas
                for detalle in transferencia.detalles.all():
                    detalle.cantidad_enviada = detalle.cantidad_solicitada
                    detalle.save(update_fields=['cantidad_enviada'])
                
                # Cambiar estado
                transferencia.estado = 'ENVIADA'
                transferencia.enviado_por = request.user
                transferencia.fecha_envio = timezone.now()
                transferencia.transportista = request.POST.get('transportista', '')
                transferencia.guia_transporte = request.POST.get('guia_transporte', '')
                transferencia.observaciones_origen = request.POST.get('observaciones', '')
                transferencia.save()
                
                # Log
                LogTransferencia.objects.create(
                    transferencia=transferencia,
                    usuario=request.user,
                    estado_anterior='BORRADOR',
                    estado_nuevo='ENVIADA',
                    comentario=f'Transferencia enviada. Transportista: {transferencia.transportista}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'Transferencia {transferencia.folio} enviada exitosamente')
                return redirect('logistica:detalle_transferencia', transferencia.id)
                
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en enviar_transferencia (views.py)")
            messages.error(request, f'Error al enviar transferencia: {str(e)}')
    
    return render(request, 'logistica/enviar_transferencia.html', {
        'transferencia': transferencia,
    })


@login_required
def recibir_transferencia(request, transferencia_id):
    """
    Recibir una transferencia y actualizar inventarios.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    transferencia = get_object_or_404(
        TransferenciaInventario, 
        id=transferencia_id, 
        empresa=empresa
    )
    
    if not transferencia.puede_recibir():
        messages.error(request, 'Esta transferencia no puede ser recibida')
        return redirect('logistica:detalle_transferencia', transferencia.id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Procesar cantidades recibidas
                for detalle in transferencia.detalles.all():
                    cantidad_recibida = Decimal(
                        request.POST.get(f'cantidad_recibida_{detalle.id}', '0')
                    )
                    detalle.cantidad_recibida = cantidad_recibida
                    detalle.daños_reportados = request.POST.get(f'danos_{detalle.id}', '')
                    detalle.save()
                    
                    # Actualizar inventarios (descontar origen, sumar destino)
                    try:
                        from farmacia.models import MovimientoInventario, MotivoAjuste
                        
                        motivo_transf, _ = MotivoAjuste.objects.get_or_create(
                            empresa=empresa,
                            codigo='TRANSFERENCIA',
                            defaults={
                                'descripcion': 'Traspaso entre sucursales',
                                'activo': True
                            }
                        )
                        
                        # Obtener el producto
                        producto = detalle.producto
                        costo = detalle.costo_unitario or producto.precio_compra or Decimal('0')
                        
                        # Movimiento de salida en sucursal origen
                        MovimientoInventario.objects.create(
                            empresa=empresa,
                            producto=producto,
                            lote=detalle.lote,
                            sucursal=transferencia.sucursal_origen,
                            tipo_movimiento='SALIDA_AJUSTE',
                            cantidad=cantidad_recibida,
                            costo_unitario=costo,
                            motivo_ajuste=motivo_transf,
                            observaciones=f'Transferencia #{transferencia.folio} a {transferencia.sucursal_destino.nombre}',
                            usuario_responsable=request.user
                        )
                        
                        # Movimiento de entrada en sucursal destino
                        MovimientoInventario.objects.create(
                            empresa=empresa,
                            producto=producto,
                            lote=detalle.lote,
                            sucursal=transferencia.sucursal_destino,
                            tipo_movimiento='ENTRADA_AJUSTE',
                            cantidad=cantidad_recibida,
                            costo_unitario=costo,
                            motivo_ajuste=motivo_transf,
                            observaciones=f'Transferencia #{transferencia.folio} desde {transferencia.sucursal_origen.nombre}',
                            usuario_responsable=request.user
                        )
                    except Exception as e:
                        logger = logging.getLogger('logistica')
                        logger.warning(f'No se pudo actualizar inventario: {str(e)}')
                
                # Cambiar estado
                transferencia.estado = 'COMPLETADA'
                transferencia.recibido_por = request.user
                transferencia.fecha_recepcion = timezone.now()
                transferencia.fecha_completado = timezone.now()
                transferencia.observaciones_destino = request.POST.get('observaciones', '')
                transferencia.save()
                
                # Log
                LogTransferencia.objects.create(
                    transferencia=transferencia,
                    usuario=request.user,
                    estado_anterior='ENVIADA',
                    estado_nuevo='COMPLETADA',
                    comentario='Transferencia recibida y completada',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, f'Transferencia {transferencia.folio} recibida exitosamente')
                return redirect('logistica:detalle_transferencia', transferencia.id)
                
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en recibir_transferencia (views.py)")
            messages.error(request, f'Error al recibir transferencia: {str(e)}')
    
    detalles = transferencia.detalles.select_related('producto', 'lote').all()
    
    return render(request, 'logistica/recibir_transferencia.html', {
        'transferencia': transferencia,
        'detalles': detalles,
    })


@login_required
def api_cadena_frio_temperatura(request, transferencia_id: int):
    """
    API: Registrar lectura de temperatura para certificación de cadena de frío ISO 15189.
    POST: { temperatura: float, metodo: 'MANUAL'|'SENSOR', sensor_id: str }
    La temperatura debe estar entre 2-8°C para que el traslado sea válido.
    """
    from django.http import JsonResponse
    from core.services.cadena_frio import registrar_lectura_temperatura
    from core.services.feature_flags import flag_activo

    empresa = getattr(request.user, 'empresa', None)

    if not flag_activo('CADENA_FRIO_ACTIVO', empresa):
        return JsonResponse({'ok': True, 'mensaje': 'Cadena de frio desactivada (flag OFF).'})

    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo no permitido'}, status=405)

    try:
        import json
        data = json.loads(request.body)
        temperatura = data.get('temperatura')
        if temperatura is None:
            return JsonResponse({'error': 'El campo temperatura es requerido.'}, status=400)

        transferencia = get_object_or_404(TransferenciaInventario, id=transferencia_id, empresa=empresa)

        resultado = registrar_lectura_temperatura(
            transferencia_id=transferencia.id,
            temperatura=float(temperatura),
            usuario=request.user,
            metodo=data.get('metodo', 'MANUAL'),
            sensor_id=data.get('sensor_id', ''),
        )

        status_code = 200 if resultado['valida'] else 422
        return JsonResponse({
            'ok': resultado['valida'],
            'temperatura': resultado['temperatura'],
            'nivel': resultado['nivel'],
            'mensaje': resultado['mensaje'],
            'bloqueado': not resultado['valida'],
        }, status=status_code)

    except Exception as exc:
        logging.getLogger(__name__).exception("Error inesperado en api_cadena_frio_temperatura (views.py)")
        return JsonResponse({'error': str(exc)}, status=500)


@login_required
def rastrear_transferencia(request, token):
    """
    Rastrear una transferencia por token UUID — requiere misma empresa del usuario.
    """
    empresa = getattr(request.user, 'empresa', None)
    transferencia = get_object_or_404(TransferenciaInventario, token_rastreo=token, empresa=empresa)
    logs = transferencia.logs.select_related('usuario').all()
    
    return render(request, 'logistica/rastrear_transferencia.html', {
        'transferencia': transferencia,
        'logs': logs,
    })