"""
core/services/feature_flags.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sistema de Feature Flags — Interruptores del Director
Usa reglas_negocio.ReglaNegocio como almacén persistente.
Sin migraciones nuevas. Caché en memoria por 5 minutos.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations
import logging
import threading
from datetime import timedelta
from django.utils import timezone
from typing import Any

logger = logging.getLogger('core.feature_flags')

# ─── Catálogo de flags con valores por defecto y descripción humana ──────────
FLAG_CATALOG: dict[str, dict] = {
    # ── ISO 15189 FLEXIBILIDAD ─────────────────────────────────────────────────
    'ISO_STRICT_MODE': {
        'default': False,
        'categoria': 'LABORATORIO',
        'nombre': 'ISO 15189 — Modo Estricto (Bloqueo por Cédula)',
        'descripcion': (
            'EN OFF (por defecto): Pasantes, practicantes y médicos sin cédula validada '
            'pueden operar normalmente. El War Room registra la ausencia de cédula como '
            'aviso informativo. La responsabilidad legal recae en el Director. '
            'EN ON: Bloquea resultados sin médico con cédula verificada en SEP. '
            'Activar SOLO cuando el laboratorio tenga acreditación ISO 15189 completa.'
        ),
    },

    # ISO 15189
    'ISO15189_CRITICOS_ACTIVO': {
        'default': True,
        'categoria': 'LABORATORIO',
        'nombre': 'Alertas de Valores Críticos (ISO 15189)',
        'descripcion': (
            'Activa alertas automáticas cuando un resultado excede rangos críticos. '
            'Recomendado para acreditación ISO 15189. '
            'Si se apaga, los resultados se guardan sin alerta adicional.'
        ),
    },
    'DELTA_CHECK_ACTIVO': {
        'default': True,
        'categoria': 'LABORATORIO',
        'nombre': 'Delta Check (Comparación con resultado previo)',
        'descripcion': (
            'Compara el resultado actual con el del mismo paciente en los últimos 90 días. '
            'Si la variación es >30%, genera una advertencia antes de validar. '
            'Requiere historial de resultados en el sistema.'
        ),
    },
    'QC_WESTGARD_ACTIVO': {
        'default': False,
        'categoria': 'LABORATORIO',
        'nombre': 'Control de Calidad — Reglas de Westgard',
        'descripcion': (
            'Evalúa los sueros control contra las reglas de Westgard (1-2s, 1-3s, 2-2s, R-4s, 4-1s, 10x). '
            'Genera alarma de QC antes de liberar resultados de paciente. '
            'Estándar ISO 15189 y CAP.'
        ),
    },

    # NOM-024 / Seguridad
    'NOM024_LOG_EXPEDIENTES_ACTIVO': {
        'default': True,
        'categoria': 'SEGURIDAD',
        'nombre': 'Trazabilidad NOM-024 (Log de acceso a expedientes)',
        'descripcion': (
            'Registra en bitácora quién, cuándo y desde dónde accede a un expediente clínico. '
            'Requerido por NOM-024. Apagar solo en entornos de desarrollo o pruebas.'
        ),
    },
    '2FA_OBLIGATORIO_ACTIVO': {
        'default': False,
        'categoria': 'SEGURIDAD',
        'nombre': '2FA Obligatorio para Administradores',
        'descripcion': (
            'Fuerza autenticación de dos factores (TOTP) para roles ADMIN y DIRECTOR. '
            'Si se apaga, el 2FA queda disponible pero no es obligatorio. '
            'Activar en entornos de producción con datos clínicos reales.'
        ),
    },
    'VERIFICACION_SEP_ACTIVA': {
        'default': False,
        'categoria': 'LABORATORIO',
        'nombre': 'Verificación de Cédula Profesional (SEP) — Solo informativa',
        'descripcion': (
            'Consulta la base de datos de la SEP al registrar un médico. '
            'NUNCA bloquea el registro. Solo agrega un badge de validación. '
            'Pasantes y practicantes pueden registrarse sin restricción.'
        ),
    },

    # Audio / Legal
    'AUDIO_SELLADO_LEGAL_ACTIVO': {
        'default': False,
        'categoria': 'SEGURIDAD',
        'nombre': 'Sellado Legal de Audio (Hash SHA-256 + Timestamp)',
        'descripcion': (
            'Genera una firma digital de cada transcripción de voz con timestamp '
            'del servidor. Da validez jurídica al registro de audio. '
            'Activar cuando el laboratorio requiera blindaje legal completo.'
        ),
    },

    # OCR / Visión
    'OCR_CLASIFICACION_ACTIVO': {
        'default': True,
        'categoria': 'LABORATORIO',
        'nombre': 'Motor OCR Inteligente (Clasificación de documentos)',
        'descripcion': (
            'Clasifica automáticamente documentos fotografiados: INE, receta médica, '
            'orden de laboratorio. Pre-llena el formulario de recepción con los datos '
            'extraídos. Ahorra tiempo y reduce errores de captura.'
        ),
    },
    'OCR_SUGERENCIAS_PERFIL_ACTIVO': {
        'default': True,
        'categoria': 'LABORATORIO',
        'nombre': 'Sugerencias de Perfil por Contexto Clínico',
        'descripcion': (
            'Si PRIS detecta una receta de ginecología, sugiere automáticamente el '
            'perfil de control prenatal. Las sugerencias son siempre opcionales. '
            'Nunca se agregan estudios sin confirmación del operador.'
        ),
    },

    # PRIS IA
    'PRIS_IA_ACTIVO': {
        'default': True,
        'categoria': 'GENERAL',
        'nombre': 'PRIS — Asistente IA (Copiloto del sistema)',
        'descripcion': (
            'Activa el copiloto de inteligencia artificial PRIS. '
            'Si se apaga, el widget de PRIS no aparece y los endpoints /ia/asistente/ '
            'quedan desactivados.'
        ),
    },

    # Bienestar
    'BIENESTAR_STAFF_ACTIVO': {
        'default': True,
        'categoria': 'GENERAL',
        'nombre': 'Módulo Bienestar Staff (NOM-035)',
        'descripcion': (
            'Activa el módulo de bienestar del personal: diario emocional, '
            'evaluación NOM-035, alertas de burnout y sesiones de coaching. '
            'Todos los datos son privados y solo visibles para RRHH (no clínicos).'
        ),
    },
    'COACH_TOMA_MUESTRA_ACTIVO': {
        'default': True,
        'categoria': 'LABORATORIO',
        'nombre': 'Coach Digital de Toma de Muestra',
        'descripcion': (
            'Evalúa el protocolo del analista durante la toma de muestra usando IA. '
            'Genera reportes de mejora continua positivos (nunca acusatorios). '
            'El personal es apoyado, no vigilado.'
        ),
    },

    # Kiosco
    'KIOSCO_ACTIVO': {
        'default': True,
        'categoria': 'GENERAL',
        'nombre': 'Kiosco de Auto Check-in (QR)',
        'descripcion': (
            'Permite a los pacientes hacer check-in escaneando el QR de su orden. '
            'Reduce el tiempo de espera en recepción.'
        ),
    },

    # ── BRECHAS DE ORO v5.1 ────────────────────────────────────────────────────

    'WAR_ROOM_ACTIVO': {
        'default': True,
        'categoria': 'DIRECTOR',
        'nombre': 'War Room — Dashboard de Excepciones del Director',
        'descripcion': (
            'Activa el panel /director/war-room/ con detección automática de anomalías: '
            'discrepancias de caja >2%, valores de pánico sin validar >15 min, '
            'intentos de acceso fallido a módulos cifrados y stock crítico de reactivos. '
            'PRIS-Jarvis reporta solo lo que requiere acción inmediata.'
        ),
    },
    'CADENA_FRIO_ACTIVO': {
        'default': True,
        'categoria': 'LABORATORIO',
        'nombre': 'Certificación de Cadena de Frío ISO 15189',
        'descripcion': (
            'Exige captura obligatoria de temperatura (2-8°C) al escanear el QR '
            'de traslado de muestras entre sucursales. Si la temperatura sale del '
            'rango, PRIS bloquea el envío y alerta al Químico Jefe. '
            'Requerido para acreditación ISO 15189 en transporte de muestras.'
        ),
    },
    'PREDICCION_STOCK_ACTIVO': {
        'default': True,
        'categoria': 'FARMACIA',
        'nombre': 'IA de Reabastecimiento Predictivo (3 días)',
        'descripcion': (
            'Analiza el consumo histórico de los últimos 30 días y predice cuándo '
            'se agotará cada producto. Genera alertas automáticas con 3 días de '
            'anticipación y permite a PRIS generar órdenes de compra preventivas. '
            'Visible en el War Room del Director.'
        ),
    },
    'FIRMA_DIGITAL_CONSENTIMIENTO': {
        'default': True,
        'categoria': 'SEGURIDAD',
        'nombre': 'Consentimiento Informado 100% Digital (Firma en Pantalla)',
        'descripcion': (
            'Captura la firma biométrica del paciente en el Kiosco o tablet. '
            'Genera un PDF con el hash SHA-256 del audio de la explicación inyectado '
            'en los metadatos, creando un blindaje legal completo. '
            'Elimina el papel y fortalece la defensa ante demandas.'
        ),
    },
    'PRIS_OFFLINE_FALLBACK': {
        'default': True,
        'categoria': 'GENERAL',
        'nombre': 'Orb de Contingencia PRIS (Modo Offline)',
        'descripcion': (
            'Si la API de Gemini no responde en 8 segundos, el Orb cambia a rojo '
            'y despliega un menú estático de "Acciones Críticas Manuales" '
            '(Crear orden, Consultar stock). El laboratorio NUNCA se detiene. '
            'El sistema detecta automáticamente la restauración del servicio.'
        ),
    },
}

# ─── Caché en memoria ─────────────────────────────────────────────────────────
_cache_lock = threading.Lock()
_cache: dict[str, dict] = {}  # empresa_id → {flag: bool, ..., _ts: datetime}
_CACHE_TTL_SECONDS = 300  # 5 minutos


def _cache_key(empresa_id: int | None) -> str:
    return str(empresa_id or 'global')


def _invalidate(empresa_id: int | None = None):
    with _cache_lock:
        key = _cache_key(empresa_id)
        _cache.pop(key, None)


def _load_from_db(empresa_id: int | None) -> dict[str, bool]:
    """Carga flags desde reglas_negocio.ReglaNegocio."""
    resultado = {k: v['default'] for k, v in FLAG_CATALOG.items()}
    try:
        from reglas_negocio.models import ReglaNegocio
        qs = ReglaNegocio.objects.filter(
            codigo__in=list(FLAG_CATALOG.keys()),
        )
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        for regla in qs:
            if regla.codigo in resultado:
                resultado[regla.codigo] = regla.activa
    except Exception as exc:
        logger.warning(f'[FeatureFlags] No se pudo leer DB: {exc}. Usando defaults.')
    return resultado


def _get_flags(empresa_id: int | None) -> dict[str, bool]:
    key = _cache_key(empresa_id)
    with _cache_lock:
        entry = _cache.get(key)
        if entry:
            if timezone.now() - entry['_ts'] < timedelta(seconds=_CACHE_TTL_SECONDS):
                return {k: v for k, v in entry.items() if k != '_ts'}
    flags = _load_from_db(empresa_id)
    with _cache_lock:
        _cache[key] = {**flags, '_ts': timezone.now()}
    return flags


# ─── API pública ──────────────────────────────────────────────────────────────

def flag_activo(codigo: str, empresa=None) -> bool:
    """
    Retorna True si el flag está activo para la empresa dada.
    Si el flag no existe en el catálogo, retorna False y loguea warning.

    Uso:
        from core.services.feature_flags import flag_activo
        if flag_activo('ISO15189_CRITICOS_ACTIVO', request.user.empresa):
            ...
    """
    if codigo not in FLAG_CATALOG:
        logger.warning(f'[FeatureFlags] Flag desconocido: {codigo}')
        return False
    empresa_id = getattr(empresa, 'id', None) if empresa else None
    flags = _get_flags(empresa_id)
    return bool(flags.get(codigo, FLAG_CATALOG[codigo]['default']))


def obtener_todos(empresa=None) -> dict[str, dict]:
    """
    Devuelve todos los flags con su estado y metadata para el panel de admin.
    """
    empresa_id = getattr(empresa, 'id', None) if empresa else None
    flags = _get_flags(empresa_id)
    resultado = {}
    for codigo, meta in FLAG_CATALOG.items():
        resultado[codigo] = {
            'activo': flags.get(codigo, meta['default']),
            'nombre': meta['nombre'],
            'descripcion': meta['descripcion'],
            'categoria': meta['categoria'],
            'es_default': flags.get(codigo, None) is None,
        }
    return resultado


def activar(codigo: str, empresa, usuario=None) -> bool:
    """Activa un flag y lo persiste en ReglaNegocio."""
    return _set_flag(codigo, empresa, True, usuario)


def desactivar(codigo: str, empresa, usuario=None) -> bool:
    """Desactiva un flag y lo persiste en ReglaNegocio."""
    return _set_flag(codigo, empresa, False, usuario)


def _set_flag(codigo: str, empresa, valor: bool, usuario=None) -> bool:
    if codigo not in FLAG_CATALOG:
        return False
    meta = FLAG_CATALOG[codigo]
    try:
        from reglas_negocio.models import ReglaNegocio
        ReglaNegocio.objects.update_or_create(
            codigo=codigo,
            empresa=empresa,
            defaults={
                'nombre': meta['nombre'],
                'descripcion': meta['descripcion'],
                'categoria': meta['categoria'],
                'tipo': 'AUTOMATICA',
                'activa': valor,
                'modificado_por': usuario,
            }
        )
        _invalidate(getattr(empresa, 'id', None))
        logger.info(f'[FeatureFlags] {codigo}={valor} | empresa={empresa} | user={usuario}')
        return True
    except Exception as exc:
        logger.error(f'[FeatureFlags] Error guardando {codigo}: {exc}')
        return False
