"""
core/utils/ia_resources.py
──────────────────────────
Servicio central de Gobernanza de IA para PRISLAB SaaS.

Funciones clave
───────────────
  verificar_disponibilidad_ia(empresa, tipo_proceso)
      → True si se puede llamar a la API | False si hay que usar Modo Manual.

  registrar_uso_ia(empresa, tipo_proceso, tokens_in, tokens_out, modelo, latencia_ms, ...)
      → Guarda un registro en UsoRecursosIA y dispara alertas de cuota.

  consumo_mensual(empresa)
      → Dict con totales del mes actual, porcentaje usado y tokens disponibles.

  get_gemini_client_para_empresa(empresa)
      → Cliente Gemini configurado con la key del laboratorio (BYOK) o la master key.

  modo_ia_activo(empresa)
      → Retorna el ConfiguracionModulos.modo_ia actual ('APRENDIZAJE', 'PRODUCCION', 'AHORRO_EXTREMO').

  ia_habilitada_para_proceso(empresa, tipo_proceso)
      → Verifica si el modo actual permite ejecutar ese proceso de IA.
"""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import TYPE_CHECKING

from django.db import models as djm
from django.utils import timezone

if TYPE_CHECKING:
    from core.models import Empresa

logger = logging.getLogger('core.ia_resources')

# Procesos que se permiten incluso en modo AHORRO_EXTREMO
PROCESOS_CRITICOS = {
    'NLP_TOMA',       # Checklist autónomo de toma de muestra
    'RAG_CONSULTA',   # Consulta de manuales internos
    'QC_ANALISIS',    # Análisis Westgard — seguridad clínica
}

# Modo AHORRO bloquea estos procesos (IA generativa no crítica)
PROCESOS_BLOQUEADOS_AHORRO = {
    'MARKETING_IA',
    'WORKLIST_SUGERENCIA',
    'OTRO',
}

# Tokens estimados típicos por proceso (para calcular ahorro de reglas locales)
TOKENS_ESTIMADOS_POR_PROCESO = {
    'NLP_TOMA': 300,
    'RESUMEN_CLINICO': 800,
    'RAG_CONSULTA': 500,
    'OCR_DOCUMENTO': 400,
    'MARKETING_IA': 600,
    'WORKLIST_SUGERENCIA': 350,
    'QC_ANALISIS': 400,
    'OTRO': 400,
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _get_config_modulos(empresa: 'Empresa'):
    """Retorna el ConfiguracionModulos de la empresa, o None si no existe."""
    try:
        return empresa.configuracion_modulos
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _get_config_modulos (ia_resources.py)")
        return None


def _consumo_tokens_mes(empresa: 'Empresa') -> int:
    """Suma de tokens_total del mes en curso (excluye llamadas LOCAL=$0)."""
    from core.models import UsoRecursosIA
    hoy = date.today()
    return (
        UsoRecursosIA.objects
        .filter(empresa=empresa, fecha__year=hoy.year, fecha__month=hoy.month)
        .exclude(fuente_key='LOCAL')
        .aggregate(total=djm.Sum('tokens_total'))['total'] or 0
    )


# ─────────────────────────────────────────────────────────────────────────────
# API PÚBLICA
# ─────────────────────────────────────────────────────────────────────────────

def modo_ia_activo(empresa: 'Empresa') -> str:
    """
    Retorna el modo IA configurado: 'APRENDIZAJE', 'PRODUCCION' o 'AHORRO_EXTREMO'.
    Fallback seguro a 'PRODUCCION' si no hay configuración.
    """
    cfg = _get_config_modulos(empresa)
    if cfg:
        return cfg.modo_ia
    # Fallback al campo directo de Empresa (si se migró)
    return getattr(empresa, 'modo_ia', 'PRODUCCION') or 'PRODUCCION'


def ia_habilitada_para_proceso(empresa: 'Empresa', tipo_proceso: str) -> bool:
    """
    Determina si el tipo de proceso IA puede ejecutarse según el modo actual.

    Reglas:
      AHORRO_EXTREMO  → Solo PROCESOS_CRITICOS permitidos.
      PRODUCCION      → Todos permitidos.
      APRENDIZAJE     → Todos permitidos (recolecta datos para reglas locales).
    """
    cfg = _get_config_modulos(empresa)
    if cfg and not cfg.modulo_ia:
        return False  # Módulo IA desactivado por contrato

    modo = modo_ia_activo(empresa)

    if modo == 'AHORRO_EXTREMO':
        return tipo_proceso in PROCESOS_CRITICOS

    return True  # PRODUCCION / APRENDIZAJE → todos permitidos


def verificar_disponibilidad_ia(empresa: 'Empresa', tipo_proceso: str = 'OTRO') -> dict:
    """
    Punto de entrada principal antes de cualquier llamada a la API de Gemini.

    Retorna:
        {
          'disponible': bool,
          'fuente': 'BYOK' | 'MASTER' | 'LOCAL',
          'motivo': str,           # explicación humana
          'modo_ia': str,
          'porcentaje_consumo': float,  # solo cuando fuente='MASTER'
        }

    Uso típico:
        resultado = verificar_disponibilidad_ia(empresa, 'NLP_TOMA')
        if not resultado['disponible']:
            # Modo manual — no llamar a Gemini
            return resultado
        client = get_gemini_client_para_empresa(empresa)
    """
    resultado_base = {
        'disponible': False,
        'fuente': 'MASTER',
        'motivo': '',
        'modo_ia': modo_ia_activo(empresa),
        'porcentaje_consumo': 0.0,
    }

    # 1. ¿El proceso está habilitado en este modo?
    if not ia_habilitada_para_proceso(empresa, tipo_proceso):
        resultado_base['motivo'] = (
            f"Proceso '{tipo_proceso}' no permitido en modo "
            f"'{resultado_base['modo_ia']}' (Ahorro Extremo activo)."
        )
        return resultado_base

    # 2. BYOK — key propia del laboratorio: uso ilimitado
    if empresa.tiene_byok_gemini():
        resultado_base.update({
            'disponible': True,
            'fuente': 'BYOK',
            'motivo': 'API Key propia del laboratorio (BYOK) — sin restricción de cuota.',
        })
        return resultado_base

    # 3. MASTER KEY — verificar cuota mensual
    cfg = _get_config_modulos(empresa)
    limite = getattr(cfg, 'limite_mensual_tokens_ia', 50_000) if cfg else 50_000
    consumo = _consumo_tokens_mes(empresa)
    porcentaje = round((consumo / limite * 100) if limite > 0 else 100.0, 1)
    resultado_base['porcentaje_consumo'] = porcentaje

    if consumo >= limite:
        resultado_base.update({
            'disponible': False,
            'fuente': 'MASTER',
            'motivo': (
                f"Cuota mensual agotada ({consumo:,} / {limite:,} tokens). "
                "El sistema continúa en Modo Manual (LIMS tradicional sin IA)."
            ),
        })
        return resultado_base

    # Disponible con la key maestra
    resultado_base.update({
        'disponible': True,
        'fuente': 'MASTER',
        'motivo': f"Consumo: {porcentaje}% ({consumo:,}/{limite:,} tokens).",
    })
    return resultado_base


def get_gemini_client_para_empresa(empresa: 'Empresa'):
    """
    Retorna un cliente Gemini (google.genai.Client) configurado con la key
    correcta según el tenant: BYOK primero, luego MASTER_KEY del sistema.

    Raises ValueError si ninguna key está disponible.
    """
    from google import genai  # type: ignore
    from django.conf import settings

    # Intentar BYOK primero
    byok_key = empresa.get_byok_gemini_key()
    if byok_key:
        logger.debug("Gemini: usando BYOK key para empresa %s", empresa.pk)
        return genai.Client(api_key=byok_key)

    # Fallback: MASTER KEY del entorno
    master_key = (
        getattr(settings, 'GOOGLE_API_KEY', '') or
        getattr(settings, 'GEMINI_API_KEY', '') or
        getattr(settings, 'GOOGLE_GEMINI_API_KEY', '')
    )
    if master_key:
        logger.debug("Gemini: usando MASTER KEY para empresa %s", empresa.pk)
        return genai.Client(api_key=master_key.strip())

    raise ValueError(
        "No hay API Key de Gemini configurada. "
        "Configure BYOK en el panel de la empresa o agregue GOOGLE_API_KEY al entorno."
    )


def registrar_uso_ia(
    empresa: 'Empresa',
    tipo_proceso: str,
    tokens_entrada: int = 0,
    tokens_salida: int = 0,
    modelo: str = 'gemini-2.0-flash',
    latencia_ms: int = 0,
    usuario_id: int | None = None,
    referencia: str = '',
    fuente_key: str = 'MASTER',
) -> None:
    """
    Registra el consumo de tokens en UsoRecursosIA y dispara alertas de cuota.
    Llámala DESPUÉS de cada llamada a la API de Gemini.
    Silencia errores — no debe bloquear el flujo principal.
    """
    try:
        from core.models import UsoRecursosIA
        UsoRecursosIA.objects.create(
            empresa=empresa,
            fecha=date.today(),
            tipo_proceso=tipo_proceso,
            tokens_entrada=tokens_entrada,
            tokens_salida=tokens_salida,
            fuente_key=fuente_key,
            modelo_usado=modelo,
            latencia_ms=latencia_ms,
            usuario_id=usuario_id,
            referencia=referencia[:200],
        )
        # Verificar si hay que enviar alertas de cuota (solo key maestra)
        if fuente_key == 'MASTER':
            _verificar_alertas_cuota(empresa)
    except Exception as exc:
        logger.warning("registrar_uso_ia: error al guardar — %s", exc)


def _verificar_alertas_cuota(empresa: 'Empresa') -> None:
    """Envía notificaciones cuando el consumo llega a 80% o 90% de la cuota."""
    try:
        from core.models import ConfiguracionModulos
        cfg = _get_config_modulos(empresa)
        if not cfg:
            return
        limite = cfg.limite_mensual_tokens_ia
        consumo = _consumo_tokens_mes(empresa)
        porcentaje = (consumo / limite * 100) if limite > 0 else 0

        if porcentaje >= 90 and not cfg.alerta_consumo_90_enviada:
            _enviar_alerta_cuota(empresa, porcentaje, 90)
            ConfiguracionModulos.objects.filter(pk=cfg.pk).update(
                alerta_consumo_90_enviada=True
            )
        elif porcentaje >= 80 and not cfg.alerta_consumo_80_enviada:
            _enviar_alerta_cuota(empresa, porcentaje, 80)
            ConfiguracionModulos.objects.filter(pk=cfg.pk).update(
                alerta_consumo_80_enviada=True
            )
    except Exception as exc:
        logger.warning("_verificar_alertas_cuota: %s", exc)


def _enviar_alerta_cuota(empresa: 'Empresa', porcentaje: float, umbral: int) -> None:
    """Registra la alerta en el sistema de notificaciones interno."""
    try:
        from core.utils.notificaciones import crear_notificacion_sistema
        crear_notificacion_sistema(
            empresa=empresa,
            titulo=f"⚠️ IA: consumo al {umbral}%",
            mensaje=(
                f"El laboratorio '{empresa.nombre}' ha usado el {porcentaje:.1f}% "
                f"de su cuota mensual de IA ({umbral}% de alerta). "
                "Considera activar el modo 'Ahorro Extremo' o contratar más tokens."
            ),
            tipo='ALERTA',
        )
    except Exception as exc:
        logger.warning("_enviar_alerta_cuota: no se pudo notificar — %s", exc)


def consumo_mensual(empresa: 'Empresa') -> dict:
    """
    Retorna un resumen del consumo del mes en curso.

    Retorna:
        {
          'tokens_usados': int,
          'tokens_limite': int,
          'porcentaje': float,
          'tokens_restantes': int,
          'llamadas_total': int,
          'llamadas_por_proceso': dict,
          'tokens_ahorrados_cache': int,
          'fuente': 'BYOK' | 'MASTER',
        }
    """
    from core.models import UsoRecursosIA, ReglaLocalIA
    hoy = date.today()
    cfg = _get_config_modulos(empresa)
    limite = getattr(cfg, 'limite_mensual_tokens_ia', 50_000) if cfg else 50_000

    qs = UsoRecursosIA.objects.filter(
        empresa=empresa, fecha__year=hoy.year, fecha__month=hoy.month
    )

    tokens_usados = qs.exclude(fuente_key='LOCAL').aggregate(
        t=djm.Sum('tokens_total')
    )['t'] or 0

    llamadas_total = qs.count()

    por_proceso = dict(
        qs.exclude(fuente_key='LOCAL')
          .values('tipo_proceso')
          .annotate(total=djm.Sum('tokens_total'))
          .values_list('tipo_proceso', 'total')
    )

    tokens_ahorrados = (
        ReglaLocalIA.objects.filter(empresa=empresa, estado='APROBADA')
        .aggregate(t=djm.Sum('tokens_ahorrados'))['t'] or 0
    )

    porcentaje = round((tokens_usados / limite * 100) if limite > 0 else 0, 1)

    return {
        'tokens_usados': tokens_usados,
        'tokens_limite': limite,
        'porcentaje': porcentaje,
        'tokens_restantes': max(0, limite - tokens_usados),
        'llamadas_total': llamadas_total,
        'llamadas_por_proceso': por_proceso,
        'tokens_ahorrados_cache': tokens_ahorrados,
        'fuente': 'BYOK' if empresa.tiene_byok_gemini() else 'MASTER',
    }


def llamar_gemini_con_gobernanza(
    empresa: 'Empresa',
    prompt: str,
    tipo_proceso: str = 'OTRO',
    modelo: str = 'gemini-2.0-flash',
    temperatura: float = 0.2,
    max_tokens: int = 1024,
    usuario_id: int | None = None,
    referencia: str = '',
) -> dict:
    """
    Wrapper completo que:
      1. Verifica disponibilidad (cuota, modo, módulo activo).
      2. Llama a la API de Gemini con el cliente correcto (BYOK o MASTER).
      3. Registra el uso de tokens.
      4. Retorna {'ok': bool, 'texto': str, 'fuente': str, 'motivo': str}.

    En caso de cuota agotada o modo AHORRO, retorna ok=False con motivo claro
    para que el caller degrade a Modo Manual sin arrojar excepciones.
    """
    disponibilidad = verificar_disponibilidad_ia(empresa, tipo_proceso)
    if not disponibilidad['disponible']:
        return {
            'ok': False,
            'texto': '',
            'fuente': disponibilidad['fuente'],
            'motivo': disponibilidad['motivo'],
        }

    t0 = time.monotonic()
    fuente = disponibilidad['fuente']

    try:
        from google.genai import types  # type: ignore
        client = get_gemini_client_para_empresa(empresa)
        config = types.GenerateContentConfig(
            temperature=temperatura,
            max_output_tokens=max_tokens,
        )
        response = client.models.generate_content(
            model=modelo,
            contents=prompt,
            config=config,
        )
        texto = response.text or ''
        latencia = int((time.monotonic() - t0) * 1000)

        # Estimar tokens (Gemini no siempre los expone en el objeto respuesta)
        tokens_in  = len(prompt.split())
        tokens_out = len(texto.split())

        registrar_uso_ia(
            empresa=empresa,
            tipo_proceso=tipo_proceso,
            tokens_entrada=tokens_in,
            tokens_salida=tokens_out,
            modelo=modelo,
            latencia_ms=latencia,
            usuario_id=usuario_id,
            referencia=referencia,
            fuente_key=fuente,
        )

        return {'ok': True, 'texto': texto, 'fuente': fuente, 'motivo': ''}

    except Exception as exc:
        logger.error("llamar_gemini_con_gobernanza: error — %s", exc)
        return {
            'ok': False,
            'texto': '',
            'fuente': fuente,
            'motivo': f'Error de API Gemini: {exc}',
        }