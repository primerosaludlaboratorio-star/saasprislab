"""
Vistas de Control Regulatorio, Validaciones de Antibióticos y Generación de Etiquetas para Farmacia
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db import DatabaseError
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date, timedelta
import json
import logging

from core.models import Producto, Lote
from farmacia.models import RegistroAntibiotico
from farmacia.forms import GenerarEtiquetasForm

logger = logging.getLogger(__name__)


@login_required
def validar_venta_antibiotico(request):
    """
    Valida la venta de un antibiótico (Fracción IV).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
        
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
            
        producto_id = data.get('producto_id')
        receta_folio = data.get('receta_folio')
        medico_cedula = data.get('medico_cedula')
        medico_nombre = data.get('medico_nombre')
        
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return JsonResponse({'success': False, 'error': 'Usuario sin empresa asignada'}, status=403)
        producto = get_object_or_404(Producto, id=producto_id, empresa=empresa)
        
        if not producto.es_antibiotico and producto.clasificacion_sanitaria != 'IV':
            return JsonResponse({
                'success': True,
                'requiere_validacion': False,
                'message': 'Producto no requiere validación de antibiótico'
            })
        
        if receta_folio:
            receta_valida = False
            try:
                from consultorio.models import Receta
                receta_obj = Receta.objects.filter(
                    folio=receta_folio,
                    paciente__empresa=empresa
                ).prefetch_related('items').first()
                if receta_obj:
                    receta_valida = receta_obj.items.filter(producto=producto).exists()
            except ImportError:
                logger.warning('[Farmacia] Módulo consultorio no disponible — validación de receta omitida')
                receta_valida = False
            except (DatabaseError, ValueError, TypeError) as _rec_exc:
                logger.error(f'[Farmacia] Error validando receta antibiótico: {_rec_exc}', exc_info=True)
                receta_valida = False

            return JsonResponse({
                'success': True,
                'requiere_validacion': True,
                'validado': receta_valida,
                'message': 'Antibiótico validado por receta interna' if receta_valida
                           else 'Receta no encontrada o no contiene este producto'
                })
        
        if not medico_cedula or not medico_nombre:
            return JsonResponse({
                'success': False,
                'requiere_validacion': True,
                'validado': False,
                'error': 'Para venta de antibióticos sin receta interna, es OBLIGATORIO capturar Cédula y Nombre del Médico Prescriptor (NOM-072-SSA1-2012).'
            }, status=400)
        
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
        # Justificación: Boundary top-level de API para validar antibiótico.
        logger.error(f"Error validando antibiótico: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error: {str(e)}'
        }, status=500)


@login_required
def reporte_cofepris(request):
    """
    Genera reporte exportable de ventas de antibióticos (Libro COFEPRIS).
    """
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if not fecha_inicio or not fecha_fin:
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
        
    registros = RegistroAntibiotico.objects.filter(
        empresa=empresa,
        sucursal=sucursal,
        fecha_venta__date__gte=fecha_inicio,
        fecha_venta__date__lte=fecha_fin
    ).select_related('producto', 'venta', 'paciente', 'usuario_vendedor', 'lote_vendido').order_by('-fecha_venta')
    
    if request.GET.get('formato') == 'csv':
        import csv
        
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
    
    context = {
        'registros': registros,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_registros': registros.count(),
    }
    
    return render(request, 'farmacia/antibioticos/reporte_cofepris.html', context)


@login_required
def generar_etiquetas(request):
    """
    Vista para generar etiquetas con código de barras (Code128).
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = GenerarEtiquetasForm(empresa=empresa, data=request.POST)
        
        if form.is_valid():
            try:
                productos = form.cleaned_data['productos']
                incluir_precio = form.cleaned_data['incluir_precio']
                incluir_caducidad = form.cleaned_data['incluir_caducidad']
                tamaño_etiqueta = form.cleaned_data['tamaño_etiqueta']
                cantidad_por_producto = form.cleaned_data['cantidad_por_producto']
                
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.units import mm
                from reportlab.graphics.barcode import code128
                from io import BytesIO
                
                buffer = BytesIO()
                
                if tamaño_etiqueta == 'zebra_4x6':
                    page_width = 4 * 25.4 * mm
                    page_height = 6 * 25.4 * mm
                elif tamaño_etiqueta == 'dymo_2x1':
                    page_width = 2 * 25.4 * mm
                    page_height = 1 * 25.4 * mm
                else:
                    page_width, page_height = A4
                
                p = canvas.Canvas(buffer, pagesize=(page_width, page_height))
                
                for producto in productos:
                    for i in range(cantidad_por_producto):
                        y_position = page_height - 20*mm
                        
                        codigo = producto.codigo_barras or f"PROD-{producto.id:06d}"
                        barcode = code128.Code128(codigo, barHeight=15*mm, barWidth=0.8)
                        barcode.drawOn(p, 10*mm, y_position - 15*mm)
                        
                        p.setFont("Helvetica-Bold", 12)
                        p.drawString(10*mm, y_position - 20*mm, producto.nombre[:40])
                        
                        if incluir_precio and producto.precio_publico:
                            p.setFont("Helvetica", 18)
                            p.drawString(10*mm, y_position - 28*mm, f"${producto.precio_publico:,.2f}")
                        
                        if incluir_caducidad:
                            lote_proximo = producto.lotes.filter(cantidad__gt=0).order_by('fecha_caducidad').first()
                            if lote_proximo:
                                p.setFont("Helvetica", 8)
                                p.drawString(10*mm, y_position - 35*mm, f"Cad: {lote_proximo.fecha_caducidad.strftime('%m/%Y')}")
                        
                        p.showPage()
                
                p.save()
                buffer.seek(0)
                
                response = HttpResponse(buffer, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="etiquetas_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
                return response
                
            except (ValueError, TypeError, IOError, ImportError, KeyError, Exception) as e:
                # Nota: reportlab puede lanzar muchas excepciones internas, se usa Exception explícitamente justificado.
                # Justificación: Integración externa (generación de PDF) propensa a fallos no controlados.
                messages.error(request, f'❌ Error al generar etiquetas: {str(e)}')
    else:
        form = GenerarEtiquetasForm(empresa=empresa)
    
    return render(request, 'farmacia/generar_etiquetas.html', {
        'form': form
    })
