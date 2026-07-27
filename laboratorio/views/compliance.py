"""API operativa para CAPA y EQA, siempre acotada al tenant del usuario."""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from django.contrib.auth import get_user_model
from laboratorio.models import NoConformidad, RondaEQA, ResultadoEQA

_ROLES_COMPLIANCE = {'ADMIN', 'DIRECTOR', 'GERENTE', 'LABORATORIO'}


def _empresa_y_permiso(request):
    empresa = getattr(request.user, 'empresa', None)
    permitido = request.user.is_superuser or getattr(request.user, 'rol', '') in _ROLES_COMPLIANCE
    return empresa, permitido


def _json(request):
    try:
        data = json.loads(request.body or '{}')
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _responsable_id(data, empresa):
    raw_id = data.get('responsable_id')
    if not raw_id:
        return None
    User = get_user_model()
    return User.objects.filter(pk=raw_id, empresa=empresa).values_list('pk', flat=True).first()


@login_required
@require_http_methods(['GET', 'POST'])
def no_conformidades_api(request):
    empresa, permitido = _empresa_y_permiso(request)
    if not empresa or not permitido:
        return JsonResponse({'error': 'Sin permiso de compliance o empresa.'}, status=403)
    if request.method == 'GET':
        items = NoConformidad.objects.filter(empresa=empresa).values(
            'folio', 'titulo', 'origen', 'severidad', 'estado', 'responsable_id', 'creado_en', 'fecha_compromiso'
        )
        return JsonResponse({'items': list(items)})

    data = _json(request)
    required = ('titulo', 'descripcion', 'origen')
    if not data or any(not str(data.get(field, '')).strip() for field in required):
        return JsonResponse({'error': 'titulo, descripcion y origen son obligatorios.'}, status=400)
    item = NoConformidad(
        empresa=empresa,
        titulo=str(data['titulo']).strip(),
        descripcion=str(data['descripcion']).strip(),
        origen=str(data['origen']).strip(),
        severidad=str(data.get('severidad', 'MENOR')).strip(),
        detectada_por=request.user,
        responsable_id=_responsable_id(data, empresa),
    )
    try:
        item.full_clean()
        item.save()
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    return JsonResponse({'folio': str(item.folio), 'estado': item.estado}, status=201)


@login_required
@require_http_methods(['POST'])
def no_conformidad_transicion_api(request, folio):
    empresa, permitido = _empresa_y_permiso(request)
    if not empresa or not permitido:
        return JsonResponse({'error': 'Sin permiso de compliance o empresa.'}, status=403)
    item = get_object_or_404(NoConformidad, folio=folio, empresa=empresa)
    data = _json(request)
    if not data or not data.get('estado'):
        return JsonResponse({'error': 'estado es obligatorio.'}, status=400)
    try:
        item.causa_raiz = data.get('causa_raiz', item.causa_raiz)
        item.correccion_inmediata = data.get('correccion_inmediata', item.correccion_inmediata)
        item.accion_correctiva = data.get('accion_correctiva', item.accion_correctiva)
        item.evidencia_verificacion = data.get('evidencia_verificacion', item.evidencia_verificacion)
        item.transition(data['estado'], request.user, data.get('notas', ''))
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    return JsonResponse({'folio': str(item.folio), 'estado': item.estado})


@login_required
@require_http_methods(['GET', 'POST'])
def rondas_eqa_api(request):
    empresa, permitido = _empresa_y_permiso(request)
    if not empresa or not permitido:
        return JsonResponse({'error': 'Sin permiso de compliance o empresa.'}, status=403)
    if request.method == 'GET':
        items = RondaEQA.objects.filter(empresa=empresa).values(
            'id', 'proveedor', 'programa', 'codigo_ronda', 'estado', 'fecha_recepcion', 'fecha_limite'
        )
        return JsonResponse({'items': list(items)})
    data = _json(request)
    required = ('proveedor', 'programa', 'codigo_ronda')
    if not data or any(not str(data.get(field, '')).strip() for field in required):
        return JsonResponse({'error': 'proveedor, programa y codigo_ronda son obligatorios.'}, status=400)
    ronda = RondaEQA(
        empresa=empresa,
        proveedor=str(data['proveedor']).strip(),
        programa=str(data['programa']).strip(),
        codigo_ronda=str(data['codigo_ronda']).strip(),
        responsable=request.user,
    )
    try:
        ronda.full_clean()
        ronda.save()
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    return JsonResponse({'id': ronda.id, 'estado': ronda.estado}, status=201)


@login_required
@require_http_methods(['POST'])
def evaluar_resultado_eqa_api(request, resultado_id):
    empresa, permitido = _empresa_y_permiso(request)
    if not empresa or not permitido:
        return JsonResponse({'error': 'Sin permiso de compliance o empresa.'}, status=403)
    resultado = get_object_or_404(ResultadoEQA, pk=resultado_id, ronda__empresa=empresa)
    try:
        evaluacion = resultado.evaluar()
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    return JsonResponse({'id': resultado.id, 'z_score': str(resultado.z_score), 'evaluacion': evaluacion})
