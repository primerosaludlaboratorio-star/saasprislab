"""Ventana C — Paquetes: lista y editor (analitos individuales + perfiles)."""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from core.tenant import tenant_protected_get
from core.utils.tenant_strict import empresa_desde_request
from lims.models import Analito, PerfilLims, PaqueteLims
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
    paquetes = (
        PaqueteLims.objects.filter(empresa=empresa)
        .annotate(
            n_analitos=Count('analitos', distinct=True),
            n_perfiles=Count('perfiles', distinct=True),
        )
        .order_by('nombre')
    )
    return render(request, 'lims/paquetes_lista.html', {
        'paquetes': paquetes,
        'total': paquetes.count(),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def nuevo(request):
    if not _check_perm(request.user):
        return redirect('home')
    if request.method == 'POST':
        # FIX V8.2 LIMS TENANT: misma empresa que el resto de ventanas (sesión / middleware)
        empresa = empresa_desde_request(request) or empresa_lims(request)
        if not empresa:
            messages.error(request, 'No hay empresa activa para crear paquetes.')
            return redirect('home')
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        venta_publico = request.POST.get('venta_publico') == '1'
        if nombre:
            paquete = PaqueteLims.objects.create(
                empresa=empresa, nombre=nombre, descripcion=descripcion,
                venta_publico=venta_publico,
            )
            return redirect('lims_paquete_detalle', pk=paquete.pk)
    emp_sel = empresa_lims(request)
    if not emp_sel:
        messages.error(request, 'No hay empresa activa para el catálogo LIMS.')
        return redirect('home')
    perfiles = PerfilLims.objects.filter(empresa=emp_sel, activo=True).order_by('nombre')
    return render(request, 'lims/paquete_editar.html', {
        'paquete': None, 'perfiles': perfiles,
    })


@login_required
def detalle(request, pk):
    if not _check_perm(request.user):
        return redirect('home')
    paquete = tenant_protected_get(PaqueteLims, pk=pk)
    return render(request, 'lims/paquete_detalle.html', {
        'paquete': paquete,
        'analitos_directos': paquete.analitos.order_by('departamento', 'nombre'),
        'perfiles': paquete.perfiles.order_by('nombre'),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def editar(request, pk):
    if not _check_perm(request.user):
        return redirect('home')
    paquete = tenant_protected_get(PaqueteLims, pk=pk)
    if request.method == 'POST':
        paquete.nombre        = request.POST.get('nombre', paquete.nombre).strip()
        paquete.descripcion   = request.POST.get('descripcion', '').strip()
        paquete.venta_publico = request.POST.get('venta_publico') == '1'
        paquete.activo        = request.POST.get('activo') == '1'
        paquete.save()
        return redirect('lims_paquete_detalle', pk=pk)
    emp_sel = empresa_lims(request)
    if not emp_sel:
        messages.error(request, 'No hay empresa activa para el catálogo LIMS.')
        return redirect('home')
    perfiles = PerfilLims.objects.filter(empresa=emp_sel, activo=True).order_by('nombre')
    return render(request, 'lims/paquete_editar.html', {
        'paquete': paquete, 'perfiles': perfiles,
    })


# ── APIs de composición ────────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def api_agregar_analito(request, pk):
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    paquete = tenant_protected_get(PaqueteLims, pk=pk)
    try:
        body = json.loads(request.body)
        analito_id = int(body.get('analito_id', 0))
    except Exception:
        analito_id = int(request.POST.get('analito_id', 0))
    analito = tenant_protected_get(Analito, pk=analito_id)
    paquete.analitos.add(analito)
    return JsonResponse({'ok': True, 'analito': {'id': analito.pk, 'nombre': analito.nombre}})


@login_required
@require_http_methods(['POST'])
def api_quitar_analito(request, pk, analito_pk):
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    paquete = tenant_protected_get(PaqueteLims, pk=pk)
    paquete.analitos.remove(tenant_protected_get(Analito, pk=analito_pk))
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['POST'])
def api_agregar_perfil(request, pk):
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    paquete = tenant_protected_get(PaqueteLims, pk=pk)
    try:
        body = json.loads(request.body)
        perfil_id = int(body.get('perfil_id', 0))
    except Exception:
        perfil_id = int(request.POST.get('perfil_id', 0))
    perfil = tenant_protected_get(PerfilLims, pk=perfil_id)
    paquete.perfiles.add(perfil)
    return JsonResponse({'ok': True, 'perfil': {'id': perfil.pk, 'nombre': perfil.nombre}})


@login_required
@require_http_methods(['POST'])
def api_quitar_perfil(request, pk, perfil_pk):
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    paquete = tenant_protected_get(PaqueteLims, pk=pk)
    paquete.perfiles.remove(tenant_protected_get(PerfilLims, pk=perfil_pk))
    return JsonResponse({'ok': True})
