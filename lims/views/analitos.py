"""Ventana A — Analitos: lista, detalle, edición y rangos de referencia."""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.tenant import tenant_protected_get
from core.utils.empresa_request import get_empresa_usuario
from lims.models import Analito, ValorReferenciaAnalito
from lims.views.tenant_lims import empresa_lims
import logging


def _check_perm(user):
    # PATRÓN CORRECTO: Validar empresa siempre, pero permitir superuser/staff CON empresa válida
    empresa = get_empresa_usuario(user)
    if not empresa:
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

    # FIX V8.2 LIMS TENANT: filtro explícito (superusuario sin ORM tenant)
    qs = Analito.objects.filter(empresa=empresa).select_related('precio')

    q = (request.GET.get('q') or '').strip()
    departamento = (request.GET.get('dep') or '').strip()
    venta = request.GET.get('venta', '')

    if q:
        qs = qs.filter(
            Q(codigo__icontains=q) | Q(abreviatura__icontains=q) |
            Q(nombre__icontains=q)
        )
    if departamento:
        qs = qs.filter(departamento=departamento)
    if venta == '1':
        qs = qs.filter(es_vendible_individualmente=True)
    elif venta == '0':
        qs = qs.filter(es_vendible_individualmente=False)

    departamentos = (
        Analito.objects.filter(empresa=empresa)
        .values_list('departamento', flat=True)
        .distinct()
        .order_by('departamento')
    )

    return render(request, 'lims/analitos_lista.html', {
        'analitos': qs.order_by('departamento', 'nombre'),
        'total': qs.count(),
        'q': q,
        'dep_sel': departamento,
        'venta_sel': venta,
        'departamentos': departamentos,
    })


@login_required
def detalle(request, pk):
    if not _check_perm(request.user):
        return redirect('home')
    analito = tenant_protected_get(Analito, pk=pk)
    rangos = analito.rangos.all().order_by('unidad_edad', 'sexo', 'edad_minima')
    return render(request, 'lims/analito_detalle.html', {
        'analito': analito,
        'rangos': rangos,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def editar(request, pk):
    if not _check_perm(request.user):
        return redirect('home')
    analito = tenant_protected_get(Analito, pk=pk)

    if request.method == 'POST':
        analito.nombre           = request.POST.get('nombre', analito.nombre).strip()
        analito.abreviatura      = request.POST.get('abreviatura', analito.abreviatura).strip()
        analito.departamento     = request.POST.get('departamento', analito.departamento).strip()
        analito.tipo_muestra     = request.POST.get('tipo_muestra', '').strip()
        analito.metodologia      = request.POST.get('metodologia', '').strip()
        analito.unidades         = request.POST.get('unidades', '').strip()
        analito.tipo_resultado   = request.POST.get('tipo_resultado', analito.tipo_resultado)
        analito.decimales        = int(request.POST.get('decimales', analito.decimales) or 2)
        analito.formula          = request.POST.get('formula', '').strip()
        analito.es_calculado     = bool(analito.formula)
        analito.es_vendible_individualmente = request.POST.get('es_vendible_individualmente') == '1'
        analito.indicaciones     = request.POST.get('indicaciones', '').strip()
        analito.notas            = request.POST.get('notas', '').strip()
        analito.activo           = request.POST.get('activo') == '1'
        analito.save()
        return redirect('lims_analito_detalle', pk=pk)

    return render(request, 'lims/analito_editar.html', {
        'analito': analito,
        'tipo_resultado_choices': Analito.TIPO_RESULTADO,
    })


# ── API: rangos de referencia (AJAX) ─────────────────────────────────────────

@login_required
def api_rangos(request, pk):
    """GET → lista JSON de rangos; POST → crear rango; DELETE → eliminar."""
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)

    analito = tenant_protected_get(Analito, pk=pk)

    if request.method == 'GET':
        datos = list(analito.rangos.values(
            'id', 'sexo', 'unidad_edad', 'edad_minima', 'edad_maxima',
            'ref_minimo', 'ref_maximo', 'texto_referencia',
        ))
        return JsonResponse({'rangos': datos})

    if request.method == 'POST':
        import json
        try:
            body = json.loads(request.body)
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en api_rangos (analitos.py)")
            body = request.POST.dict()

        def _dec(v):
            try:
                return Decimal(str(v))
            except (InvalidOperation, TypeError):
                return None

        rango = ValorReferenciaAnalito.objects.create(
            analito=analito,
            sexo=body.get('sexo', 'I'),
            unidad_edad=body.get('unidad_edad', 'ANOS'),
            edad_minima=int(body.get('edad_minima', 0)),
            edad_maxima=int(body.get('edad_maxima', 150)),
            ref_minimo=_dec(body.get('ref_minimo')),
            ref_maximo=_dec(body.get('ref_maximo')),
            texto_referencia=body.get('texto_referencia', ''),
        )
        return JsonResponse({'ok': True, 'id': rango.id})

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def api_rango_eliminar(request, rango_pk):
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    emp = empresa_lims(request)
    if not emp:
        return JsonResponse({'error': 'Sin empresa activa'}, status=403)
    rango = get_object_or_404(
        ValorReferenciaAnalito,
        pk=rango_pk,
        analito__empresa=emp,
    )
    rango.delete()
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['GET', 'POST'])
def api_rango_item(request, pk, rango_pk):
    """GET → JSON de un rango; POST → actualizar campos (mismo esquema que creación)."""
    if not _check_perm(request.user):
        return JsonResponse({'error': 'Sin permisos'}, status=403)

    analito = tenant_protected_get(Analito, pk=pk)
    rango = get_object_or_404(ValorReferenciaAnalito, pk=rango_pk, analito=analito)

    if request.method == 'GET':
        return JsonResponse({
            'id': rango.id,
            'sexo': rango.sexo,
            'unidad_edad': rango.unidad_edad,
            'edad_minima': rango.edad_minima,
            'edad_maxima': rango.edad_maxima,
            'ref_minimo': str(rango.ref_minimo) if rango.ref_minimo is not None else '',
            'ref_maximo': str(rango.ref_maximo) if rango.ref_maximo is not None else '',
            'texto_referencia': rango.texto_referencia or '',
        })

    import json

    try:
        body = json.loads(request.body)
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en api_rango_item (analitos.py)")
        body = request.POST.dict()

    def _dec(v):
        try:
            return Decimal(str(v))
        except (InvalidOperation, TypeError):
            return None

    if body.get('sexo') in ('I', 'M', 'F'):
        rango.sexo = body['sexo']
    rango.unidad_edad = body.get('unidad_edad', rango.unidad_edad) or rango.unidad_edad
    rango.edad_minima = int(body.get('edad_minima', rango.edad_minima))
    rango.edad_maxima = int(body.get('edad_maxima', rango.edad_maxima))
    if 'ref_minimo' in body:
        rm = body.get('ref_minimo')
        rango.ref_minimo = _dec(rm) if rm not in (None, '') else None
    if 'ref_maximo' in body:
        rx = body.get('ref_maximo')
        rango.ref_maximo = _dec(rx) if rx not in (None, '') else None
    rango.texto_referencia = body.get('texto_referencia', rango.texto_referencia) or ''
    rango.save()
    return JsonResponse({'ok': True, 'id': rango.id})