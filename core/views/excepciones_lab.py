"""
Vistas para Flujos de Excepción en Laboratorio
Implementa cancelación, edición, valores de pánico, rechazo de muestra, etc.
"""
import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.models import (
    Empresa, Paciente, OrdenDeServicio, DetalleOrden,
    GastoCaja, PagoOrden,
)
from core.lims_cart import resolve_lims_cart_ids, aplicar_precio_convenio, detalle_orden_etiqueta


def _detalle_lims_key(detail):
    if getattr(detail, 'analito_id', None):
        return ('analito', detail.analito_id)
    if getattr(detail, 'perfil_lims_id', None):
        return ('perfil', detail.perfil_lims_id)
    if getattr(detail, 'paquete_lims_id', None):
        return ('paquete', detail.paquete_lims_id)
    return (None, None)


def _row_lims_key(row):
    if row.get('analito'):
        return ('analito', row['analito'].id)
    if row.get('perfil_lims'):
        return ('perfil', row['perfil_lims'].id)
    if row.get('paquete_lims'):
        return ('paquete', row['paquete_lims'].id)
    return (None, None)


def es_superusuario(user):
    """Verifica si el usuario es superusuario."""
    return user.is_superuser


@login_required
@user_passes_test(es_superusuario)
@require_http_methods(["POST"])
def cancelar_orden(request, orden_id):
    """
    Cancela una orden de servicio (requiere superusuario).
    Genera un registro negativo en el corte de caja.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    
    try:
        orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)
        
        if orden.estado == 'CANCELADO':
            return JsonResponse({
                'status': 'error',
                'mensaje': 'La orden ya está cancelada'
            }, status=400)
        
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        motivo = data.get('motivo', 'Sin motivo especificado')
        
        with transaction.atomic():
            # Cambiar estado a CANCELADO
            estado_anterior = orden.estado
            orden.estado = 'CANCELADO'
            orden.motivo_eliminacion = motivo
            orden.deleted_at = timezone.now()
            orden.save()
            
            # Si la orden estaba pagada, generar registro negativo en corte
            if estado_anterior in ['PAGADO', 'EN_PROCESO', 'RESULTADOS_LISTOS'] and orden.anticipo > 0:
                GastoCaja.objects.create(
                    empresa=empresa,
                    usuario=request.user,
                    concepto=f"Devolución Orden {orden.folio_orden or orden.id}",
                    monto=-orden.anticipo,  # Negativo para indicar devolución
                )
            
            # Registrar auditoría forense (quién, qué, cuándo)
            from core.services.audit_service import registrar_auditoria
            registrar_auditoria(
                accion='UPDATE',
                modelo='OrdenDeServicio',
                objeto_id=str(orden.id),
                datos_anteriores={'estado': estado_anterior, 'folio': orden.folio_orden or str(orden.id)},
                datos_nuevos={'estado': 'CANCELADO', 'motivo': motivo},
                request=request,
            )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Orden cancelada exitosamente',
            'orden_id': orden.id
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def editar_paciente_orden(request, orden_id):
    """
    Permite editar nombre/edad de un paciente en una orden ya cobrada
    sin alterar el folio ni el cobro.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    
    try:
        orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)
        
        # Solo permitir edición si la orden está cobrada pero no entregada
        if orden.estado not in ['PAGADO', 'EN_PROCESO', 'RESULTADOS_LISTOS']:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Solo se puede editar paciente en órdenes pagadas'
            }, status=400)
        
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        nombre_nuevo = data.get('nombre_completo')
        fecha_nacimiento_nueva = data.get('fecha_nacimiento')
        
        if not nombre_nuevo:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Debe proporcionar el nuevo nombre'
            }, status=400)
        
        with transaction.atomic():
            # Actualizar paciente (no se modifica el folio ni el cobro)
            paciente = orden.paciente
            nombre_anterior = paciente.nombre_completo
            
            paciente.nombre_completo = nombre_nuevo
            if fecha_nacimiento_nueva:
                from datetime import datetime
                paciente.fecha_nacimiento = datetime.strptime(fecha_nacimiento_nueva, '%Y-%m-%d').date()
            paciente.save()
            
            from core.services.audit_service import registrar_auditoria
            registrar_auditoria(
                accion='UPDATE',
                modelo='Paciente',
                objeto_id=str(paciente.id),
                datos_anteriores={'nombre_completo': nombre_anterior, 'orden_id': orden.id},
                datos_nuevos={'nombre_completo': nombre_nuevo, 'folio_orden': orden.folio_orden or str(orden.id)},
                request=request,
            )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Paciente actualizado exitosamente',
            'nombre_anterior': nombre_anterior,
            'nombre_nuevo': nombre_nuevo
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def validar_valor_critico(request, detalle_id):
    """
    Valida un valor crítico (de pánico) ingresado en captura_resultados.
    Verifica si el valor está fuera del rango crítico del estudio.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    
    try:
        detalle = get_object_or_404(DetalleOrden, id=detalle_id, orden__empresa=empresa)
        estudio = detalle.estudio
        
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        valor_ingresado = Decimal(str(data.get('valor', 0)))
        confirmado = data.get('confirmado', False)
        
        # Verificar si hay rango de pánico definido
        es_valor_critico = False
        mensaje = ''
        
        if estudio.rango_panico_min is not None and valor_ingresado < estudio.rango_panico_min:
            es_valor_critico = True
            mensaje = f"⚠ VALOR DE PÁNICO: {valor_ingresado} está por debajo del rango crítico mínimo ({estudio.rango_panico_min} {estudio.unidad})"
        elif estudio.rango_panico_max is not None and valor_ingresado > estudio.rango_panico_max:
            es_valor_critico = True
            mensaje = f"⚠ VALOR DE PÁNICO: {valor_ingresado} está por encima del rango crítico máximo ({estudio.rango_panico_max} {estudio.unidad})"
        
        if es_valor_critico:
            if not confirmado:
                return JsonResponse({
                    'status': 'valor_critico',
                    'es_critico': True,
                    'mensaje': mensaje,
                    'requiere_confirmacion': True
                })
            else:
                # Marcar como confirmado
                detalle.valor_critico_confirmado = True
                detalle.save()
                
                from core.services.audit_service import registrar_auditoria
                registrar_auditoria(
                    accion='UPDATE',
                    modelo='DetalleOrden',
                    objeto_id=str(detalle.id),
                    datos_nuevos={'valor_critico_confirmado': valor_ingresado, 'estudio': estudio.nombre},
                    request=request,
                )
        
        return JsonResponse({
            'status': 'success',
            'es_critico': es_valor_critico,
            'mensaje': mensaje if es_valor_critico else 'Valor dentro de rango normal'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def rechazar_muestra(request, detalle_id):
    """
    Rechaza una muestra (Muestra Insuficiente/Hemolizada/Coagulada).
    Reinicia el estado del estudio a "PENDIENTE_TOMA" pero guarda la incidencia.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    
    try:
        detalle = get_object_or_404(DetalleOrden, id=detalle_id, orden__empresa=empresa)
        
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        motivo_rechazo = data.get('motivo_rechazo', 'Sin motivo especificado')
        
        with transaction.atomic():
            # Guardar motivo de rechazo
            detalle.motivo_rechazo = motivo_rechazo
            detalle.estado_procesamiento = 'PENDIENTE_TOMA'  # Reiniciar a pendiente de toma
            detalle.resultado = ''  # Limpiar resultado anterior si existe
            detalle.validado_por = None
            detalle.fecha_validacion = None
            detalle.save()
            
            from core.services.audit_service import registrar_auditoria
            registrar_auditoria(
                accion='UPDATE',
                modelo='DetalleOrden',
                objeto_id=str(detalle.id),
                datos_anteriores={'estudio': detalle.estudio.nombre},
                datos_nuevos={'estado_procesamiento': 'PENDIENTE_TOMA', 'motivo_rechazo': motivo_rechazo, 'estudio': detalle.estudio.nombre},
                request=request,
            )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Muestra rechazada y reiniciada a PENDIENTE_TOMA',
            'detalle_id': detalle.id
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def registrar_merma(request):
    """
    Registra una baja por merma en inventario (sin generar venta).
    Motivos: 'Caducado', 'Roto', 'Consumo Interno'
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    
    try:
        from core.models import Producto, Lote, AjusteInventario
        
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        producto_id = data.get('producto_id')
        lote_id = data.get('lote_id')
        cantidad = int(data.get('cantidad', 0))
        motivo = data.get('motivo', 'MERMA')
        
        if not producto_id or cantidad <= 0:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Debe proporcionar producto_id y cantidad válida'
            }, status=400)
        
        producto = get_object_or_404(Producto, id=producto_id, empresa=empresa)
        
        # Validar que haya suficiente stock
        if producto.stock < cantidad:
            return JsonResponse({
                'status': 'error',
                'mensaje': f'Stock insuficiente. Disponible: {producto.stock}, Solicitado: {cantidad}'
            }, status=400)
        
        with transaction.atomic():
            # Obtener lote (si no se proporciona, usar el más antiguo - PEPS)
            if lote_id:
                lote = get_object_or_404(Lote, id=lote_id, producto=producto)
            else:
                lote = Lote.objects.filter(producto=producto, cantidad__gt=0).order_by('fecha_caducidad').first()
                if not lote:
                    return JsonResponse({
                        'status': 'error',
                        'mensaje': 'No hay lotes disponibles para este producto'
                    }, status=400)
            
            # Validar que el lote tenga suficiente cantidad
            if lote.cantidad < cantidad:
                return JsonResponse({
                    'status': 'error',
                    'mensaje': f'Cantidad insuficiente en lote. Disponible: {lote.cantidad}, Solicitado: {cantidad}'
                }, status=400)
            
            # Crear ajuste de inventario (merma)
            ajuste = AjusteInventario.objects.create(
                empresa=empresa,
                producto=producto,
                lote=lote,
                cantidad=cantidad,
                tipo_movimiento='MERMA',
                observacion=motivo,
                usuario=request.user
            )
            
            # Descontar del stock
            producto.stock -= cantidad
            producto.save()
            
            # Descontar del lote
            lote.cantidad -= cantidad
            lote.save()
            
            # Registrar auditoría
            from core.models import AuditLog
            AuditLog.objects.create(
                empresa=empresa,
                usuario=request.user,
                accion='REGISTRAR_MERMA',
                detalle=f"Merma registrada: {cantidad} unidades de {producto.nombre}. Motivo: {motivo}",
                referencia_id=ajuste.id
            )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Merma registrada exitosamente',
            'ajuste_id': ajuste.id,
            'stock_restante': producto.stock
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=500)


# ══════════════════════════════════════════════════════════════════
# EDICIÓN DE ORDEN: AGREGAR / ELIMINAR ESTUDIOS
# ══════════════════════════════════════════════════════════════════

@login_required
@require_http_methods(["POST"])
def agregar_estudio_orden(request, orden_id):
    """Agrega un estudio a una orden existente."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    if orden.estado in ('CANCELADO', 'ENTREGADO'):
        return JsonResponse({'status': 'error', 'mensaje': f'No se puede editar orden {orden.estado}'}, status=400)

    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        raw = data.get('estudio_id') or data.get('lims_id')
        if not raw:
            return JsonResponse({'status': 'error', 'mensaje': 'Falta estudio_id / lims_id (token LIMS)'}, status=400)

        lineas = resolve_lims_cart_ids([raw])
        if not lineas:
            return JsonResponse({'status': 'error', 'mensaje': 'Ítem de catálogo LIMS no válido'}, status=400)
        row = lineas[0]
        nk = _row_lims_key(row)
        if nk[0] is None:
            return JsonResponse({'status': 'error', 'mensaje': 'Línea LIMS incompleta'}, status=400)

        for d in orden.detalles.all():
            if _detalle_lims_key(d) == nk:
                return JsonResponse({
                    'status': 'error',
                    'mensaje': f'"{detalle_orden_etiqueta(d)}" ya está en esta orden',
                }, status=400)

        with transaction.atomic():
            from decimal import ROUND_HALF_UP
            precio = aplicar_precio_convenio(row['precio_base'], row['precio_key'], {}, Decimal('0'))
            desc = (row.get('descripcion_linea') or '')[:300]
            detalle = DetalleOrden.objects.create(
                orden=orden,
                analito=row['analito'],
                perfil_lims=row['perfil_lims'],
                paquete_lims=row['paquete_lims'],
                descripcion_linea=desc,
                precio_momento=precio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            )
            etiqueta = (row.get('descripcion_linea') or '').strip() or detalle_orden_etiqueta(detalle)
            total_nuevo = sum(d.precio_momento for d in orden.detalles.all())
            anticipo = orden.anticipo or Decimal('0')
            try:
                anticipo = sum(p.monto_total for p in PagoOrden.objects.filter(orden=orden))
            except Exception:
                pass
            saldo = total_nuevo - anticipo
            orden.total = total_nuevo
            orden.save(update_fields=['total'])
            from core.services.audit_service import registrar_auditoria
            registrar_auditoria(
                accion='CREATE',
                modelo='DetalleOrden',
                objeto_id=str(detalle.id),
                datos_nuevos={
                    'linea_lims': etiqueta,
                    'precio': str(precio),
                    'orden_id': orden.id,
                    'folio_orden': orden.folio_orden or str(orden.id),
                    'total_nuevo': str(total_nuevo),
                },
                request=request,
            )

        return JsonResponse({
            'status': 'success',
            'mensaje': f'"{etiqueta}" agregado. Total: ${total_nuevo}',
            'detalle_id': detalle.id, 'total': float(total_nuevo), 'saldo': float(saldo),
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def eliminar_estudio_orden(request, orden_id, detalle_id):
    """Elimina un estudio de una orden existente."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    if orden.estado in ('CANCELADO', 'ENTREGADO'):
        return JsonResponse({'status': 'error', 'mensaje': f'No se puede editar orden {orden.estado}'}, status=400)

    try:
        detalle = get_object_or_404(DetalleOrden, id=detalle_id, orden=orden)

        if orden.detalles.count() <= 1:
            return JsonResponse({'status': 'error', 'mensaje': 'No se puede eliminar el único estudio. Use cancelar orden.'}, status=400)

        from core.models import ResultadoParametro
        nombre_est = detalle_orden_etiqueta(detalle)
        if detalle.analito_id:
            tiene_resultados = ResultadoParametro.objects.filter(
                orden=orden,
                analito_id=detalle.analito_id,
            ).exclude(valor='').exclude(valor__isnull=True).exclude(valor='Pendiente').exists()
        else:
            res_txt = (detalle.resultado or '').strip()
            tiene_resultados = bool(res_txt) and res_txt != 'Pendiente'
        if tiene_resultados:
            return JsonResponse({
                'status': 'error',
                'mensaje': f'"{nombre_est}" ya tiene resultados capturados.',
            }, status=400)

        with transaction.atomic():
            detalle.delete()
            total_nuevo = sum(d.precio_momento for d in orden.detalles.all())
            anticipo = orden.anticipo or Decimal('0')
            try:
                anticipo = sum(p.monto_total for p in PagoOrden.objects.filter(orden=orden))
            except Exception:
                pass
            saldo = total_nuevo - anticipo
            orden.total = total_nuevo
            orden.save(update_fields=['total'])
            from core.services.audit_service import registrar_auditoria
            registrar_auditoria(
                accion='DELETE',
                modelo='DetalleOrden',
                objeto_id=str(detalle_id),
                datos_anteriores={'linea_lims': nombre_est, 'orden_id': orden.id, 'folio_orden': orden.folio_orden or str(orden.id)},
                datos_nuevos={'total_nuevo': str(total_nuevo)},
                request=request,
            )

        return JsonResponse({
            'status': 'success', 'mensaje': f'"{nombre_est}" eliminado. Total: ${total_nuevo}',
            'total': float(total_nuevo), 'saldo': float(saldo),
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@login_required
def api_detalle_orden(request, orden_id):
    """Obtener detalles de una orden para el modal de edición."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Usuario sin empresa asignada'}, status=403)
    orden = get_object_or_404(OrdenDeServicio.objects.select_related('paciente'), id=orden_id, empresa=empresa)

    detalles = []
    for d in orden.detalles.select_related('analito', 'perfil_lims', 'paquete_lims').all():
        k = _detalle_lims_key(d)
        token = f'{k[0]}:{k[1]}' if k[0] else None
        codigo = ''
        if d.analito_id and d.analito:
            codigo = d.analito.codigo or ''
        detalles.append({
            'detalle_id': d.id,
            'estudio_id': token,
            'nombre': detalle_orden_etiqueta(d),
            'codigo': codigo,
            'precio': float(d.precio_momento),
            'tiene_resultado': bool(d.resultado and d.resultado.strip() and d.resultado != 'Pendiente'),
        })

    anticipo = orden.anticipo or Decimal('0')
    try:
        anticipo = sum(p.monto_total for p in PagoOrden.objects.filter(orden=orden))
    except Exception:
        pass

    return JsonResponse({
        'ok': True,
        'orden': {
            'id': orden.id, 'folio': orden.folio_orden or f'ORD-{orden.id}',
            'paciente': orden.paciente.nombre_completo if orden.paciente else '',
            'estado': orden.estado, 'total': float(orden.total or 0),
            'anticipo': float(anticipo), 'saldo': float((orden.total or Decimal('0')) - anticipo),
            'editable': orden.estado not in ('CANCELADO', 'ENTREGADO'),
        },
        'detalles': detalles,
    })
