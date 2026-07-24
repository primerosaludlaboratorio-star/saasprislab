"""
MOTOR FINANCIERO (Cortes y Caja)
REGLA: Reportes dinámicos con filtrado y exportación Excel/PDF.
PRIS Financiero: acceso a queries para resúmenes ejecutivos por voz (solo Dirección).
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils.html import escape
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
import csv
import io

from core.models import Venta, Pago, GastoCaja, Empresa
from core.decorators import role_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def genera_reporte_caja(request):
    """
    Genera reporte de caja con filtrado dinámico.
    REGLA: Reportes dinámicos con exportación Excel/PDF.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.shortcuts import redirect
        from django.contrib import messages
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')
    
    # Parámetros de filtrado
    hoy = timezone.localdate()
    fecha_inicio = request.GET.get('fecha_inicio', (hoy - timedelta(days=30)).strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fecha_fin', hoy.strftime('%Y-%m-%d'))
    tipo_reporte = request.GET.get('tipo', 'completo')  # completo, ventas, gastos, resumen
    formato = request.GET.get('formato', 'html')  # html, excel, pdf
    
    try:
        fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    except ValueError:
        fecha_inicio_dt = hoy - timedelta(days=30)
        fecha_fin_dt = hoy
    
    # Consultas base
    ventas = Venta.objects.filter(
        empresa=empresa,
        fecha__date__gte=fecha_inicio_dt,
        fecha__date__lte=fecha_fin_dt,
        estado='COMPLETADA',
    ).select_related('usuario', 'sucursal')
    
    gastos = GastoCaja.objects.filter(
        empresa=empresa,
        fecha__date__gte=fecha_inicio_dt,
        fecha__date__lte=fecha_fin_dt
    ).select_related('usuario')
    
    # Agregaciones
    total_ventas = ventas.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    total_gastos = gastos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    saldo_neto = total_ventas - total_gastos
    num_ventas = ventas.count()
    num_gastos = gastos.count()
    
    # Desglose por método de pago (siempre venta__empresa + fechas; nunca venta__in sin tenant explícito)
    _pago_base = {
        'venta__empresa': empresa,
        'venta__fecha__date__gte': fecha_inicio_dt,
        'venta__fecha__date__lte': fecha_fin_dt,
        'venta__estado': 'COMPLETADA',
    }
    pagos_qs = Pago.objects.filter(**_pago_base)
    pagos_totales = pagos_qs.aggregate(
        efectivo=Sum('monto_efectivo'),
        tarjeta=Sum('monto_tarjeta'),
        transferencia=Sum('monto_transferencia'),
    )
    pagos_efectivo = pagos_totales['efectivo'] or Decimal('0.00')
    pagos_tarjeta = pagos_totales['tarjeta'] or Decimal('0.00')
    pagos_transferencia = pagos_totales['transferencia'] or Decimal('0.00')
    
    # Datos para el reporte
    datos_reporte = {
        'fecha_inicio': fecha_inicio_dt,
        'fecha_fin': fecha_fin_dt,
        'total_ventas': total_ventas,
        'total_gastos': total_gastos,
        'saldo_neto': saldo_neto,
        'num_ventas': num_ventas,
        'num_gastos': num_gastos,
        'pagos_efectivo': pagos_efectivo,
        'pagos_tarjeta': pagos_tarjeta,
        'pagos_transferencia': pagos_transferencia,
    }

    # Exportación según formato
    if formato == 'excel':
        datos_reporte['ventas_detalle'] = list(ventas[:100])
        return exportar_reporte_excel(datos_reporte, empresa)
    elif formato == 'pdf':
        datos_reporte['ventas_detalle'] = list(ventas[:100])
        return exportar_reporte_pdf(datos_reporte, empresa)
    else:
        # HTML ligero: respuesta directa para evitar el costo del motor de plantillas
        empresa_nombre = escape(empresa.nombre or '')
        fecha_inicio_txt = escape(fecha_inicio)
        fecha_fin_txt = escape(fecha_fin)
        html = f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Reporte de Caja</title>
  <style>
    body {{ margin:0; font-family: system-ui,-apple-system,Segoe UI,Roboto,sans-serif; background:#0f172a; color:#e5e7eb; }}
    .wrap {{ max-width:1200px; margin:0 auto; padding:24px; }}
    .head {{ display:flex; justify-content:space-between; gap:16px; align-items:center; margin-bottom:20px; flex-wrap:wrap; }}
    h1 {{ margin:0; font-size:28px; }}
    p {{ margin:6px 0 0; color:#94a3b8; }}
    .actions a {{ display:inline-block; padding:10px 14px; border-radius:12px; text-decoration:none; margin-right:8px; color:#e5e7eb; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.08); }}
    .actions a.primary {{ background:rgba(34,197,94,.16); border-color:rgba(34,197,94,.35); }}
    .grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-bottom:18px; }}
    .card {{ background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); border-radius:18px; padding:16px; }}
    .label {{ color:#94a3b8; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
    .value {{ font-size:28px; font-weight:700; margin-top:8px; }}
    .ok {{ color:#22c55e; }} .bad {{ color:#ef4444; }}
    .sub {{ color:#94a3b8; margin-top:6px; font-size:13px; }}
    .panel {{ background:#111827; border:1px solid rgba(255,255,255,.08); border-radius:18px; overflow:hidden; margin-top:18px; }}
    .panel h2 {{ margin:0; padding:16px 18px; border-bottom:1px solid rgba(255,255,255,.08); font-size:18px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ padding:12px 16px; border-bottom:1px solid rgba(255,255,255,.08); }}
    th {{ color:#94a3b8; text-transform:uppercase; font-size:12px; text-align:left; }}
    .num {{ text-align:right; }}
    .note {{ color:#94a3b8; font-size:13px; padding:14px 18px 18px; }}
    @media (max-width:980px) {{ .grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
    @media (max-width:640px) {{ .grid {{ grid-template-columns:1fr; }} .wrap {{ padding:14px; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div>
        <h1>Reporte de Caja</h1>
        <p>{empresa_nombre} · {fecha_inicio_txt} a {fecha_fin_txt}</p>
      </div>
      <div class="actions">
        <a class="primary" href="?formato=pdf">PDF</a>
        <a href="?formato=excel">Excel</a>
      </div>
    </div>
    <div class="grid">
      <div class="card"><div class="label">Total ventas</div><div class="value">${float(datos_reporte['total_ventas']):.2f}</div><div class="sub">{datos_reporte['num_ventas']} ventas completadas</div></div>
      <div class="card"><div class="label">Total gastos</div><div class="value bad">${float(datos_reporte['total_gastos']):.2f}</div><div class="sub">{datos_reporte['num_gastos']} egresos</div></div>
      <div class="card"><div class="label">Saldo neto</div><div class="value {'ok' if datos_reporte['saldo_neto'] >= 0 else 'bad'}">${float(datos_reporte['saldo_neto']):.2f}</div><div class="sub">Ventas menos gastos</div></div>
      <div class="card"><div class="label">Cobro efectivo</div><div class="value">${float(datos_reporte['pagos_efectivo']):.2f}</div><div class="sub">Efectivo registrado</div></div>
    </div>
    <div class="panel">
      <h2>Desglose de pagos</h2>
      <table>
        <thead><tr><th>Método</th><th class="num">Monto</th></tr></thead>
        <tbody>
          <tr><td>Efectivo</td><td class="num">${float(datos_reporte['pagos_efectivo']):.2f}</td></tr>
          <tr><td>Tarjeta</td><td class="num">${float(datos_reporte['pagos_tarjeta']):.2f}</td></tr>
          <tr><td>Transferencia</td><td class="num">${float(datos_reporte['pagos_transferencia']):.2f}</td></tr>
        </tbody>
      </table>
      <div class="note">Este reporte resume caja. Para detalle diario completo usa Ingresos/Egresos o Flujo de Caja.</div>
    </div>
  </div>
</body>
</html>
"""
        return HttpResponse(html)


def exportar_reporte_excel(datos_reporte, empresa):
    """Exporta reporte de caja a Excel (CSV)."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="reporte_caja_{empresa.nombre}_{datos_reporte["fecha_inicio"]}_{datos_reporte["fecha_fin"]}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['REPORTE DE CAJA', empresa.nombre])
    writer.writerow(['Período:', f'{datos_reporte["fecha_inicio"]} a {datos_reporte["fecha_fin"]}'])
    writer.writerow([])
    
    # Resumen
    writer.writerow(['RESUMEN'])
    writer.writerow(['Total Ventas', f'${datos_reporte["total_ventas"]:.2f}'])
    writer.writerow(['Total Gastos', f'${datos_reporte["total_gastos"]:.2f}'])
    writer.writerow(['Saldo Neto', f'${datos_reporte["saldo_neto"]:.2f}'])
    writer.writerow([])
    
    # Desglose de pagos
    writer.writerow(['DESGLOSE DE PAGOS'])
    writer.writerow(['Efectivo', f'${datos_reporte["pagos_efectivo"]:.2f}'])
    writer.writerow(['Tarjeta', f'${datos_reporte["pagos_tarjeta"]:.2f}'])
    writer.writerow(['Transferencia', f'${datos_reporte["pagos_transferencia"]:.2f}'])
    writer.writerow([])
    
    # Detalle de ventas
    writer.writerow(['DETALLE DE VENTAS'])
    writer.writerow(['Folio', 'Fecha', 'Total', 'Método Pago', 'Usuario'])
    for venta in datos_reporte['ventas_detalle']:
        metodo_pago = venta.pagos.first().metodo if venta.pagos.exists() else 'N/A'
        writer.writerow([
            venta.folio_operacion or venta.id,
            venta.fecha.strftime('%Y-%m-%d %H:%M') if venta.fecha else '',
            f'${venta.total:.2f}',
            metodo_pago,
            venta.usuario.username if venta.usuario else 'N/A'
        ])
    
    return response


def exportar_reporte_pdf(datos_reporte, empresa):
    """Exporta reporte de caja a PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#003366'),
        alignment=1  # Centrado
    )
    elements.append(Paragraph(f'REPORTE DE CAJA - {empresa.nombre}', title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Período
    elements.append(Paragraph(
        f'Período: {datos_reporte["fecha_inicio"]} a {datos_reporte["fecha_fin"]}',
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.3*inch))
    
    # Resumen
    resumen_data = [
        ['CONCEPTO', 'MONTO'],
        ['Total Ventas', f'${datos_reporte["total_ventas"]:.2f}'],
        ['Total Gastos', f'${datos_reporte["total_gastos"]:.2f}'],
        ['Saldo Neto', f'${datos_reporte["saldo_neto"]:.2f}'],
    ]
    
    resumen_table = Table(resumen_data, colWidths=[4*inch, 2*inch])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(resumen_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Desglose de pagos
    pagos_data = [
        ['MÉTODO DE PAGO', 'MONTO'],
        ['Efectivo', f'${datos_reporte["pagos_efectivo"]:.2f}'],
        ['Tarjeta', f'${datos_reporte["pagos_tarjeta"]:.2f}'],
        ['Transferencia', f'${datos_reporte["pagos_transferencia"]:.2f}'],
    ]
    
    pagos_table = Table(pagos_data, colWidths=[4*inch, 2*inch])
    pagos_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(pagos_table)
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_caja_{empresa.nombre}_{datos_reporte["fecha_inicio"]}_{datos_reporte["fecha_fin"]}.pdf"'
    return response


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
@require_http_methods(["GET"])
def api_resumen_ejecutivo_pris(request):
    """
    API para PRIS: Resumen ejecutivo financiero por voz (solo Dirección).
    PRIS Financiero: Acceso exclusivo para rol de Dirección.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Usuario sin empresa asignada.'
        }, status=403)
    
    # Parámetros
    dias = int(request.GET.get('dias', 7))
    fecha_fin = timezone.localdate()
    fecha_inicio = fecha_fin - timedelta(days=dias)
    
    # Consultas optimizadas
    ventas = Venta.objects.filter(
        empresa=empresa,
        fecha__date__gte=fecha_inicio,
        fecha__date__lte=fecha_fin
    )
    
    gastos = GastoCaja.objects.filter(
        empresa=empresa,
        fecha__date__gte=fecha_inicio,
        fecha__date__lte=fecha_fin
    )
    
    # Agregaciones
    total_ventas = ventas.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    total_gastos = gastos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    saldo_neto = total_ventas - total_gastos
    num_ventas = ventas.count()
    
    # Promedio diario
    promedio_diario = total_ventas / dias if dias > 0 else Decimal('0.00')
    
    # Resumen ejecutivo en texto natural
    resumen_texto = f"""
    Resumen financiero de los últimos {dias} días:
    Total de ventas: ${total_ventas:,.2f}
    Total de gastos: ${total_gastos:,.2f}
    Saldo neto: ${saldo_neto:,.2f}
    Número de ventas: {num_ventas}
    Promedio diario: ${promedio_diario:,.2f}
    """
    
    return JsonResponse({
        'status': 'success',
        'resumen': resumen_texto.strip(),
        'datos': {
            'total_ventas': float(total_ventas),
            'total_gastos': float(total_gastos),
            'saldo_neto': float(saldo_neto),
            'num_ventas': num_ventas,
            'promedio_diario': float(promedio_diario),
            'periodo': f'{fecha_inicio} a {fecha_fin}'
        }
    })
