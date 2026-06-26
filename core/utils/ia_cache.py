"""
core/utils/ia_cache.py
──────────────────────
Motor de Caché de Inteligencia Local (Reglas Aprobadas por QFB).

Flujo:
  1. PRIS genera una respuesta IA → se guarda como ReglaLocalIA (estado=PROPUESTA).
  2. QFB revisa en el panel de Reglas Locales y hace clic en "Aprobar".
  3. En las consultas futuras, buscar_en_cache() devuelve la respuesta local
     sin llamar a la API de Gemini ($0 de costo).
  4. Si no hay coincidencia en caché, el sistema llama a la API normalmente.

Normalización de claves:
  Las claves se normalizan (minúsculas, sin tildes, sin caracteres especiales)
  para maximizar el porcentaje de aciertos del caché.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import Empresa, ReglaLocalIA

logger = logging.getLogger('core.ia_cache')

UMBRAL_CONFIANZA_DEFAULT = 0.75


# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar(texto: str) -> str:
    """Convierte a lowercase sin tildes ni caracteres especiales."""
    nfkd = unicodedata.normalize('NFKD', texto)
    sin_tildes = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r'[^\w\s]', ' ', sin_tildes).lower().strip()


def construir_clave(ambito: str, *partes: str) -> str:
    """
    Genera la clave canónica para una regla.
    Ejemplo: construir_clave('CHECKLIST_TOMA', 'AYUNO', 'GLUCOSA')
             → 'checklist_toma:ayuno:glucosa'
    """
    return ':'.join(_normalizar(p) for p in [ambito, *partes] if p)


# ─────────────────────────────────────────────────────────────────────────────
# BÚSQUEDA EN CACHÉ
# ─────────────────────────────────────────────────────────────────────────────

def buscar_en_cache(
    empresa: 'Empresa',
    ambito: str,
    clave: str,
) -> 'ReglaLocalIA | None':
    """
    Busca una regla local aprobada para la empresa, ámbito y clave dados.

    Retorna la instancia ReglaLocalIA o None si no hay coincidencia activa.
    """
    from core.models import ReglaLocalIA
    clave_norm = _normalizar(clave)
    try:
        regla = (
            ReglaLocalIA.objects
            .filter(empresa=empresa, ambito=ambito, clave=clave_norm,
                    estado=ReglaLocalIA.ESTADO_APROBADA)
            .order_by('-confianza', '-veces_usada')
            .first()
        )
        if regla:
            logger.debug(
                "ia_cache HIT: empresa=%s ambito=%s clave=%s",
                empresa.pk, ambito, clave_norm,
            )
        return regla
    except Exception as exc:
        logger.warning("buscar_en_cache: error — %s", exc)
        return None


def responder_desde_cache(
    empresa: 'Empresa',
    ambito: str,
    clave: str,
    tokens_estimados: int = 400,
) -> dict | None:
    """
    Responde desde la caché si hay una regla aprobada.

    Retorna:
        {'ok': True, 'texto': str, 'fuente': 'LOCAL', 'regla_id': int}
        o None si no hay caché disponible.
    """
    regla = buscar_en_cache(empresa, ambito, clave)
    if not regla:
        return None

    # Registrar uso y tokens ahorrados
    regla.registrar_uso(tokens_estimados)

    # Registrar en UsoRecursosIA con fuente=LOCAL (costo $0)
    try:
        from core.utils.ia_resources import registrar_uso_ia
        registrar_uso_ia(
            empresa=empresa,
            tipo_proceso=ambito,
            tokens_entrada=0,
            tokens_salida=0,
            fuente_key='LOCAL',
            referencia=f'cache:{regla.pk}',
        )
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en responder_desde_cache (ia_cache.py)")
        pass

    return {
        'ok': True,
        'texto': regla.respuesta_efectiva(),
        'fuente': 'LOCAL',
        'regla_id': regla.pk,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PROPONER NUEVA REGLA (después de una respuesta IA aprobada)
# ─────────────────────────────────────────────────────────────────────────────

def proponer_regla(
    empresa: 'Empresa',
    ambito: str,
    clave: str,
    contexto_original: str,
    respuesta_ia: str,
    confianza: float = 0.80,
) -> 'ReglaLocalIA':
    """
    Crea o actualiza una ReglaLocalIA en estado PROPUESTA.
    Si ya existe una aprobada con la misma clave, la actualiza con
    la nueva respuesta y la devuelve al estado PROPUESTA para re-validación.

    El QFB debe revisar y aprobar desde el panel de administración.
    """
    from core.models import ReglaLocalIA
    clave_norm = _normalizar(clave)

    regla, creada = ReglaLocalIA.objects.update_or_create(
        empresa=empresa,
        ambito=ambito,
        clave=clave_norm,
        defaults={
            'contexto_original': contexto_original[:2000],
            'respuesta_ia': respuesta_ia[:4000],
            'estado': ReglaLocalIA.ESTADO_PROPUESTA,
            'confianza': confianza,
        },
    )
    accion = "creada" if creada else "actualizada para re-validación"
    logger.info(
        "ReglaLocalIA %s: empresa=%s ambito=%s clave=%s",
        accion, empresa.pk, ambito, clave_norm,
    )
    return regla


# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN DE EFECTIVIDAD DEL CACHÉ
# ─────────────────────────────────────────────────────────────────────────────

def estadisticas_cache(empresa: 'Empresa') -> dict:
    """
    Retorna estadísticas de eficiencia del caché de reglas locales.

    Retorna:
        {
          'reglas_aprobadas': int,
          'reglas_pendientes': int,
          'total_usos_cache': int,
          'tokens_ahorrados_total': int,
          'tasa_acierto_estimada': str,  # porcentaje legible
        }
    """
    from core.models import ReglaLocalIA
    from django.db.models import Sum

    qs = ReglaLocalIA.objects.filter(empresa=empresa)
    aprobadas   = qs.filter(estado=ReglaLocalIA.ESTADO_APROBADA)
    pendientes  = qs.filter(estado=ReglaLocalIA.ESTADO_PROPUESTA)

    usos    = aprobadas.aggregate(u=Sum('veces_usada'))['u'] or 0
    ahorros = aprobadas.aggregate(t=Sum('tokens_ahorrados'))['t'] or 0

    return {
        'reglas_aprobadas': aprobadas.count(),
        'reglas_pendientes': pendientes.count(),
        'total_usos_cache': usos,
        'tokens_ahorrados_total': ahorros,
        'tasa_acierto_estimada': f"{min(round(aprobadas.count() / max(qs.count(), 1) * 100, 1), 100)}%",
    }