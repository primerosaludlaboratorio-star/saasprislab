"""
laboratorio/services/iso15189.py
════════════════════════════════════════════════════════════════════════════════
FASE 6 — Motor de Validación ISO 15189:2022

Responsabilidades:
  1. Validar resultados contra rangos dinámicos (RangoReferenciaParametro)
  2. Detectar y disparar alertas de valores críticos ("panic values")
  3. Notificar al Químico validador y a PRIS cuando hay valores críticos
  4. Proveer API para que PRIS use en pre-llenado con rangos correctos

ISO 15189:2022 §7.3.7 — Intervalos de referencia biológica
ISO 15189:2022 §7.4.1 — Procedimientos de examen: valores de alerta
════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations
import logging
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger('laboratorio.iso15189')


# ─── Dataclasses de resultados de validación ──────────────────────────────────

@dataclass
class ValidacionResultado:
    """Resultado de validar un valor contra rangos de referencia."""
    valor_numerico: Optional[Decimal] = None
    es_numerico: bool = False
    es_anormal: bool = False
    es_critico: bool = False
    nivel: str = 'NORMAL'     # NORMAL | BAJO | ALTO | CRITICO_BAJO | CRITICO_ALTO
    rango_min: Optional[Decimal] = None
    rango_max: Optional[Decimal] = None
    critico_min: Optional[Decimal] = None
    critico_max: Optional[Decimal] = None
    fuente_rango: str = 'ESTATICO'  # ESTATICO | DINAMICO
    mensaje: str = ''
    alertas: list[str] = field(default_factory=list)


# ─── Función principal de validación ──────────────────────────────────────────

def validar_resultado(
    parametro_id: int,
    valor_str: str,
    edad_paciente: float | None = None,
    sexo_paciente: str | None = None,
) -> ValidacionResultado:
    """
    Valida un valor de resultado contra los rangos dinámicos del parámetro.
    Si no hay rangos dinámicos, cae al rango estático del Parámetro padre.

    Args:
        parametro_id: ID del modelo Parametro (laboratorio.Parametro)
        valor_str: Valor como string (puede contener letras: "Negativo", ">10")
        edad_paciente: Edad en años del paciente (para rangos por edad)
        sexo_paciente: 'M' o 'F' (para rangos por sexo)

    Returns:
        ValidacionResultado con todos los campos relevantes.
    """
    resultado = ValidacionResultado()

    # Parsear valor numérico
    valor_num = _parsear_valor(valor_str)
    resultado.valor_numerico = valor_num
    resultado.es_numerico = valor_num is not None

    if not resultado.es_numerico:
        return resultado

    # Buscar rango dinámico primero (ISO 15189)
    rango = _buscar_rango_dinamico(parametro_id, edad_paciente, sexo_paciente)

    if rango:
        resultado.fuente_rango = 'DINAMICO'
        resultado.rango_min = rango.get('valor_minimo')
        resultado.rango_max = rango.get('valor_maximo')
        resultado.critico_min = rango.get('valor_critico_bajo')
        resultado.critico_max = rango.get('valor_critico_alto')
    else:
        # Fallback: rango estático del Parametro
        resultado.fuente_rango = 'ESTATICO'
        _cargar_rango_estatico(parametro_id, resultado)

    # Clasificar valor
    _clasificar_valor(valor_num, resultado)

    return resultado


def validar_resultado_analito_lims(
    analito_id: int,
    valor_str: str,
    edad_paciente: float | int | None = None,
    sexo_paciente: str | None = None,
    edad_dias: int | None = None,
) -> ValidacionResultado:
    """
    Valida contra lims.ValorReferenciaAnalito — misma lógica que ``validar_contra_rango``
    (DIAS < 365 o ANOS). Escudo clínico v1.14: umbrales LIMS únicamente.
    """
    resultado = ValidacionResultado()
    valor_num = _parsear_valor(valor_str)
    resultado.valor_numerico = valor_num
    resultado.es_numerico = valor_num is not None
    if not resultado.es_numerico:
        return resultado

    from django.db.models import Q
    from lims.models import ValorReferenciaAnalito

    qs = ValorReferenciaAnalito.objects.filter(analito_id=analito_id)
    sexo = (sexo_paciente or '').strip().upper()[:1] or ''
    if sexo in ('M', 'F'):
        qs = qs.filter(Q(sexo=sexo) | Q(sexo='I'))
    else:
        qs = qs.filter(sexo='I')

    if edad_dias is not None and edad_dias < 365:
        qs = qs.filter(
            unidad_edad='DIAS',
            edad_minima__lte=edad_dias,
            edad_maxima__gte=edad_dias,
        )
    elif edad_paciente is not None:
        try:
            edad_anos = int(float(edad_paciente))
            if edad_anos < 1:
                edad_anos = 1
        except (TypeError, ValueError):
            return resultado
        qs = qs.filter(
            unidad_edad='ANOS',
            edad_minima__lte=edad_anos,
            edad_maxima__gte=edad_anos,
        )
    else:
        return resultado

    rango = qs.order_by('edad_minima').first()
    if not rango:
        return resultado

    ev = rango.evaluar_valor_numerico(valor_num)
    resultado.fuente_rango = 'DINAMICO'
    if rango.ref_minimo is not None:
        resultado.rango_min = Decimal(str(rango.ref_minimo))
    if rango.ref_maximo is not None:
        resultado.rango_max = Decimal(str(rango.ref_maximo))
    if rango.valor_critico_bajo is not None:
        resultado.critico_min = Decimal(str(rango.valor_critico_bajo))
    if rango.valor_critico_alto is not None:
        resultado.critico_max = Decimal(str(rango.valor_critico_alto))
    resultado.es_critico = bool(ev.get('es_critico'))
    resultado.es_anormal = bool(ev.get('fuera_rango')) or resultado.es_critico
    resultado.mensaje = ev.get('mensaje_critico') or ''
    resultado.nivel = ev.get('estado') or 'NORMAL'
    return resultado


def _parsear_valor(valor_str: str) -> Optional[Decimal]:
    """Convierte string a Decimal. Acepta '> 10', '<5.5', '10,5' etc."""
    if not valor_str:
        return None
    # Limpiar prefijos comunes
    cleaned = (
        valor_str.strip()
        .replace(',', '.')
        .lstrip('><= ')
        .split()[0]
    )
    try:
        return Decimal(cleaned)
    except (InvalidOperation, IndexError):
        return None


def _buscar_rango_dinamico(
    parametro_id: int,
    edad: float | None,
    sexo: str | None,
) -> dict | None:
    """
    Busca en RangoReferenciaParametro el rango que aplica para este paciente.
    Retorna None si los modelos de rangos dinámicos aún no están migrados.
    """
    try:
        from laboratorio.models import RangoReferenciaParametro  # post-migración
        edad_dec = Decimal(str(edad or 30))
        sexo_filtro = sexo if sexo in ('M', 'F') else 'A'

        rango = (
            RangoReferenciaParametro.objects
            .filter(
                parametro_id=parametro_id,
                activo=True,
                edad_min_anios__lte=edad_dec,
                edad_max_anios__gte=edad_dec,
                sexo__in=[sexo_filtro, 'A'],
            )
            .order_by('-sexo')  # Específico primero (M/F antes que A)
            .values('valor_minimo', 'valor_maximo',
                    'valor_critico_bajo', 'valor_critico_alto', 'fuente')
            .first()
        )
        return rango
    except Exception:
        return None  # Modelo no existe aún (pre-migración)


def _cargar_rango_estatico(parametro_id: int, resultado: ValidacionResultado):
    """Carga los rangos estáticos del modelo Parametro legado."""
    try:
        from laboratorio.models import Parametro
        param = Parametro.objects.get(pk=parametro_id)
        resultado.rango_min = param.valor_ref_min
        resultado.rango_max = param.valor_ref_max
    except Exception:
        pass


def _clasificar_valor(valor: Decimal, resultado: ValidacionResultado):
    """Clasifica el valor y actualiza el ValidacionResultado."""
    min_val = resultado.rango_min
    max_val = resultado.rango_max
    crit_bajo = resultado.critico_min
    crit_alto = resultado.critico_max

    # Verificar críticos primero (más urgente)
    if crit_bajo is not None and valor < crit_bajo:
        resultado.es_critico = True
        resultado.es_anormal = True
        resultado.nivel = 'CRITICO_BAJO'
        resultado.mensaje = f'⚠️ VALOR CRÍTICO BAJO: {valor} (crítico < {crit_bajo})'
        resultado.alertas.append(f'Pánico: valor {valor} por debajo del umbral crítico {crit_bajo}')
        return

    if crit_alto is not None and valor > crit_alto:
        resultado.es_critico = True
        resultado.es_anormal = True
        resultado.nivel = 'CRITICO_ALTO'
        resultado.mensaje = f'⚠️ VALOR CRÍTICO ALTO: {valor} (crítico > {crit_alto})'
        resultado.alertas.append(f'Pánico: valor {valor} por encima del umbral crítico {crit_alto}')
        return

    # Verificar anormalidad
    if min_val is not None and valor < min_val:
        resultado.es_anormal = True
        resultado.nivel = 'BAJO'
        resultado.mensaje = f'Valor bajo: {valor} (normal ≥ {min_val})'
        return

    if max_val is not None and valor > max_val:
        resultado.es_anormal = True
        resultado.nivel = 'ALTO'
        resultado.mensaje = f'Valor alto: {valor} (normal ≤ {max_val})'
        return

    resultado.nivel = 'NORMAL'
    resultado.mensaje = 'Valor dentro del rango normal'


# ─── Alertas de valores críticos ──────────────────────────────────────────────

def disparar_alerta_critica(
    resultado_id: int,
    validacion: ValidacionResultado,
    orden_id: int | None = None,
    paciente_nombre: str = '',
    parametro_nombre: str = '',
):
    """
    Notifica al Químico y a PRIS cuando se detecta un valor crítico.
    ISO 15189:2022 §7.4.1.5 — Reportes inmediatos de valores de alerta.
    """
    if not validacion.es_critico:
        return

    mensaje = (
        f'🚨 *VALOR CRÍTICO DETECTADO — ISO 15189*\n'
        f'Parámetro: `{parametro_nombre}`\n'
        f'Valor: `{validacion.valor_numerico}` ({validacion.nivel})\n'
        f'Paciente: {paciente_nombre}\n'
        f'Orden ID: {orden_id}'
    )

    # Log prioritario
    logger.warning(f'[ISO 15189] VALOR CRÍTICO — Orden {orden_id} — {parametro_nombre}: {validacion.valor_numerico}')

    # Notificar vía Telegram/Email
    import threading
    threading.Thread(
        target=_enviar_alerta_critica_bg,
        args=(mensaje, resultado_id, orden_id),
        daemon=True,
    ).start()


def _enviar_alerta_critica_bg(mensaje: str, resultado_id: int, orden_id):
    """Ejecutado en thread daemon. No bloquea el flujo de validación."""
    try:
        from django.conf import settings
        from core.services.telegram_outbound import send_telegram_message

        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or None
        chat_id = getattr(settings, 'TELEGRAM_CISO_CHAT_ID', '') or None
        if token and chat_id:
            send_telegram_message(
                token, chat_id, mensaje, parse_mode='Markdown'
            )
    except Exception as exc:
        logger.debug(f'[ISO 15189] Alerta crítica no enviada: {exc}')


# ─── Helper para PRIS: obtener rangos para pre-llenado ────────────────────────

def obtener_rangos_para_pris(
    parametros_ids: list[int],
    edad: float | None = None,
    sexo: str | None = None,
) -> dict[int, dict]:
    """
    Retorna un mapa {parametro_id: {min, max, critico_bajo, critico_alto, unidad}}
    que PRIS usa para validar en tiempo real mientras el químico dicta resultados.
    """
    rangos = {}
    for pid in parametros_ids:
        rango = _buscar_rango_dinamico(pid, edad, sexo)
        if rango:
            rangos[pid] = rango
        else:
            try:
                from laboratorio.models import Parametro
                param = Parametro.objects.get(pk=pid)
                rangos[pid] = {
                    'valor_minimo': param.valor_ref_min,
                    'valor_maximo': param.valor_ref_max,
                    'valor_critico_bajo': None,
                    'valor_critico_alto': None,
                    'fuente': 'ESTATICO',
                }
            except Exception:
                rangos[pid] = {}
    return rangos
