"""
core/views/medico/ultrasonido.py
Lista de trabajo, captura y descarga PDF de reportes de ultrasonido.
"""
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone as django_timezone

from consultorio.models import ReporteUltrasonido
from core.models import Paciente
from core.utils.empresa_request import empresa_efectiva_request
import logging


@login_required
def lista_trabajo_usg(request):
    """Lista de reportes de ultrasonido de la empresa."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    estado = request.GET.get('estado', '')
    qs = ReporteUltrasonido.objects.filter(empresa=empresa).select_related('paciente', 'medico')
    if estado:
        qs = qs.filter(estado=estado)

    paginator = Paginator(qs.order_by('-fecha_estudio'), 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'core/medico/lista_trabajo_usg.html', {
        'empresa': empresa,
        'page_obj': page_obj,
        'estado_filtro': estado,
        'estados': ReporteUltrasonido.ESTADO_CHOICES,
    })


@login_required
def captura_reporte_usg(request, paciente_id=None):
    """Vista para capturar/crear un nuevo reporte de ultrasonido."""
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('lista_trabajo_usg')

    paciente = None
    if paciente_id:
        paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

    if request.method == 'POST':
        try:
            pac_id = request.POST.get('paciente_id')
            paciente = get_object_or_404(Paciente, id=pac_id, empresa=empresa)
            medico = getattr(request.user, 'medico', None)
            reporte = ReporteUltrasonido.objects.create(
                empresa=empresa,
                paciente=paciente,
                medico=medico,
                tipo_estudio=request.POST.get('tipo_estudio', 'GENERAL'),
                hallazgos=request.POST.get('hallazgos', ''),
                conclusion=request.POST.get('conclusion', ''),
                estado='PENDIENTE',
            )
            messages.success(request, f'Reporte USG creado: {reporte.id}')
            return redirect('lista_trabajo_usg')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en captura_reporte_usg (ultrasonido.py)")
            messages.error(request, f'Error al crear reporte: {e}')

    pacientes = Paciente.objects.filter(empresa=empresa).order_by('nombres')[:50]
    return render(request, 'core/medico/captura_reporte_usg.html', {
        'empresa': empresa,
        'paciente': paciente,
        'pacientes': pacientes,
    })


@login_required
def descargar_pdf_ultrasonido(request, reporte_id):
    """Genera y descarga el PDF de un reporte de ultrasonido."""
    from core.utils.pdf_generator import render_to_pdf
    empresa = empresa_efectiva_request(request)
    reporte = get_object_or_404(ReporteUltrasonido, id=reporte_id, empresa=empresa)
    pdf = render_to_pdf('core/medico/reporte_usg_pdf.html', {'reporte': reporte, 'empresa': empresa})
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename=usg_{reporte.id}.pdf'
        return response
    messages.error(request, 'No se pudo generar el PDF.')
    return redirect('lista_trabajo_usg')