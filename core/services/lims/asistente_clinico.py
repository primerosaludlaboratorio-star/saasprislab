from __future__ import annotations

import logging
from collections import Counter
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.utils import timezone

from core.models import IncidenciaOperativa, ResultadoParametro
from core.services.feature_flags import flag_activo
from core.services.validador_ia import generar_sugerencias_proceso

logger = logging.getLogger('core.lims.asistente_clinico')

UMBRAL_DELTA_PORCENTAJE = Decimal('30')


def _parse_decimal(valor: Any) -> Decimal | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        return Decimal(texto.replace(',', '.'))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _normalizar_alerta(alerta: dict, *, orden, detalle, usuario) -> dict:
    analito = getattr(detalle, 'analito', None)
    alerta = dict(alerta or {})
    alerta.setdefault('fuente', 'VALIDADOR_IA')
    alerta.setdefault('orden_id', getattr(orden, 'id', None))
    alerta.setdefault('detalle_id', getattr(detalle, 'id', None))
    alerta.setdefault('analito_id', getattr(detalle, 'analito_id', None))
    alerta.setdefault('analito', getattr(analito, 'nombre', '') or '')
    alerta.setdefault('codigo_analito', getattr(analito, 'codigo', '') or '')
    alerta.setdefault('usuario', getattr(usuario, 'username', '') or '')
    return alerta


def _delta_alerta(orden, resultado: ResultadoParametro) -> dict | None:
    valor_actual = _parse_decimal(resultado.valor)
    if valor_actual is None:
        return None

    analito_id = getattr(resultado, 'analito_id', None)
    if not analito_id:
        return None

    anterior = (
        ResultadoParametro.objects.filter(
            orden__paciente=orden.paciente,
            analito_id=analito_id,
        )
        .exclude(orden_id=orden.id)
        .exclude(valor__isnull=True)
        .exclude(valor__exact='')
        .select_related('orden', 'analito')
        .order_by('-orden__fecha_creacion', '-id')
        .first()
    )
    if not anterior:
        return None

    valor_anterior = _parse_decimal(anterior.valor)
    if valor_anterior in (None, Decimal('0')):
        return None

    diferencia = abs(valor_actual - valor_anterior)
    porcentaje = (diferencia / abs(valor_anterior)) * 100
    if porcentaje < UMBRAL_DELTA_PORCENTAJE:
        return None

    analito = getattr(resultado, 'analito', None)
    return {
        'tipo': 'DELTA_CHECK',
        'severidad': 'ALTA',
        'parametro': getattr(analito, 'nombre', '') or f'Analito #{analito_id}',
        'valor': str(resultado.valor),
        'mensaje': (
            f'Variación delta superior al umbral en {getattr(analito, "nombre", "el analito")}: '
            f'{valor_anterior} → {valor_actual} ({porcentaje.quantize(Decimal("0.1"))}%).'
        ),
        'comparacion': {
            'valor_anterior': str(valor_anterior),
            'valor_actual': str(valor_actual),
            'porcentaje': float(porcentaje),
        },
        'fuente': 'DELTA_CHECK',
        'orden_anterior_id': getattr(anterior, 'orden_id', None),
        'resultado_anterior_id': getattr(anterior, 'id', None),
    }


def _persistir_incidencia(orden, empresa, usuario, alertas: list[dict], modo: str, request=None):
    if not alertas or not usuario:
        return None

    recientes = IncidenciaOperativa.objects.filter(
        empresa=empresa,
        tipo_incidencia='ALERTA_CLINICA_ISO',
        datos_contexto__orden_id=getattr(orden, 'id', None),
        fecha_hora__gte=timezone.now() - timedelta(hours=24),
    )
    if recientes.exists():
        return recientes.first()

    criticas = [a for a in alertas if a.get('severidad') == 'CRITICA']
    altas = [a for a in alertas if a.get('severidad') == 'ALTA']
    resumen = (
        f'Orden {getattr(orden, "folio_orden", orden.id)} con {len(criticas)} alertas críticas '
        f'y {len(altas)} alertas altas bajo modo ISO {modo}.'
    )
    contexto = {
        'orden_id': getattr(orden, 'id', None),
        'folio': getattr(orden, 'folio_orden', ''),
        'modo_iso': modo,
        'alertas': alertas[:25],
        'alertas_criticas': len(criticas),
        'alertas_altas': len(altas),
        'total_alertas': len(alertas),
        'request_path': getattr(request, 'path', '') if request else '',
    }
    return IncidenciaOperativa.objects.create(
        empresa=empresa,
        usuario_responsable=usuario,
        tipo_incidencia='ALERTA_CLINICA_ISO',
        justificacion=resumen,
        estado_revision='PENDIENTE',
        datos_contexto=contexto,
    )


def evaluar_asistencia_clinica_orden(
    orden,
    empresa,
    *,
    usuario=None,
    request=None,
    accion='borrador',
) -> dict:
    """
    Analiza la orden contra validaciones clínicas y devuelve un resumen accionable.

    Flujo:
      - El switch principal es Empresa.iso15189_enabled.
      - OPTIONAL: solo informa.
      - GUIDED: informa y sugiere, sin bloquear.
      - STRICT: bloquea la liberación si hay alertas críticas.
    """
    modo = (getattr(empresa, 'iso15189_mode', '') or 'OPTIONAL').upper().strip()
    habilitado = bool(getattr(empresa, 'iso15189_enabled', False))

    resultado = {
        'habilitado': habilitado,
        'modo': modo,
        'activo': False,
        'requiere_revision': False,
        'debe_bloquear': False,
        'alertas': [],
        'recomendaciones': [],
        'resumen': {
            'criticas': 0,
            'altas': 0,
            'medias': 0,
            'bajas': 0,
        },
        'mensaje': '',
    }

    if not habilitado or not empresa:
        resultado['mensaje'] = 'El módulo ISO 15189 asistido está deshabilitado para este laboratorio.'
        return resultado

    if not flag_activo('ISO15189_CRITICOS_ACTIVO', empresa):
        resultado['mensaje'] = 'Las alertas críticas de ISO 15189 están apagadas por configuración.'
        return resultado

    alertas: list[dict] = []
    detalles = list(
        orden.detalles.select_related('analito', 'perfil_lims', 'paquete_lims')
    )
    for detalle in detalles:
        analito_id = getattr(detalle, 'analito_id', None)
        if not analito_id:
            continue

        from core.services.validador_ia import validar_resultado_ia

        alertas_detalle = validar_resultado_ia(detalle, analito_id=analito_id) or []
        for alerta in alertas_detalle:
            alertas.append(_normalizar_alerta(alerta, orden=orden, detalle=detalle, usuario=usuario))

        if flag_activo('DELTA_CHECK_ACTIVO', empresa):
            rp = (
                ResultadoParametro.objects.filter(orden=orden, analito_id=analito_id)
                .select_related('analito')
                .order_by('-fecha_captura', '-id')
                .first()
            )
            if rp:
                delta = _delta_alerta(orden, rp)
                if delta:
                    delta.setdefault('detalle_id', getattr(detalle, 'id', None))
                    delta.setdefault('analito_id', analito_id)
                    alertas.append(delta)

    if flag_activo('QC_WESTGARD_ACTIVO', empresa):
        try:
            from laboratorio.services.westgard import evaluar_westgard

            controles = []
            for rp in ResultadoParametro.objects.filter(orden=orden).select_related('analito'):
                valor_num = _parse_decimal(rp.valor)
                if valor_num is not None:
                    controles.append(float(valor_num))

            if len(controles) >= 3:
                media = sum(controles) / len(controles)
                sd = max((max(controles) - min(controles)) / 6, 0.01)
                westgard = evaluar_westgard(controles, media, sd)
                if westgard.estado in ('WARNING', 'RECHAZO'):
                    alerta_w = {
                        'tipo': 'WESTGARD',
                        'severidad': 'CRITICA' if westgard.estado == 'RECHAZO' else 'ALTA',
                        'parametro': 'Control de calidad',
                        'valor': '',
                        'mensaje': (
                            'Westgard detectó '
                            f"{westgard.estado.lower()} ({', '.join(westgard.reglas_violadas)})"
                        ),
                        'fuente': 'WESTGARD',
                        'reglas': westgard.reglas_violadas,
                    }
                    alertas.append(alerta_w)
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en evaluar_asistencia_clinica_orden")

    if modo in ('GUIDED', 'STRICT'):
        try:
            sugerencias = generar_sugerencias_proceso(empresa) or []
            resultado['recomendaciones'] = sugerencias[:5]
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en recomendaciones de proceso")

    resumen = Counter(a.get('severidad', 'BAJA') for a in alertas)
    resultado['alertas'] = alertas
    resultado['resumen'] = {
        'criticas': int(resumen.get('CRITICA', 0)),
        'altas': int(resumen.get('ALTA', 0)),
        'medias': int(resumen.get('MEDIA', 0)),
        'bajas': int(resumen.get('BAJA', 0)),
    }
    resultado['requiere_revision'] = bool(alertas)
    resultado['activo'] = True
    resultado['debe_bloquear'] = modo == 'STRICT' and resultado['resumen']['criticas'] > 0

    if resultado['debe_bloquear']:
        criticas = resultado['resumen']['criticas']
        resultado['mensaje'] = (
            f'Liberación bloqueada por ISO 15189 STRICT: {criticas} alerta(s) crítica(s) '
            'requieren corrección antes de publicar resultados.'
        )
    elif resultado['requiere_revision']:
        resultado['mensaje'] = (
            f'El módulo asistido detectó {len(alertas)} alerta(s). '
            'El flujo puede continuar en modo guiado, pero conviene revisar.'
        )
    else:
        resultado['mensaje'] = 'Sin discrepancias clínicas relevantes detectadas.'

    if accion == 'validar' and alertas:
        try:
            _persistir_incidencia(orden, empresa, usuario, alertas, modo, request=request)
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado al persistir incidencia clínica")

    return resultado
