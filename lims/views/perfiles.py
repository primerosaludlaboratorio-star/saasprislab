"""Ventana B — Perfiles: lista, edición con Typeahead de analitos."""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from core.tenant import tenant_protected_get
from core.utils.tenant_strict import empresa_desde_request
from lims.models import Analito, PerfilLims
from lims.views.tenant_lims import empresa_lims


def _check_perm(user):
    # PATRÓN CORRECTO: Validar empresa siempre, pero permitir superuser/staff CON empresa válida
    if not getattr(user, 'empresa', None):
        return False
    
    # Superuser/staff con empresa válida pueden operar
    if user.is_superuser or user.is_staff:
        return True
    
    rol = (getattr(user, 'rol', '') or '').upper()
    if rol in ('ADMIN', 'ADMINISTRADOR', 'LABORATORIO', 'LIMS'):
        return True
    return user.groups.filter(name__in=['LABORATORIO', 'LIMS', 'ADMIN']).exists()


@login_required
def lista(request):
    if not _check_perm(request.user):
        return redirect('home')
    empresa = empresa_lims(request)
    if not empresa:
        messages.error(request, 'No hay empresa activa para el catálogo LIMS.')
        return redirect('home')
    # FIX V8.2 LIMS TENANT
    perfiles = (
        PerfilLims.objects.filter(empresa=empresa)
        .annotate(num_analitos=Count('analitos'))
        .order_by('nombre')
    )
    return render(request, 'lims/perfiles_lista.html', {
        'perfiles': perfiles,
        'total': perfiles.count(),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def nuevo(request):
    if not _check_perm(request.user):
        return redirect('home')
    if request.method == 'POST':
        # FIX V8.2 LIMS TENANT: alinear con empresa_actual del middleware
        empresa = empresa_desde_request(request) or empresa_lims(request)
        if not empresa:
            messages.error(request, 'No hay empresa activa para crear perfiles.')
            return redirect('home')
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        if nombre:
            perfil = PerfilLims.objects.create(empresa=empresa, nombre=nombre, descripcion=descripcion)
            return redirect('lims_perfil_detalle', pk=perfil.pk)
    return render(request, 'lims/perfil_editar.html', {'perfil': None})


@login_required
def detalle(request, pk):
    if not _check_perm(request.user):
        return redirect('home')
    perfil = tenant_protected_get(PerfilLims, pk=pk)
    return render(request, 'lims/perfil_detalle.html', {
        'perfil': perfil,
        'analitos': perfil.analitos.order_by('departamento', 'nombre'),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def editar(request, pk):
    if not _check_perm(request.user):
        return redirect('home')
    perfil = tenant_protected_get(PerfilLims, pk=pk)
    if request.method == 'POST':
        perfil.nombre      = request.POST.get('nombre', perfil.nombre).strip()
        perfil.descripcion = request.POST.get('descripcion', '').strip()
        perfil.activo      = request.POST.get('activo') == '1'
        perfil.save()
        return redirect('lims_perfil_detalle', pk=pk)
    return render(request, 'lims/perfil_editar.html', {'perfil': perfil})


# ── APIs Typeahead ────────────────────────────────────────────────────────────

@login_required
def api_buscar_analitos(request):
    """
    GET /lims/api/analitos/buscar/?q=termo
    Retorna JSON con analitos que coincidan (SIN filtro es_vendible_individualmente).
    """
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos', 'resultados': []}, status=403)

    empresa = empresa_lims(request)
    if not empresa:
        return JsonResponse({'error': 'Sin empresa activa', 'resultados': []}, status=403)

    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return JsonResponse({'resultados': []})

    # FIX V8.2 LIMS TENANT
    qs = (
        Analito.objects.filter(empresa=empresa, activo=True)
        .filter(
            Q(codigo__icontains=q) | Q(abreviatura__icontains=q) |
            Q(nombre__icontains=q) | Q(departamento__icontains=q)
        )
        .values('id', 'codigo', 'abreviatura', 'nombre', 'departamento', 'unidades')[:20]
    )

    return JsonResponse({'resultados': list(qs)})


@login_required
@require_http_methods(['POST'])
def api_agregar_analito(request, pk):
    """POST → agrega analito a perfil."""
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    perfil = tenant_protected_get(PerfilLims, pk=pk)
    try:
        body = json.loads(request.body)
        analito_id = int(body.get('analito_id', 0))
    except Exception:
        analito_id = int(request.POST.get('analito_id', 0))
    analito = tenant_protected_get(Analito, pk=analito_id)
    perfil.analitos.add(analito)
    return JsonResponse({
        'ok': True,
        'analito': {
            'id': analito.pk,
            'nombre': analito.nombre,
            'abreviatura': analito.abreviatura,
            'departamento': analito.departamento,
        },
    })


@login_required
@require_http_methods(['POST'])
def api_quitar_analito(request, pk, analito_pk):
    """POST → quita analito del perfil."""
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    perfil = tenant_protected_get(PerfilLims, pk=pk)
    analito = tenant_protected_get(Analito, pk=analito_pk)
    perfil.analitos.remove(analito)
    return JsonResponse({'ok': True})
