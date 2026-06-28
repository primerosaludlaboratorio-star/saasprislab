"""
Historial de resultados — LIMS v7.5 (core.OrdenDeServicio + ResultadoParametro + lims.Analito).

El query param `estudio` y el path `estudio_id` se interpretan como ID de lims.Analito (compatibilidad de rutas).
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Q
import json

from core.models import Paciente, OrdenDeServicio, ResultadoParametro
from lims.models import Analito, ValorReferenciaAnalito


def _ref_min_max_analito(analito, paciente):
    if not analito or not paciente:
        return None, None
    sexo = getattr(paciente, 'sexo', 'I') or 'I'
    qs = (
        ValorReferenciaAnalito.objects.filter(analito=analito)
        .filter(Q(sexo=sexo) | Q(sexo='I'))
        .order_by('edad_minima')
    )
    r = qs.first()
    if r and r.ref_minimo is not None and r.ref_maximo is not None:
        return float(r.ref_minimo), float(r.ref_maximo)
    return None, None


@login_required
def historial_resultados(request, paciente_id=None):
    empresa = getattr(request.user, 'empresa', None)
    paciente = None
    if paciente_id:
        paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

    analitos = Analito.objects.filter(activo=True).order_by('nombre')

    estudio_id = request.GET.get('estudio', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')

    if not paciente:
        pacientes = Paciente.objects.filter(empresa=empresa).order_by('-id')[:50]
        return render(request, 'core/historial_resultados/lista_pacientes.html', {
            'empresa': empresa,
            'pacientes': pacientes,
        })

    ordenes = OrdenDeServicio.objects.filter(
        paciente=paciente,
        empresa=empresa,
        estado__in=('RESULTADOS_LISTOS', 'ENTREGADO'),
    ).order_by('-fecha_creacion')

    if fecha_desde:
        ordenes = ordenes.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        ordenes = ordenes.filter(fecha_creacion__date__lte=fecha_hasta)

    resultados_grafica = []
    if estudio_id and str(estudio_id).isdigit():
        analito = get_object_or_404(Analito, id=int(estudio_id), activo=True)
        rps = ResultadoParametro.objects.filter(
            orden__paciente=paciente,
            orden__empresa=empresa,
            analito=analito,
            orden__estado__in=('RESULTADOS_LISTOS', 'ENTREGADO'),
        ).select_related('orden').order_by('orden__fecha_creacion')
        if fecha_desde:
            rps = rps.filter(orden__fecha_creacion__date__gte=fecha_desde)
        if fecha_hasta:
            rps = rps.filter(orden__fecha_creacion__date__lte=fecha_hasta)
        for rp in rps:
            try:
                valor_num = float(str(rp.valor).replace(',', '.'))
                resultados_grafica.append({
                    'fecha': rp.orden.fecha_creacion.strftime('%Y-%m-%d'),
                    'valor': valor_num,
                    'orden_id': rp.orden.id,
                    'es_anormal': bool(rp.fuera_rango or rp.es_critico),
                })
            except (ValueError, TypeError):
                pass

    todos_resultados = (
        ResultadoParametro.objects.filter(
            orden__paciente=paciente,
            orden__empresa=empresa,
            orden__estado__in=('RESULTADOS_LISTOS', 'ENTREGADO'),
        )
        .select_related('orden', 'analito')
        .annotate(_forense_num_ediciones=Count('historial_cambios', distinct=True))
        .order_by('-orden__fecha_creacion', 'analito__nombre')
    )

    if fecha_desde:
        todos_resultados = todos_resultados.filter(orden__fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        todos_resultados = todos_resultados.filter(orden__fecha_creacion__date__lte=fecha_hasta)
    if estudio_id and str(estudio_id).isdigit():
        todos_resultados = todos_resultados.filter(analito_id=int(estudio_id))

    return render(request, 'core/historial_resultados/historial.html', {
        'empresa': empresa,
        'paciente': paciente,
        'ordenes': ordenes[:20],
        'estudios': analitos,
        'resultados_grafica': json.dumps(resultados_grafica),
        'resultados_tabla': todos_resultados[:100],
        'estudio_seleccionado': estudio_id,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })


@login_required
def api_resultados_grafica(request, paciente_id, estudio_id):
    """estudio_id = lims.Analito.pk (compatibilidad de nombre de ruta)."""
    empresa = getattr(request.user, 'empresa', None)
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)
    analito = get_object_or_404(Analito, id=estudio_id, activo=True)

    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')

    resultados = ResultadoParametro.objects.filter(
        orden__paciente=paciente,
        orden__empresa=empresa,
        analito=analito,
        orden__estado__in=('RESULTADOS_LISTOS', 'ENTREGADO'),
    ).select_related('orden').order_by('orden__fecha_creacion')

    if fecha_desde:
        resultados = resultados.filter(orden__fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        resultados = resultados.filter(orden__fecha_creacion__date__lte=fecha_hasta)

    rmin, rmax = _ref_min_max_analito(analito, paciente)
    datos = {
        'labels': [],
        'valores': [],
        'es_anormal': [],
        'rango_min': rmin,
        'rango_max': rmax,
    }

    for resultado in resultados:
        try:
            valor_num = float(str(resultado.valor).replace(',', '.'))
            datos['labels'].append(resultado.orden.fecha_creacion.strftime('%Y-%m-%d'))
            datos['valores'].append(valor_num)
            datos['es_anormal'].append(bool(resultado.fuera_rango or resultado.es_critico))
        except (ValueError, TypeError):
            continue

    return JsonResponse(datos)


@login_required
def comparar_resultados(request, paciente_id):
    empresa = getattr(request.user, 'empresa', None)
    paciente = get_object_or_404(Paciente, id=paciente_id, empresa=empresa)

    estudios_ids = request.GET.getlist('estudios', [])
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')

    if not estudios_ids:
        return JsonResponse({'error': 'Seleccione al menos un estudio'}, status=400)

    datos_comparacion = {}

    for aid in estudios_ids:
        analito = get_object_or_404(Analito, id=int(aid), activo=True)
        resultados = ResultadoParametro.objects.filter(
            orden__paciente=paciente,
            orden__empresa=empresa,
            analito=analito,
            orden__estado__in=('RESULTADOS_LISTOS', 'ENTREGADO'),
        ).select_related('orden').order_by('orden__fecha_creacion')

        if fecha_desde:
            resultados = resultados.filter(orden__fecha_creacion__date__gte=fecha_desde)
        if fecha_hasta:
            resultados = resultados.filter(orden__fecha_creacion__date__lte=fecha_hasta)

        valores = []
        fechas = []
        for resultado in resultados:
            try:
                valor_num = float(str(resultado.valor).replace(',', '.'))
                valores.append(valor_num)
                fechas.append(resultado.orden.fecha_creacion.strftime('%Y-%m-%d'))
            except (ValueError, TypeError):
                continue

        rmin, rmax = _ref_min_max_analito(analito, paciente)
        datos_comparacion[analito.nombre] = {
            'valores': valores,
            'fechas': fechas,
            'rango_min': rmin,
            'rango_max': rmax,
        }

    return JsonResponse(datos_comparacion)
