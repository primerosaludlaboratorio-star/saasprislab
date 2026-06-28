"""
Listado e historial de pacientes en contexto laboratorio.
"""
from collections import Counter

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from core.models import (
    Paciente, OrdenDeServicio, DetalleOrden,
)
from core.lims_cart import detalle_orden_etiqueta


@login_required
def lista_pacientes_lab(request):
    """
    Listado de pacientes filtrado al contexto de Laboratorio.
    El link de cada paciente va al historial de estudios (no al expediente clínico).
    Acceso: roles LABORATORIO, RECEPCION, QUIMICO, Superusuario.
    """
    empresa = getattr(request.user, 'empresa', None)
    query = request.GET.get('q', '').strip()

    qs = Paciente.objects.filter(empresa=empresa, activo=True).order_by('nombre_completo')
    if query:
        qs = qs.filter(
            Q(nombre_completo__icontains=query) |
            Q(telefono__icontains=query) |
            Q(nombres__icontains=query) |
            Q(apellido_paterno__icontains=query) |
            Q(apellido_materno__icontains=query)
        )

    from django.core.paginator import Paginator
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'core/lab_pacientes/lista.html', {
        'pacientes': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'query': query,
    })


@login_required
def historial_lab_paciente(request, paciente_id):
    """
    Historial de laboratorio de un paciente: visitas, órdenes y resultados.
    EXCLUSIVO contexto laboratorio — sin historia clínica ni consultas médicas.
    Acceso: roles LABORATORIO, RECEPCION, QUIMICO, MEDICO (como referencia), Superusuario.
    """
    empresa = getattr(request.user, 'empresa', None)
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

    # Todas las órdenes del paciente ordenadas por fecha descendente
    ordenes = (
        OrdenDeServicio.objects
        .filter(paciente=paciente, empresa=empresa)
        .prefetch_related('detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims')
        .order_by('-fecha_creacion')
    )

    total_visitas = ordenes.count()
    ultima_visita = ordenes.first()

    _det_labels = []
    for d in DetalleOrden.objects.filter(
        orden__paciente=paciente, orden__empresa=empresa
    ).select_related('analito', 'perfil_lims', 'paquete_lims')[:800]:
        lab = detalle_orden_etiqueta(d).strip()
        if lab:
            _det_labels.append(lab)
    estudios_frecuentes = [
        {'linea_label': lab, 'veces': n}
        for lab, n in Counter(_det_labels).most_common(5)
    ]

    return render(request, 'core/lab_pacientes/historial.html', {
        'paciente': paciente,
        'ordenes': ordenes[:50],   # Últimas 50 órdenes
        'total_visitas': total_visitas,
        'ultima_visita': ultima_visita,
        'estudios_frecuentes': estudios_frecuentes,
    })
