"""
Vistas del módulo de Contabilidad y Facturación
PRISLAB V5.0 - CFDI 4.0
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.decorators import role_required
from django.contrib import messages
from django.utils.html import escape as html_escape
from django.http import HttpResponse, JsonResponse
from django.db import transaction, IntegrityError
from django.db.models import Sum
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Q

from .models import ClienteFacturacion, FacturaCFDI, ConceptoFactura, ImpuestoConcepto
from .services.timbrado_cfdi import ejecutar_timbrado
from core.models import Paciente


def _empresa_fiscal(request):
    # FIX V8.2 SAT TENANT: misma empresa que middleware (facturación = tenant activo)
    return getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)


# ============================================================================
# CLIENTES DE FACTURACIÓN
# ============================================================================

@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def lista_clientes(request):
    """
    Lista de clientes de facturación
    """
    empresa_u = _empresa_fiscal(request)
    if not empresa_u:
        messages.error(request, 'No hay empresa activa para facturación.')
        return redirect('home')
    clientes = ClienteFacturacion.objects.filter(activo=True, empresa=empresa_u).order_by('razon_social')
    
    # Búsqueda
    q = request.GET.get('q')
    if q:
        clientes = clientes.filter(
            Q(rfc__icontains=q) | 
            Q(razon_social__icontains=q) | 
            Q(email__icontains=q)
        )
    
    context = {
        'clientes': clientes,
        'q': q or '',
    }
    
    return render(request, 'contabilidad/clientes/lista.html', context)


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def crear_cliente(request):
    """
    Crear nuevo cliente de facturación
    """
    if request.method == 'POST':
        try:
            empresa_c = _empresa_fiscal(request)
            if not empresa_c:
                messages.error(request, 'No hay empresa activa para registrar clientes fiscales.')
                return redirect('home')
            paciente = None
            paciente_id = request.POST.get('paciente_id')
            if paciente_id:
                paciente = Paciente.objects.get(id=paciente_id, empresa=empresa_c)

            cliente = ClienteFacturacion.objects.create(
                paciente=paciente,
                empresa=empresa_c,
                rfc=request.POST.get('rfc').strip().upper(),
                razon_social=request.POST.get('razon_social').strip(),
                email=request.POST.get('email').strip(),
                codigo_postal=request.POST.get('codigo_postal').strip(),
                regimen_fiscal=request.POST.get('regimen_fiscal'),
                uso_cfdi_default=request.POST.get('uso_cfdi_default', 'D01'),
            )
            
            messages.success(request, f'Cliente {cliente.razon_social} creado exitosamente.')
            return redirect('contabilidad:lista_clientes')
            
        except (IntegrityError, ValidationError, ValueError) as e:
            messages.error(request, f'Error al crear cliente: {str(e)}')
    
    # GET
    empresa_u = _empresa_fiscal(request)
    if not empresa_u:
        messages.error(request, 'No hay empresa activa para facturación.')
        return redirect('home')
    pacientes = Paciente.objects.filter(activo=True, empresa=empresa_u).order_by('nombre_completo')
    
    context = {
        'pacientes': pacientes,
    }
    
    return render(request, 'contabilidad/clientes/crear.html', context)


# ============================================================================
# FACTURAS
# ============================================================================

@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def lista_facturas(request):
    """
    Lista de facturas emitidas — filtrada por empresa del usuario (multi-tenant)
    """
    empresa = _empresa_fiscal(request)

    # FIX V8.2 SAT TENANT: criterio fiscal = cliente del CFDI (emisor/receptor por tenant)
    if empresa:
        facturas = FacturaCFDI.objects.filter(
            empresa=empresa,
        ).select_related('cliente', 'usuario_creo').order_by('-fecha_emision')
    else:
        messages.error(request, 'No hay empresa activa para listar facturas.')
        return redirect('home')

    # Filtros adicionales
    estado = request.GET.get('estado')
    if estado:
        facturas = facturas.filter(estado=estado)

    cliente_id = request.GET.get('cliente')
    if cliente_id:
        facturas = facturas.filter(
            cliente_id=cliente_id,
            empresa=empresa,
        )

    # Estadísticas — calculadas sobre el mismo QS ya acotado
    stats = {
        'total': facturas.count(),
        'timbradas': facturas.filter(estado='TIMBRADO').count(),
        'borradores': facturas.filter(Q(estado='BORRADOR') | Q(estado='PENDIENTE')).count(),
        'monto_total': facturas.filter(estado='TIMBRADO').aggregate(Sum('total'))['total__sum'] or 0,
    }

    context = {
        'facturas': facturas[:100],
        'stats': stats,
        'clientes': ClienteFacturacion.objects.filter(activo=True, empresa=empresa),
    }
    
    return render(request, 'contabilidad/facturas/lista.html', context)


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def crear_factura(request):
    """
    Crear nueva factura (borrador)
    """
    if request.method == 'POST':
        try:
            with transaction.atomic():
                empresa_u = _empresa_fiscal(request)
                if not empresa_u:
                    messages.error(request, 'No hay empresa activa para emitir facturas.')
                    return redirect('home')
                cliente = ClienteFacturacion.objects.get(
                    id=request.POST.get('cliente_id'),
                    empresa=empresa_u,
                )
                
                factura = FacturaCFDI.objects.create(
                    cliente=cliente,
                    serie=request.POST.get('serie', 'A'),
                    tipo_comprobante='I',
                    forma_pago=request.POST.get('forma_pago', '01'),
                    metodo_pago=request.POST.get('metodo_pago', 'PUE'),
                    subtotal=0,
                    total=0,
                    usuario_creo=request.user,
                )
                
                # Crear conceptos
                conceptos_data = request.POST.getlist('concepto_descripcion')
                cantidades = request.POST.getlist('concepto_cantidad')
                valores = request.POST.getlist('concepto_valor')
                
                subtotal = Decimal('0')
                total_impuestos = Decimal('0')
                
                for i, desc in enumerate(conceptos_data):
                    if desc.strip():
                        cantidad = Decimal(cantidades[i])
                        valor = Decimal(valores[i])
                        importe = cantidad * valor
                        
                        concepto = ConceptoFactura.objects.create(
                            factura=factura,
                            numero_linea=i + 1,
                            descripcion=desc.strip(),
                            cantidad=cantidad,
                            valor_unitario=valor,
                            importe=importe,
                            objeto_impuesto='02',  # Sí objeto de impuesto
                        )
                        
                        # IVA 16%
                        impuesto = ImpuestoConcepto.objects.create(
                            concepto=concepto,
                            tipo='TRASLADO',
                            impuesto='002',  # IVA
                            tasa_o_cuota=Decimal('0.16'),
                            tipo_factor='Tasa',
                            base=importe,
                        )
                        
                        subtotal += importe
                        total_impuestos += impuesto.importe
                
                # Actualizar totales
                factura.subtotal = subtotal
                factura.total_impuestos_trasladados = total_impuestos
                factura.total = subtotal + total_impuestos
                factura.save()
                
                messages.success(request, f'Factura {factura.folio_interno} creada como borrador.')
                return redirect('contabilidad:detalle_factura', factura_id=factura.id)
                
        except (IntegrityError, ValidationError, ValueError) as e:
            messages.error(request, f'Error al crear factura: {str(e)}')
    
    # GET
    empresa_u = _empresa_fiscal(request)
    if not empresa_u:
        messages.error(request, 'No hay empresa activa para emitir facturas.')
        return redirect('home')
    clientes = ClienteFacturacion.objects.filter(activo=True, empresa=empresa_u).order_by('razon_social')

    context = {
        'clientes': clientes,
    }

    return render(request, 'contabilidad/facturas/crear.html', context)


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def detalle_factura(request, factura_id):
    """
    Detalle de una factura
    """
    empresa = _empresa_fiscal(request)
    if not empresa:
        messages.error(request, 'No hay empresa activa para ver facturas.')
        return redirect('home')
    factura = get_object_or_404(
        FacturaCFDI.objects.select_related('cliente', 'usuario_creo'),
        id=factura_id,
        empresa=empresa,
    )
    
    conceptos = factura.conceptos.prefetch_related('impuestos').all()
    
    context = {
        'factura': factura,
        'conceptos': conceptos,
    }
    
    return render(request, 'contabilidad/facturas/detalle.html', context)


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def timbrar_factura(request, factura_id):
    """
    Timbrar una factura con Facturama (Punto 16: lock + Idempotency-Key determinista).
    """
    if request.method != 'POST':
        messages.error(request, 'Método no permitido')
        return redirect('contabilidad:lista_facturas')

    return ejecutar_timbrado(request, factura_id)


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def descargar_xml(request, factura_id):
    """Descarga el XML timbrado almacenado (PAC)."""
    empresa = _empresa_fiscal(request)
    if not empresa:
        messages.error(request, 'No hay empresa activa.')
        return redirect('home')
    factura = get_object_or_404(
        FacturaCFDI,
        id=factura_id,
        empresa=empresa,
    )
    if factura.estado != 'TIMBRADO' or not (factura.xml_timbrado or '').strip():
        messages.error(request, 'No hay XML timbrado disponible para esta factura.')
        return redirect('contabilidad:detalle_factura', factura_id=factura.id)
    safe_name = f"cfdi_{factura.folio_interno.replace(' ', '_')}.xml"
    response = HttpResponse(factura.xml_timbrado, content_type='application/xml; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{safe_name}"'
    return response


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def descargar_pdf(request, factura_id):
    """
    Descargar PDF de factura
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from io import BytesIO
    
    empresa = _empresa_fiscal(request)
    if not empresa:
        messages.error(request, 'No hay empresa activa.')
        return redirect('home')
    factura = get_object_or_404(
        FacturaCFDI,
        id=factura_id,
        empresa=empresa,
    )
    
    # Crear PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    elements.append(Paragraph(f"<b>FACTURA {factura.folio_interno}</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    # FIX V8.2 SAT TENANT: emisor = datos fiscales del tenant (core.Empresa)
    elements.append(Paragraph(
        f"<b>Emisor:</b> {html_escape(empresa.nombre)} &nbsp;|&nbsp; "
        f"<b>RFC:</b> {html_escape((empresa.rfc or '').strip() or '—')}",
        styles['Normal'],
    ))
    elements.append(Spacer(1, 12))
    
    # Información del cliente
    elements.append(Paragraph(f"<b>Cliente:</b> {factura.cliente.razon_social}", styles['Normal']))
    elements.append(Paragraph(f"<b>RFC:</b> {factura.cliente.rfc}", styles['Normal']))
    elements.append(Paragraph(f"<b>Fecha:</b> {factura.fecha_emision.strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # Tabla de conceptos
    data = [['#', 'Descripción', 'Cantidad', 'Precio', 'Importe']]
    for concepto in factura.conceptos.all():
        data.append([
            str(concepto.numero_linea),
            concepto.descripcion[:50],
            f"{concepto.cantidad:.2f}",
            f"${concepto.valor_unitario:,.2f}",
            f"${concepto.importe:,.2f}",
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    # Totales
    elements.append(Paragraph(f"<b>Subtotal:</b> ${factura.subtotal:,.2f}", styles['Normal']))
    elements.append(Paragraph(f"<b>IVA:</b> ${factura.total_impuestos_trasladados:,.2f}", styles['Normal']))
    elements.append(Paragraph(f"<b>TOTAL:</b> ${factura.total:,.2f}", styles['Heading2']))
    
    if factura.uuid_sat:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"<b>UUID SAT:</b> {factura.uuid_sat}", styles['Normal']))
    
    # Construir PDF
    doc.build(elements)
    
    # Retornar respuesta
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{factura.folio_interno}.pdf"'
    response.write(pdf)
    
    return response


# ============================================================================
# API / AJAX
# ============================================================================

@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def api_buscar_cliente(request):
    """
    API para buscar clientes (AJAX)
    """
    q = request.GET.get('q', '').strip()
    
    if len(q) < 3:
        return JsonResponse({'results': []})
    
    empresa = _empresa_fiscal(request)
    if not empresa:
        return JsonResponse({'results': [], 'error': 'sin_empresa'}, status=403)
    clientes = ClienteFacturacion.objects.filter(
        Q(rfc__icontains=q) | Q(razon_social__icontains=q),
        activo=True,
        empresa=empresa,
    )[:10]
    
    results = [
        {
            'id': c.id,
            'rfc': c.rfc,
            'razon_social': c.razon_social,
            'email': c.email,
        }
        for c in clientes
    ]
    
    return JsonResponse({'results': results})


# ============================================================================
# AUTOFACTURA PÚBLICA POR FOLIO — /f/<folio>/
# Acceso sin login (escaneo QR desde ticket de venta)
# ============================================================================
def autofactura_por_folio(request, folio):
    """Redirige el acceso corto /f/<folio>/ al portal de autofacturación."""
    from django.shortcuts import redirect
    return redirect(f'/contabilidad/autofactura/?folio={folio}')

