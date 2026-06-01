"""
APIs agregadas CCI / Levey-Jennings (Cloud Economy — agregación en BD, puntos acotados).
"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Avg, Count, FloatField, Max, Min
from django.db.models.aggregates import Aggregate
from django.db.models.functions import TruncDay, TruncHour
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from lims.models import Analito
from laboratorio.cci_models import LoteMaterialControl, MedicionControlInterno

logger = logging.getLogger('laboratorio.cci_api')


def _empresa_cci(request):
    # FIX V8.2 HL7 TENANT (CCI): alinear con middleware + usuario
    return getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)


def _target_lote_respuesta(target: dict) -> dict:
    """Alias JSON para consumidores Westgard / Chart.js (sin romper claves actuales)."""
    if not target:
        return target
    out = dict(target)
    if out.get('media') is not None:
        out['mean'] = out['media']
    if out.get('sd') is not None:
        out['desviacion_std'] = out['sd']
    return out


class _StdDevSample(Aggregate):
    function = 'STDDEV_SAMP'
    name = 'stddev_sample'
    output_field = FloatField()


def _parse_positive_int(request, name: str, default: int | None = None) -> int | None:
    raw = request.GET.get(name)
    if raw is None or str(raw).strip() == '':
        return default
    try:
        v = int(raw)
        return v if v > 0 else default
    except (TypeError, ValueError):
        return default


def _base_qs(empresa_id: int, equipo_id: int, analito_id: int, lote_id: int | None, since):
    qs = MedicionControlInterno.objects.filter(
        empresa_id=empresa_id,
        equipo_id=equipo_id,
        analito_id=analito_id,
        fecha_medicion__gte=since,
    )
    if lote_id:
        qs = qs.filter(lote_material_id=lote_id)
    return qs


def _target_from_lote(empresa_id: int, analito_id: int, lote_id: int | None) -> dict:
    q = LoteMaterialControl.objects.filter(
        material__empresa_id=empresa_id,
        material__analito_id=analito_id,
        material__activo=True,
        activo=True,
    )
    if lote_id:
        q = q.filter(pk=lote_id)
    lot = q.select_related('material').order_by('-pk').first()
    if not lot:
        return {'media': None, 'sd': None, 'lote_id': None, 'numero_lote': None, 'nivel': ''}
    sd = float(lot.sd) if lot.sd and Decimal(str(lot.sd)) != 0 else None
    return {
        'media': float(lot.media),
        'sd': sd,
        'lote_id': lot.pk,
        'numero_lote': lot.numero_lote,
        'nivel': lot.nivel or '',
    }


def _float_or_none(x):
    if x is None:
        return None
    return float(x)


def _series_annotate_kwargs():
    d = {
        'n': Count('id'),
        'avg_valor': Avg('valor'),
        'min_valor': Min('valor'),
        'max_valor': Max('valor'),
    }
    if connection.vendor == 'postgresql':
        d['stddev_samp_valor'] = _StdDevSample('valor')
    return d


@login_required
@require_GET
def api_cci_lj_summary(request):
    """
    Resumen + puntos recientes (máx 200) para Chart.js.
    GET: equipo_id, analito_id, lote_id?, days? (90), max_points? (120)
    """
    empresa = _empresa_cci(request)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'sin_empresa'}, status=403)
    equipo_id = _parse_positive_int(request, 'equipo_id')
    analito_id = _parse_positive_int(request, 'analito_id')
    if not equipo_id or not analito_id:
        return JsonResponse(
            {'ok': False, 'error': 'equipo_id y analito_id son obligatorios'},
            status=400,
        )
    if not Analito.objects.filter(pk=analito_id, empresa_id=empresa.pk, activo=True).exists():
        return JsonResponse(
            {'ok': False, 'error': 'analito_id no pertenece a su empresa'},
            status=403,
        )
    lote_id = _parse_positive_int(request, 'lote_id')
    days = _parse_positive_int(request, 'days', 90) or 90
    days = min(days, 730)
    max_points = _parse_positive_int(request, 'max_points', 120) or 120
    max_points = min(max_points, 200)
    since = timezone.now() - timedelta(days=days)

    qs = _base_qs(empresa.pk, equipo_id, analito_id, lote_id, since)
    agg = qs.aggregate(
        n=Count('id'),
        avg_valor=Avg('valor'),
        min_valor=Min('valor'),
        max_valor=Max('valor'),
    )
    std_global = None
    if connection.vendor == 'postgresql':
        try:
            std_global = _float_or_none(qs.aggregate(s=_StdDevSample('valor')).get('s'))
        except Exception as exc:
            logger.debug('STDDEV_SAMP global: %s', exc)

    target = _target_from_lote(empresa.pk, analito_id, lote_id)
    target_out = _target_lote_respuesta(target)

    puntos_qs = (
        qs.order_by('-fecha_medicion').values(
            'fecha_medicion',
            'valor',
            'z_score',
            'reglas_disparadas',
            'westgard_estado',
        )[:max_points]
    )
    puntos = list(puntos_qs)
    puntos.reverse()

    alertas_base = MedicionControlInterno.objects.filter(
        empresa=empresa,
        equipo_id=equipo_id,
        analito_id=analito_id,
        fecha_medicion__gte=since,
    ).exclude(reglas_disparadas=[])
    if lote_id:
        alertas_base = alertas_base.filter(lote_material_id=lote_id)
    alertas_recientes = []
    for row in alertas_base.order_by('-fecha_medicion').values(
        'fecha_medicion', 'reglas_disparadas', 'westgard_estado', 'valor'
    )[:25]:
        v = row.get('valor')
        alertas_recientes.append(
            {
                'fecha_medicion': row['fecha_medicion'].isoformat() if row.get('fecha_medicion') else '',
                'reglas_disparadas': row.get('reglas_disparadas') or [],
                'westgard_estado': row.get('westgard_estado') or '',
                'valor': float(v) if v is not None else None,
            }
        )

    lotes_opts = list(
        LoteMaterialControl.objects.filter(
            material__empresa_id=empresa.pk,
            material__analito_id=analito_id,
            material__activo=True,
            activo=True,
        ).values('id', 'numero_lote', 'nivel')[:80]
    )

    puntos_payload = [
        {
            't': p['fecha_medicion'].isoformat(),
            'valor': _float_or_none(p['valor']),
            'z': _float_or_none(p['z_score']),
            'reglas': p['reglas_disparadas'] or [],
            'westgard_estado': p['westgard_estado'] or '',
        }
        for p in puntos
    ]
    avg_v = _float_or_none(agg['avg_valor'])
    return JsonResponse(
        {
            'ok': True,
            'filtros': {
                'equipo_id': equipo_id,
                'analito_id': analito_id,
                'lote_id': lote_id,
                'days': days,
            },
            'resumen': {
                'n': agg['n'] or 0,
                'avg_valor': avg_v,
                'min_valor': _float_or_none(agg['min_valor']),
                'max_valor': _float_or_none(agg['max_valor']),
                'stddev_samp_valor': std_global,
                # FIX CONTRATO UI: alias Westgard / documentación
                'media': avg_v,
                'desviacion_muestral': std_global,
            },
            'target_lote': target_out,
            'puntos': puntos_payload,
            # FIX CONTRATO UI: consumidores que esperan `labels` / `data` explícitos
            'labels': [x['t'] for x in puntos_payload],
            'data': [x['valor'] for x in puntos_payload],
            'alertas_recientes': alertas_recientes,
            'lotes_disponibles': lotes_opts,
        }
    )


@login_required
@require_GET
def api_cci_lj_series(request):
    """
    Serie agregada por día u hora (GROUP BY en BD).
    GET: equipo_id, analito_id, lote_id?, days?, bucket=day|hour
    """
    empresa = _empresa_cci(request)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'sin_empresa'}, status=403)
    equipo_id = _parse_positive_int(request, 'equipo_id')
    analito_id = _parse_positive_int(request, 'analito_id')
    if not equipo_id or not analito_id:
        return JsonResponse(
            {'ok': False, 'error': 'equipo_id y analito_id son obligatorios'},
            status=400,
        )
    if not Analito.objects.filter(pk=analito_id, empresa_id=empresa.pk, activo=True).exists():
        return JsonResponse(
            {'ok': False, 'error': 'analito_id no pertenece a su empresa'},
            status=403,
        )
    lote_id = _parse_positive_int(request, 'lote_id')
    days = _parse_positive_int(request, 'days', 90) or 90
    days = min(days, 730)
    since = timezone.now() - timedelta(days=days)
    bucket = (request.GET.get('bucket') or 'day').strip().lower()
    trunc = TruncHour('fecha_medicion') if bucket == 'hour' else TruncDay('fecha_medicion')

    qs = _base_qs(empresa.pk, equipo_id, analito_id, lote_id, since)
    series = (
        qs.annotate(bucket=trunc)
        .values('bucket')
        .annotate(**_series_annotate_kwargs())
        .order_by('bucket')
    )

    rows = []
    for row in series:
        item = {
            'bucket': row['bucket'].isoformat(),
            'n': row['n'],
            'avg_valor': _float_or_none(row['avg_valor']),
            'min_valor': _float_or_none(row['min_valor']),
            'max_valor': _float_or_none(row['max_valor']),
        }
        if 'stddev_samp_valor' in row:
            item['stddev_samp_valor'] = _float_or_none(row['stddev_samp_valor'])
        else:
            item['stddev_samp_valor'] = None
        rows.append(item)

    target = _target_from_lote(empresa.pk, analito_id, lote_id)
    return JsonResponse(
        {
            'ok': True,
            'bucket': bucket,
            'target_lote': _target_lote_respuesta(target),
            'series': rows,
        }
    )
