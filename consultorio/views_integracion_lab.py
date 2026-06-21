"""
Integración Consultorio-Laboratorio - PRISLAB
Permite crear órdenes de laboratorio directamente desde la consulta médica.

LEGACY / NO CABLEADO EN urls.py (2026): Tras core.0073, DetalleOrden ya no tiene FK
`estudio`; el flujo correcto es analito/perfil_lims/paquete_lims. No registrar rutas
hasta reescribir este módulo (ver docs/manual/LEGACY_BOUNDARY_FASE0.md).
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import json

from core.models import (
    Empresa, Paciente, OrdenDeServicio, DetalleOrden, Estudio,
    PreOrdenLaboratorio, DetallePreOrden, ConsultaMedica,
)
from consultorio.models import AgendaCita
from core.utils.trazabilidad import registrar_trazabilidad, serializar_modelo


@login_required
@require_http_methods(["POST"])
def crear_orden_lab_desde_consulta(request, consulta_id):
    """
    Crea una orden de laboratorio directamente desde una consulta médica.
    Integración fluida Consultorio-Laboratorio.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    consulta = get_object_or_404(ConsultaMedica, id=consulta_id, empresa=empresa)
    if consulta.paciente.empresa_id != empresa.id:
        return JsonResponse(
            {'status': 'error', 'mensaje': 'El paciente de la consulta no pertenece a su empresa.'},
            status=403,
        )

    try:
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        else:
            data = request.POST
        estudio_ids = data.get('estudio_ids', [])
        
        if not estudio_ids:
            return JsonResponse({'status': 'error', 'mensaje': 'Debe seleccionar al menos un estudio'}, status=400)
        
        estudios = Estudio.objects.filter(id__in=estudio_ids, activo=True)
        if estudios.count() != len(estudio_ids):
            return JsonResponse({'status': 'error', 'mensaje': 'Uno o más estudios no encontrados'}, status=404)
        
        # Calcular total
        total = sum(estudio.precio for estudio in estudios)
        
        with transaction.atomic():
            # Generar folio único
            hoy = timezone.localtime(timezone.now())
            fecha_str = hoy.strftime('%Y%m%d')
            ultima_orden_hoy = OrdenDeServicio.objects.filter(
                empresa=empresa,
                fecha_creacion__date=hoy.date()
            ).order_by('-id').first()
            
            if ultima_orden_hoy and ultima_orden_hoy.folio_orden:
                try:
                    num_secuencial = int(ultima_orden_hoy.folio_orden.split('-')[-1]) + 1
                except (ValueError, TypeError):
                    num_secuencial = 1
            else:
                num_secuencial = 1
            
            folio_orden = f'LAB-{fecha_str}-{num_secuencial:04d}'
            
            # Crear orden de laboratorio
            orden = OrdenDeServicio.objects.create(
                empresa=empresa,
                paciente=consulta.paciente,
                total=total,
                anticipo=Decimal('0.00'),
                estado='PENDIENTE_PAGO',
                estado_pago='PENDIENTE',
                responsable_ingreso=request.user,
                folio_orden=folio_orden,
                tipo_servicio='LABORATORIO',
                diagnostico=getattr(consulta, 'diagnostico_principal', None) or getattr(consulta, 'diagnostico_texto', None) or getattr(consulta, 'diagnostico_cie10', None) or '',
                notas_internas=f'Orden creada desde consulta médica #{consulta.id}',
            )
            
            # Crear detalles
            for estudio in estudios:
                DetalleOrden.objects.create(
                    orden=orden,
                    estudio=estudio,
                    precio_momento=estudio.precio
                )
            
            # Registrar trazabilidad
            registrar_trazabilidad(
                tipo_operacion='ORDEN_LAB',
                modulo='LABORATORIO',
                referencia_id=orden.id,
                referencia_tipo='OrdenDeServicio',
                accion='CREAR',
                descripcion=f'Orden de laboratorio creada desde consulta médica - Consulta: #{consulta.id} - Paciente: {consulta.paciente.nombre_completo}',
                usuario=request.user,
                empresa=empresa,
                datos_nuevos=serializar_modelo(orden),
                request=request,
            )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Orden de laboratorio creada exitosamente',
            'orden_id': orden.id,
            'folio': folio_orden,
            'total': float(total),
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al crear orden: {str(e)}'
        }, status=500)


@login_required
def ver_resultados_lab_en_consulta(request, consulta_id):
    """
    Muestra los resultados de laboratorio relacionados con una consulta.
    Integración Consultorio-Laboratorio.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    consulta = get_object_or_404(ConsultaMedica, id=consulta_id, empresa=empresa)
    if consulta.paciente.empresa_id != empresa.id:
        from django.contrib import messages
        messages.error(request, 'El paciente de la consulta no pertenece a su empresa.')
        return redirect('home')

    # Buscar órdenes de laboratorio del paciente relacionadas con esta consulta
    # (mismo día o cercanas en fecha)
    fecha_consulta = consulta.fecha_creacion.date()
    
    ordenes_lab = OrdenDeServicio.objects.filter(
        empresa=empresa,
        paciente=consulta.paciente,
        fecha_creacion__date__gte=fecha_consulta
    ).select_related('paciente').prefetch_related(
        'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
    ).order_by('-fecha_creacion')

    from core.utils.detalle_orden import attach_detalle_display_attrs
    for orden in ordenes_lab:
        attach_detalle_display_attrs(list(orden.detalles.all()))
    
    return render(request, 'consultorio/resultados_lab_consulta.html', {
        'consulta': consulta,
        'ordenes_lab': ordenes_lab,
    })
