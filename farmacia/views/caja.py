"""
Vistas de Turnos de Caja, Aperturas y Cortes de Caja para Farmacia
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction, DatabaseError, IntegrityError
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from datetime import datetime, date, time
from decimal import Decimal, InvalidOperation
import json

from core.models import Venta, Pago
from farmacia.models import AperturaCaja
from farmacia.forms import CorteCajaFarmaciaForm


@login_required
def corte_caja_farmacia(request):
    """
    Vista para realizar el corte de caja al final del turno (Arqueo ciego).
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('dashboard')
    usuario = request.user
    
    if request.method == 'POST':
        form = CorteCajaFarmaciaForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    efectivo_declarado = form.cleaned_data['efectivo_declarado']
                    tarjeta_declarada = form.cleaned_data.get('tarjeta_declarada', Decimal('0'))
                    transferencia_declarada = form.cleaned_data.get('transferencia_declarada', Decimal('0'))
                    observaciones = form.cleaned_data.get('observaciones_corte', '')
                    
                    total_declarado = efectivo_declarado + tarjeta_declarada + transferencia_declarada
                    
                    hoy_inicio = datetime.combine(date.today(), time.min)
                    ahora = timezone.now()
                    
                    ventas_turno = Venta.objects.filter(
                        empresa=empresa,
                        fecha__gte=hoy_inicio,
                        fecha__lte=ahora,
                        usuario=usuario
                    ).exclude(estado='CANCELADA')
                    
                    total_sistema = ventas_turno.aggregate(
                        total=Coalesce(Sum('total'), Value(Decimal('0')), output_field=DecimalField())
                    )['total']
                    
                    pagos_desglose = Pago.objects.filter(
                        venta__in=ventas_turno
                    ).aggregate(
                        total_efectivo=Coalesce(Sum('monto_efectivo'), Value(Decimal('0')), output_field=DecimalField()),
                        total_tarjeta=Coalesce(Sum('monto_tarjeta'), Value(Decimal('0')), output_field=DecimalField()),
                        total_transferencia=Coalesce(Sum('monto_transferencia'), Value(Decimal('0')), output_field=DecimalField()),
                    )
                    pagos_efectivo = pagos_desglose['total_efectivo']
                    pagos_tarjeta = pagos_desglose['total_tarjeta']
                    pagos_transferencia = pagos_desglose['total_transferencia']
                    
                    diferencia_efectivo = efectivo_declarado - pagos_efectivo
                    diferencia_tarjeta = tarjeta_declarada - pagos_tarjeta
                    diferencia_transferencia = transferencia_declarada - pagos_transferencia
                    diferencia_total = total_declarado - total_sistema
                    
                    if abs(diferencia_total) <= Decimal('1.00'):
                        estado = 'CUADRADO'
                        nivel_alerta = 'success'
                    elif diferencia_total > 0:
                        estado = 'SOBRANTE'
                        nivel_alerta = 'warning'
                    else:
                        estado = 'FALTANTE'
                        nivel_alerta = 'danger'
                    
                    from core.models import AuditLog
                    corte_log = AuditLog.objects.create(
                        empresa=empresa,
                        usuario=usuario,
                        accion=AuditLog.ACCION_CREATE,
                        modelo_afectado='CorteCajaFarmacia',
                        objeto_id='0',
                        datos_anteriores=None,
                        datos_nuevos={
                            'fecha_corte': ahora.isoformat(),
                            'turno_inicio': hoy_inicio.isoformat(),
                            'turno_fin': ahora.isoformat(),
                            'num_ventas': ventas_turno.count(),
                            'sistema_total': str(total_sistema),
                            'sistema_efectivo': str(pagos_efectivo),
                            'sistema_tarjeta': str(pagos_tarjeta),
                            'sistema_transferencia': str(pagos_transferencia),
                            'declarado_total': str(total_declarado),
                            'declarado_efectivo': str(efectivo_declarado),
                            'declarado_tarjeta': str(tarjeta_declarada),
                            'declarado_transferencia': str(transferencia_declarada),
                            'diferencia_total': str(diferencia_total),
                            'diferencia_efectivo': str(diferencia_efectivo),
                            'diferencia_tarjeta': str(diferencia_tarjeta),
                            'estado': estado,
                            'observaciones': observaciones
                        },
                        sucursal=getattr(usuario, 'sucursal', None),
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                    )
                    
                    return render(request, 'farmacia/corte_caja_resultado.html', {
                        'corte_id': corte_log.id,
                        'fecha_corte': ahora,
                        'total_ventas': ventas_turno.count(),
                        'sistema_total': total_sistema,
                        'sistema_efectivo': pagos_efectivo,
                        'sistema_tarjeta': pagos_tarjeta,
                        'declarado_total': total_declarado,
                        'declarado_efectivo': efectivo_declarado,
                        'declarado_tarjeta': tarjeta_declarada,
                        'declarado_transferencia': transferencia_declarada,
                        'diferencia_total': diferencia_total,
                        'diferencia_efectivo': diferencia_efectivo,
                        'diferencia_tarjeta': diferencia_tarjeta,
                        'estado': estado,
                        'nivel_alerta': nivel_alerta,
                        'observaciones': observaciones
                    })
                    
            except (DatabaseError, ValueError, TypeError, InvalidOperation, ValidationError) as e:
                messages.error(request, f'❌ Error al procesar corte de caja: {str(e)}')
    else:
        form = CorteCajaFarmaciaForm()
    
    hoy_inicio = datetime.combine(date.today(), time.min)
    ahora = timezone.now()
    
    ventas_turno_count = Venta.objects.filter(
        empresa=empresa,
        fecha__gte=hoy_inicio,
        fecha__lte=ahora,
        usuario=usuario,
    ).exclude(estado='CANCELADA').count()
    
    return render(request, 'farmacia/corte_caja_form.html', {
        'form': form,
        'ventas_turno_count': ventas_turno_count,
        'turno_inicio': hoy_inicio
    })


@login_required
def verificar_apertura_caja(request):
    """
    Verifica si hay una caja abierta para el usuario actual.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'success': False, 'error': 'Usuario sin empresa asignada'}, status=403)
    apertura_activa = AperturaCaja.objects.filter(
        empresa=empresa,
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
def abrir_caja(request):
    """
    Abre un nuevo turno de caja.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'success': False, 'error': 'Usuario sin empresa asignada'}, status=403)
    
    apertura_activa = AperturaCaja.objects.filter(
        empresa=empresa,
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
            
            apertura = AperturaCaja.objects.create(
                empresa=empresa,
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
            
        except (DatabaseError, ValueError, TypeError, InvalidOperation, ValidationError) as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al abrir caja: {str(e)}'
            }, status=500)
    
    return render(request, 'farmacia/caja/abrir_caja.html')
