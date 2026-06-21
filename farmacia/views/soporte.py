"""
Vistas de Soporte Operativo para Farmacia V5.0
================================================
Módulos:
1. Devoluciones y Cancelaciones
2. Apertura de Caja
3. Control de Antibióticos (Validación)
4. Entrada Express (Fast Restock)

Autor: PRIS AI Team
Fecha: 2026-02-10
"""
import json
import logging
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods, require_POST
from django.http import JsonResponse
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum, F, Count, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.models import Usuario, Producto, Lote, Empresa, Sucursal, Venta, DetalleVenta
from farmacia.models import (
    AperturaCaja, CierreTurnoFarmacia, 
    DevolucionVenta, RegistroAntibiotico,
    MermaFarmacia, MovimientoInventario
)

logger = logging.getLogger(__name__)


def _serializar_venta_para_devolucion(venta):
    devoluciones_previas = venta.devoluciones_farmacia.all()
    total_devuelto = sum(d.monto_devolucion for d in devoluciones_previas)
    return {
        'venta': {
            'id': venta.id,
            'folio': venta.folio_operacion or str(venta.id),
            'fecha': venta.fecha.strftime('%Y-%m-%d %H:%M'),
            'total': str(venta.total),
            'cliente': venta.paciente.nombre_completo if venta.paciente else 'Cliente General',
            'vendedor': venta.usuario.get_full_name(),
            'tiene_devoluciones': devoluciones_previas.exists(),
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
    """Requerido para procesar devoluciones (solo gerente/admin)."""
    if user.is_superuser:
        return True
    rol = (getattr(user, 'rol', '') or '').upper().strip()
    if rol in ('ADMIN', 'ADMINISTRADOR', 'GERENTE'):
        return True
    return user.groups.filter(name__in=['Gerente', 'Administrador', 'Admin']).exists()


# ==============================================================================
# 1. MÓDULO DE DEVOLUCIONES Y CANCELACIONES
# ==============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def buscar_venta_para_devolucion(request):
    """
    Busca una venta por folio para iniciar proceso de devolución.
    GET: Renderiza formulario de búsqueda.
    POST: Busca y muestra detalles de la venta.
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
            
            # Buscar venta (core.Venta usa folio_operacion) scoped por empresa
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
            logger.error(f"Error buscando venta: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Error al buscar venta: {str(e)}'
            }, status=500)
    
    # GET: Renderizar formulario, opcionalmente con venta precargada desde historial
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


@login_required
@user_passes_test(_es_gerente_o_admin, login_url='/login/')
@require_POST
def procesar_devolucion(request):
    """
    Procesa una devolución parcial o total.
    SEGURIDAD: Solo gerente o administrador. Un CAJERO no puede procesar devoluciones.
    Solicita al usuario si desea reingresar al inventario o enviar a mermas.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'success': False, 'error': 'Usuario sin empresa asignada'}, status=403)
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
        
        venta_id = data.get('venta_id')
        tipo = data.get('tipo')  # 'TOTAL' o 'PARCIAL'
        monto = Decimal(data.get('monto', '0.00'))
        motivo = data.get('motivo')
        motivo_detallado = data.get('motivo_detallado', '')
        reingresar_stock = data.get('reingresar_stock', True)
        
        # Validaciones
        if not venta_id or not tipo or not motivo:
            return JsonResponse({
                'success': False,
                'error': 'Datos incompletos'
            }, status=400)
        
        venta = get_object_or_404(Venta, id=venta_id, empresa=empresa)
        
        # Sucursal requerida por DevolucionVenta: usar venta, usuario o primera de empresa
        sucursal = getattr(venta, 'sucursal', None) or getattr(request.user, 'sucursal', None)
        if not sucursal and venta.empresa:
            sucursal = venta.empresa.sucursales.filter(activa=True).first()
        if not sucursal:
            return JsonResponse({
                'success': False,
                'error': 'No hay sucursal asignada a la venta ni al usuario. Configure una sucursal.'
            }, status=400)
        
        # Verificar que no exceda el total (Coalesce evita None cuando no hay devoluciones)
        devoluciones_previas = venta.devoluciones_farmacia.aggregate(
            total=Coalesce(Sum('monto_devolucion'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
        
        disponible = venta.total - devoluciones_previas
        
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
            # Crear registro de devolución
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
                pass
            # Si requiere autorización, detener aquí
            if devolucion.requiere_autorizacion:
                return JsonResponse({
                    'success': True,
                    'requiere_autorizacion': True,
                    'folio': devolucion.folio,
                    'message': f'Devolución {devolucion.folio} creada. Requiere autorización gerencial (monto > $500).'
                })
            
            # Si no requiere autorización, marcar como autorizada automáticamente
            devolucion.autorizado = True
            devolucion.save(update_fields=['autorizado'])
            
            # Procesar la devolución (reingreso o merma)
            if reingresar_stock:
                for detalle in venta.detalles.all():
                    # Reingreso vía Kardex (actualiza stock automáticamente). DetalleVenta usa lote_vendido.
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
                    except Exception as e_mov:
                        # Si el Kardex falla, incrementar stock manualmente
                        logger.warning(f"Kardex reingreso falló para {detalle.producto}: {e_mov}. Ajuste manual.")
                        detalle.producto.stock += detalle.cantidad
                        detalle.producto.save(update_fields=['stock'])
                logger.info(f"Mercancía de {devolucion.folio} reingresada al stock")
            else:
                # Crear merma automática (MermaFarmacia requiere lote no nulo)
                for detalle in venta.detalles.all():
                    lote = getattr(detalle, 'lote_vendido', None) or getattr(detalle, 'lote', None)
                    if not lote:
                        # Sin lote en detalle: usar primer lote del producto con stock
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
            
    except Exception as e:
        logger.error(f"Error procesando devolución: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar devolución: {str(e)}'
        }, status=500)


@login_required
def dashboard_devoluciones(request):
    """
    Dashboard para gestión de devoluciones.
    Muestra devoluciones pendientes de autorización y últimas procesadas.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return render(request, 'farmacia/devoluciones/dashboard.html', {'pendientes': [], 'procesadas': []})
    sucursal = getattr(request.user, 'sucursal', None)
    # Devoluciones pendientes de autorización
    pendientes = DevolucionVenta.objects.filter(
        empresa=empresa,
        sucursal=sucursal,
        requiere_autorizacion=True,
        autorizado=False
    ).select_related('venta_original', 'usuario_procesa').order_by('-fecha_devolucion')
    
    # Últimas 50 devoluciones procesadas
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
            # Autorizar
            devolucion.autorizado = True
            devolucion.autorizado_por = request.user
            devolucion.save(update_fields=['autorizado', 'autorizado_por'])
            
            # Procesar
            devolucion.procesar_devolucion()
        
        return JsonResponse({
            'success': True,
            'message': f'Devolución {devolucion.folio} autorizada y procesada.'
        })
        
    except Exception as e:
        logger.error(f"Error autorizando devolución: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error: {str(e)}'
        }, status=500)


# ==============================================================================
# 2. MÓDULO DE APERTURA DE CAJA
# ==============================================================================

@login_required
def verificar_apertura_caja(request):
    """
    Verifica si hay una caja abierta para el usuario actual.
    Si no hay, redirige a apertura.
    """
    apertura_activa = AperturaCaja.objects.filter(
        sucursal=request.user.sucursal,
        usuario_responsable=request.user,
        activa=True
    ).first()
    
    if apertura_activa:
        return JsonResponse({
            'success': True,
            'caja_abierta': True,
            'apertura': {
                'folio': apertura_activa.folio,
                'fondo_inicial': str(apertura_activa.fondo_efectivo),
                'fecha_apertura': apertura_activa.fecha_apertura.strftime('%Y-%m-%d %H:%M'),
            }
        })
    else:
        return JsonResponse({
            'success': True,
            'caja_abierta': False,
            'message': 'No hay caja abierta. Debe abrir turno antes de vender.'
        })


@login_required
@require_http_methods(["GET", "POST"])
def abrir_caja(request):
    """
    Abre un nuevo turno de caja.
    Solicita el fondo inicial de efectivo.
    """
    # Verificar que no haya caja abierta
    apertura_activa = AperturaCaja.objects.filter(
        sucursal=request.user.sucursal,
        usuario_responsable=request.user,
        activa=True
    ).first()
    
    if apertura_activa:
        return JsonResponse({
            'success': False,
            'error': f'Ya existe una caja abierta: {apertura_activa.folio}'
        }, status=400)
    
    if request.method == 'POST':
        try:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
            fondo_efectivo = Decimal(data.get('fondo_efectivo', '0.00'))
            fondo_vales = Decimal(data.get('fondo_vales', '0.00'))
            observaciones = data.get('observaciones', '')
            
            if fondo_efectivo <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'El fondo inicial de efectivo debe ser mayor a 0'
                }, status=400)
            
            # Crear apertura
            apertura = AperturaCaja.objects.create(
                empresa=getattr(request.user, 'empresa', None),
                sucursal=request.user.sucursal,
                usuario_responsable=request.user,
                fondo_efectivo=fondo_efectivo,
                fondo_vales=fondo_vales,
                observaciones=observaciones
            )
            
            return JsonResponse({
                'success': True,
                'folio': apertura.folio,
                'message': f'Caja abierta correctamente: {apertura.folio}',
                'apertura': {
                    'folio': apertura.folio,
                    'fondo_efectivo': str(apertura.fondo_efectivo),
                    'fecha_apertura': apertura.fecha_apertura.strftime('%Y-%m-%d %H:%M'),
                }
            })
            
        except Exception as e:
            logger.error(f"Error abriendo caja: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': f'Error al abrir caja: {str(e)}'
            }, status=500)
    
    # GET: Renderizar formulario
    return render(request, 'farmacia/caja/abrir_caja.html')


# ==============================================================================
# 3. VALIDACIÓN DE ANTIBIÓTICOS (PDV)
# ==============================================================================

@login_required
@require_POST
def validar_venta_antibiotico(request):
    """
    Valida la venta de un antibiótico (Fracción IV).
    Si no viene de receta interna, exige datos del médico prescriptor.
    """
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
        producto_id = data.get('producto_id')
        receta_folio = data.get('receta_folio')  # Opcional
        medico_cedula = data.get('medico_cedula')  # Obligatorio si no hay receta
        medico_nombre = data.get('medico_nombre')  # Obligatorio si no hay receta
        
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return JsonResponse({'success': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        producto = get_object_or_404(Producto, id=producto_id, empresa=empresa)
        
        # Verificar si es antibiótico
        if not producto.es_antibiotico and producto.clasificacion_sanitaria != 'IV':
            return JsonResponse({
                'success': True,
                'requiere_validacion': False,
                'message': 'Producto no requiere validación de antibiótico'
            })
        
        # Si viene de receta interna, verificar que la receta existe y contiene el producto
        if receta_folio:
            receta_valida = False
            try:
                from consultorio.models import Receta
                receta_obj = Receta.objects.filter(
                    folio=receta_folio,
                    paciente__empresa=empresa
                ).prefetch_related('items').first()
                if receta_obj:
                    # Verificar que la receta contenga ESTE producto específico
                    receta_valida = receta_obj.items.filter(producto=producto).exists()
            except ImportError:
                logger.warning('[Farmacia] Módulo consultorio no disponible — validación de receta omitida')
                receta_valida = False
            except Exception as _rec_exc:
                logger.error(f'[Farmacia] Error validando receta antibiótico: {_rec_exc}', exc_info=True)
                receta_valida = False

            return JsonResponse({
                'success': True,
                'requiere_validacion': True,
                'validado': receta_valida,
                'message': 'Antibiótico validado por receta interna' if receta_valida
                           else 'Receta no encontrada o no contiene este producto'
            })
        
        # Si no hay receta, EXIGIR datos del médico
        if not medico_cedula or not medico_nombre:
            return JsonResponse({
                'success': False,
                'requiere_validacion': True,
                'validado': False,
                'error': 'Para venta de antibióticos sin receta interna, es OBLIGATORIO capturar Cédula y Nombre del Médico Prescriptor (NOM-072-SSA1-2012).'
            }, status=400)
        
        # Validación exitosa
        return JsonResponse({
            'success': True,
            'requiere_validacion': True,
            'validado': True,
            'message': 'Antibiótico validado. Datos del médico capturados.',
            'medico': {
                'cedula': medico_cedula,
                'nombre': medico_nombre
            }
        })
        
    except Exception as e:
        logger.error(f"Error validando antibiótico: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error: {str(e)}'
        }, status=500)


@login_required
def reporte_cofepris(request):
    """
    Genera reporte exportable de ventas de antibióticos (Libro COFEPRIS).
    Cumple con NOM-072-SSA1-2012.
    """
    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if not fecha_inicio or not fecha_fin:
        # Por defecto, último mes
        fecha_fin = date.today()
        fecha_inicio = fecha_fin - timedelta(days=30)
    else:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            fecha_fin = date.today()
            fecha_inicio = fecha_fin - timedelta(days=30)
    
    empresa = getattr(request.user, 'empresa', None)
    sucursal = getattr(request.user, 'sucursal', None)
    if not empresa:
        return render(request, 'farmacia/antibioticos/reporte_cofepris.html', {
            'registros': [], 'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin, 'total_registros': 0
        })
    # Obtener registros
    registros = RegistroAntibiotico.objects.filter(
        empresa=empresa,
        sucursal=sucursal,
        fecha_venta__date__gte=fecha_inicio,
        fecha_venta__date__lte=fecha_fin
    ).select_related('producto', 'venta', 'paciente', 'usuario_vendedor', 'lote_vendido').order_by('-fecha_venta')
    
    # Si es exportación (formato=csv), generar CSV
    if request.GET.get('formato') == 'csv':
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="reporte_cofepris_{fecha_inicio}_{fecha_fin}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Folio', 'Fecha Venta', 'Producto', 'Sustancia Activa', 'Cantidad',
            'Lote', 'Paciente', 'Edad', 'Cédula Médico', 'Nombre Médico',
            'Folio Receta', 'Vendedor'
        ])
        
        for reg in registros:
            writer.writerow([
                reg.folio,
                reg.fecha_venta.strftime('%Y-%m-%d %H:%M'),
                reg.producto.nombre,
                reg.producto.sustancia_activa or '',
                str(reg.cantidad_vendida),
                reg.lote_vendido.numero_lote if reg.lote_vendido else '',
                reg.paciente_nombre,
                reg.paciente_edad or '',
                reg.medico_cedula,
                reg.medico_nombre,
                reg.receta_folio or '',
                reg.usuario_vendedor.get_full_name()
            ])
        
        return response
    
    # Renderizar vista HTML
    context = {
        'registros': registros,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_registros': registros.count(),
    }
    
    return render(request, 'farmacia/antibioticos/reporte_cofepris.html', context)


# ==============================================================================
# 4. ENTRADA EXPRESS (FAST RESTOCK) - AJAX
# ==============================================================================

@login_required
@require_POST
def entrada_express(request):
    """
    Ingreso rápido de mercancía por AJAX.
    Usuario escanea código, ingresa cantidad y caducidad, sistema guarda sin recargar.
    """
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
        fecha_caducidad = data.get('fecha_caducidad')  # YYYY-MM-DD
        try:
            precio_compra = Decimal(str(data.get('precio_compra', '0.00')))
        except Exception:
            precio_compra = Decimal('0.00')
        
        # Validaciones
        if not codigo_barras or cantidad <= 0 or not numero_lote or not fecha_caducidad:
            return JsonResponse({
                'success': False,
                'error': 'Datos incompletos. Se requiere: código, cantidad, lote y caducidad.'
            }, status=400)
        
        # Buscar producto — filtrar estrictamente por empresa (sin fallback cross-tenant)
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return JsonResponse({'success': False, 'error': 'Usuario sin empresa asignada.'}, status=403)
        producto = Producto.objects.filter(codigo_barras=codigo_barras, empresa=empresa).first()
        
        if not producto:
            return JsonResponse({
                'success': False,
                'error': f'Producto con código {codigo_barras} no encontrado. Debe registrarlo primero.'
            }, status=404)
        
        # Convertir fecha
        fecha_caducidad_dt = datetime.strptime(fecha_caducidad, '%Y-%m-%d').date()
        
        with transaction.atomic():
            costo = precio_compra if precio_compra > 0 else (producto.precio_compra or Decimal('0.01'))
            
            # Buscar o crear lote
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
            
            # Crear movimiento Kardex (auto-actualiza stock en lote y producto)
            MovimientoInventario.objects.create(
                empresa=getattr(request.user, 'empresa', None),
                sucursal=getattr(request.user, 'sucursal', None),
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
        
    except Exception as e:
        logger.error(f"Error en entrada express: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar entrada: {str(e)}'
        }, status=500)
