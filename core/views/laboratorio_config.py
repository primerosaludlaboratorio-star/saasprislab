"""
Configuración de catálogo LIMS v7.5.

La fuente de verdad es la app `lims` (Django Admin y modelos Analito / PerfilLims / PaqueteLims).
Estas vistas redirigen al panel admin o exponen APIs mínimas compatibles con rutas legacy.
"""
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from core.decorators import role_required
from lims.models import Analito, PerfilLims, ValorReferenciaAnalito
from lims.views.tenant_lims import empresa_lims

logger = logging.getLogger(__name__)

ADMIN_ANALITOS = '/admin/lims/analito/'
ADMIN_PERFILES = '/admin/lims/perfillims/'
ADMIN_PAQUETES = '/admin/lims/paquetelims/'


def _can_manage_lims_catalog(user) -> bool:
    """Permiso de edición LIMS: empresa obligatoria, staff solo dentro de tenant."""
    if not getattr(user, 'empresa', None):
        return False
    if user.is_superuser or user.is_staff:
        return True
    rol = (getattr(user, 'rol', '') or '').upper()
    return rol in ('DIRECTOR_QC', 'ADMIN', 'ADMINISTRADOR', 'LABORATORIO', 'LIMS')


@login_required
@role_required('DIRECTOR_QC', 'ADMIN')
def lista_pruebas(request):
    messages.info(
        request,
        'Catálogo v7.5: gestione analitos, perfiles y paquetes en Administración LIMS.',
    )
    return redirect(ADMIN_ANALITOS)


@login_required
@role_required('DIRECTOR_QC', 'ADMIN')
def configurar_prueba(request, estudio_id=None):
    messages.info(request, 'Edición de ítems LIMS desde el panel administrativo.')
    return redirect(ADMIN_PERFILES if estudio_id else ADMIN_ANALITOS)


@login_required
@role_required('DIRECTOR_QC', 'ADMIN')
def configurar_rangos(request, parametro_id):
    a = get_object_or_404(Analito, pk=parametro_id)
    return redirect(f'/admin/lims/analito/{a.pk}/change/')


@login_required
@role_required('DIRECTOR_QC', 'ADMIN')
def eliminar_prueba(request, estudio_id):
    if request.method == 'POST':
        messages.warning(request, 'Use el admin LIMS para desactivar o eliminar ítems.')
    return redirect(ADMIN_ANALITOS)


@login_required
@role_required('DIRECTOR_QC', 'ADMIN')
def duplicar_prueba(request, estudio_id):
    messages.info(request, 'Duplique registros desde el admin LIMS (analito/perfil/paquete).')
    return redirect(ADMIN_ANALITOS)


@login_required
def api_parametros_estudio(request, estudio_id):
    """Legacy: `estudio_id` se interpreta como PerfilLims.pk o, si no existe, Analito.pk."""
    empresa = empresa_lims(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)

    perfil = PerfilLims.objects.filter(pk=estudio_id, empresa=empresa, activo=True).first()
    if perfil:
        analitos = perfil.analitos.filter(activo=True).order_by('nombre')
        data = {
            'estudio': {'id': perfil.id, 'codigo': '', 'nombre': perfil.nombre},
            'parametros': [
                {
                    'id': a.id,
                    'nombre': a.nombre,
                    'unidad': a.unidades or '',
                    'tipo_dato': a.tipo_resultado,
                    'orden': 0,
                    'rangos_count': a.rangos.count(),
                }
                for a in analitos
            ],
        }
        return JsonResponse(data)

    analito = Analito.objects.filter(pk=estudio_id, empresa=empresa).first()
    if not analito:
        return JsonResponse({'error': 'No encontrado'}, status=404)

    return JsonResponse({
        'estudio': {'id': analito.id, 'codigo': analito.codigo, 'nombre': analito.nombre},
        'parametros': [
            {
                'id': analito.id,
                'nombre': analito.nombre,
                'unidad': analito.unidades or '',
                'tipo_dato': analito.tipo_resultado,
                'orden': 0,
                'rangos_count': analito.rangos.count(),
            }
        ],
    })


@login_required
@role_required('DIRECTOR_QC', 'ADMIN')
def lista_parametros(request):
    messages.info(request, 'Listado de analitos (parámetros) en Admin LIMS.')
    return redirect(ADMIN_ANALITOS)


@login_required
@role_required('DIRECTOR_QC', 'ADMIN')
def editar_parametro(request, parametro_id=None, estudio_id=None):
    if parametro_id:
        return redirect(f'/admin/lims/analito/{parametro_id}/change/')
    messages.info(request, 'Cree un nuevo analito desde Administración LIMS.')
    return redirect('/admin/lims/analito/add/')


@login_required
def api_rangos_parametro(request, parametro_id):
    empresa = empresa_lims(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)

    analito = get_object_or_404(Analito, pk=parametro_id, empresa=empresa)

    if request.method == 'GET':
        rangos = analito.rangos.all().order_by('unidad_edad', 'edad_minima', 'sexo')
        data = [_rango_lims_to_dict(r) for r in rangos]
        return JsonResponse({'rangos': data})

    if request.method == 'POST':
        if not _can_manage_lims_catalog(request.user):
            return JsonResponse({'error': 'Permiso denegado'}, status=403)
        try:
            body = json.loads(request.body)
            with transaction.atomic():
                ValorReferenciaAnalito.objects.create(
                    analito=analito,
                    sexo=body.get('sexo', 'I')[:1],
                    unidad_edad=body.get('unidad_edad', 'ANOS')[:5],
                    edad_minima=int(body.get('edad_minima') or 0),
                    edad_maxima=int(body.get('edad_maxima') or 120),
                    ref_minimo=body.get('valor_minimo') or None,
                    ref_maximo=body.get('valor_maximo') or None,
                    texto_referencia=body.get('texto_referencia') or '',
                )
            return JsonResponse({'ok': True}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def api_rango_detalle(request, parametro_id, rango_id):
    empresa = empresa_lims(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)

    analito = get_object_or_404(Analito, pk=parametro_id, empresa=empresa)
    rango = get_object_or_404(ValorReferenciaAnalito, pk=rango_id, analito=analito)

    if request.method == 'DELETE':
        if not _can_manage_lims_catalog(request.user):
            return JsonResponse({'error': 'Permiso denegado'}, status=403)
        rango.delete()
        return JsonResponse({'ok': True})

    return JsonResponse({'error': 'Use admin LIMS para ediciones complejas'}, status=405)


@login_required
def api_soft_delete_parametro(request, parametro_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    empresa = empresa_lims(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)

    if not _can_manage_lims_catalog(request.user):
        return JsonResponse({'error': 'Permiso denegado'}, status=403)

    analito = get_object_or_404(Analito, pk=parametro_id, empresa=empresa)
    analito.activo = False
    analito.save(update_fields=['activo', 'fecha_actualiz'])
    return JsonResponse({'ok': True, 'mensaje': f'Analito "{analito.nombre}" desactivado.'})


@login_required
def api_buscar_parametros(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'parametros': []})

    empresa = empresa_lims(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada', 'parametros': []}, status=403)

    qs = (
        Analito.objects.filter(empresa=empresa, activo=True)
        .filter(
            Q(nombre__icontains=q) | Q(abreviatura__icontains=q) | Q(codigo__icontains=q)
        )[:25]
    )
    data = [
        {
            'id': p.id,
            'nombre': p.nombre,
            'abreviatura': p.abreviatura or '',
            'unidad': p.unidades or '',
            'tipo_dato': p.tipo_resultado,
            'estudio_nombre': p.departamento,
            'estudio_id': p.id,
        }
        for p in qs
    ]
    return JsonResponse({'parametros': data})


def _rango_lims_to_dict(r: ValorReferenciaAnalito) -> dict:
    return {
        'id': r.id,
        'sexo': r.sexo,
        'unidad_edad': r.unidad_edad,
        'edad_minima': r.edad_minima,
        'edad_maxima': r.edad_maxima,
        'valor_minimo': str(r.ref_minimo) if r.ref_minimo is not None else None,
        'valor_maximo': str(r.ref_maximo) if r.ref_maximo is not None else None,
        'texto_referencia': r.texto_referencia or '',
        'activo': True,
        'vigente_desde': timezone.now().isoformat(),
    }
