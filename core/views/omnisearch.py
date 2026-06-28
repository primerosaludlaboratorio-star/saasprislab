"""
PRISLAB V5 - OmniSearch (Buscador Global)
Busca pacientes por nombre/UUID y órdenes por folio.
Usado desde la navbar en base.html.
"""
import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from core.models import OrdenDeServicio, Paciente

logger = logging.getLogger(__name__)


@login_required
@require_GET
def api_omnisearch(request):
    """
    GET /api/omnisearch/?q=texto
    Busca pacientes (nombre, UUID) y ordenes (folio) de la empresa del usuario.
    Retorna max 5 resultados de cada tipo.
    """
    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return JsonResponse({'resultados': [], 'total': 0})

    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'resultados': [], 'total': 0})
    resultados = []

    # --- Buscar Pacientes ---
    q_filter = (
        Q(nombre_completo__icontains=q) |
        Q(uuid__icontains=q) |
        Q(telefono__icontains=q) |
        Q(nombres__icontains=q) |
        Q(apellido_paterno__icontains=q)
    )
    if q.isdigit():
        q_filter |= Q(id=int(q))
    pacientes = Paciente.objects.filter(
        empresa=empresa
    ).filter(q_filter).order_by('-id')[:5]

    for p in pacientes:
        resultados.append({
            'tipo': 'paciente',
            'icono': 'fa-user',
            'color': '#0d6efd',
            'titulo': p.nombre_completo,
            'subtitulo': f'Tel: {p.telefono or "N/D"} | {p.sexo or ""}',
            'url': f'/pacientes/{p.id}/expediente/',
            'id': p.id,
        })

    # --- Buscar Ordenes de Laboratorio ---
    ordenes = OrdenDeServicio.objects.filter(
        empresa=empresa
    ).filter(
        Q(folio_orden__icontains=q) |
        Q(paciente__nombre_completo__icontains=q)
    ).select_related('paciente').order_by('-fecha_creacion')[:5]

    for o in ordenes:
        estado = o.get_estado_clinico_display() if hasattr(o, 'get_estado_clinico_display') else o.estado_clinico
        resultados.append({
            'tipo': 'orden',
            'icono': 'fa-flask',
            'color': '#198754',
            'titulo': f'Orden {o.folio_orden or o.id}',
            'subtitulo': f'{o.paciente.nombre_completo} | {estado}',
            'url': f'/laboratorio/captura/{o.id}/',
            'id': o.id,
        })

    return JsonResponse({
        'resultados': resultados,
        'total': len(resultados),
        'query': q,
    })
