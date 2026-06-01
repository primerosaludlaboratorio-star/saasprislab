"""
core/utils/pris_audio_vision.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Escudo Legal de Audio y OCR de Visión para PRIS.
Usa VoiceAuditLog (ya en DB — migración 0014) para el sellado
legal de transcripciones con hash SHA-256 + timestamp servidor.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations
import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Optional

from django.utils import timezone

logger = logging.getLogger('core.pris_audio')


# ─── Hash & Sellado ───────────────────────────────────────────────────────────

def generar_hash_digital(contenido: str, timestamp: Optional[str] = None) -> str:
    """
    Hash SHA-256 de la transcripción + timestamp servidor.
    Inmutable: cualquier alteración posterior cambia el hash.
    """
    ts = timestamp or timezone.now().isoformat()
    payload = f'{contenido}|{ts}'
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def sellar_transcripcion(
    transcripcion: str,
    usuario,
    empresa,
    modulo: str = 'PRIS',
    duracion_segundos: Optional[float] = None,
    url_actual: str = '',
    datos_pantalla: Optional[dict] = None,
) -> dict:
    """
    Registra una transcripción en VoiceAuditLog con sellado legal.
    Retorna dict con el id del registro y el hash generado.

    Si AUDIO_SELLADO_LEGAL_ACTIVO está en False, guarda sin hash
    (funciona igual, solo sin blindaje forense).
    """
    from core.services.feature_flags import flag_activo

    ts_servidor = timezone.now()
    sellado_activo = flag_activo('AUDIO_SELLADO_LEGAL_ACTIVO', empresa)

    hash_digital = ''
    if sellado_activo:
        hash_digital = generar_hash_digital(transcripcion, ts_servidor.isoformat())

    try:
        from core.models import VoiceAuditLog
        registro = VoiceAuditLog.objects.create(
            usuario=usuario,
            empresa=empresa,
            timestamp=ts_servidor,
            url_actual=url_actual or f'/pris/{modulo.lower()}/',
            datos_pantalla=datos_pantalla or {},
            transcripcion=transcripcion,
            tipo_comando='DICTADO_PRIS',
            intencion_detectada=modulo,
            parametros_extraidos={'hash_sha256': hash_digital, 'sellado_legal': sellado_activo},
            respuesta_ia='',
            accion_ejecutada='REGISTRO_AUDIO',
            estado='COMPLETADO',
            duracion_segundos=duracion_segundos,
        )
        return {
            'id': registro.id,
            'hash_sha256': hash_digital,
            'timestamp_servidor': ts_servidor.isoformat(),
            'sellado_legal': sellado_activo,
        }
    except Exception as exc:
        logger.error(f'[PrisAudio] Error sellando transcripción: {exc}')
        return {
            'id': None,
            'hash_sha256': hash_digital,
            'timestamp_servidor': ts_servidor.isoformat(),
            'sellado_legal': False,
            'error': str(exc),
        }


def verificar_integridad(registro_id: int) -> dict:
    """
    Dado un VoiceAuditLog.id, verifica que el hash almacenado
    sigue siendo consistente con la transcripción guardada.
    """
    try:
        from core.models import VoiceAuditLog
        registro = VoiceAuditLog.objects.get(pk=registro_id)
        params = registro.parametros_extraidos or {}
        hash_almacenado = params.get('hash_sha256', '')
        if not hash_almacenado:
            return {'valido': None, 'motivo': 'Registro sin sellado legal'}
        ts = registro.timestamp.isoformat()
        hash_calculado = generar_hash_digital(registro.transcripcion, ts)
        es_valido = hash_calculado == hash_almacenado
        return {
            'valido': es_valido,
            'registro_id': registro_id,
            'hash_almacenado': hash_almacenado,
            'hash_calculado': hash_calculado,
            'timestamp': ts,
        }
    except Exception as exc:
        return {'valido': False, 'error': str(exc)}


# ─── Extracción semántica de transcripción ────────────────────────────────────

def extraer_resumen_clinico(transcripcion: str) -> dict:
    """
    Extrae síntomas y diagnósticos de una transcripción usando palabras clave.
    Fallback rápido cuando Gemini no está disponible.
    """
    sintomas_kw = ['dolor', 'fiebre', 'náusea', 'vómito', 'mareo', 'cansancio', 'malestar',
                   'sangrado', 'dificultad', 'inflamación', 'tos', 'disnea']
    diag_kw = ['diagnóstico', 'diagnostico', 'conclusión', 'hallazgo', 'impresión', 'sospecha']

    tl = transcripcion.lower()
    sintomas, diagnosticos = [], []

    for kw in sintomas_kw:
        idx = tl.find(kw)
        if idx >= 0:
            ctx = transcripcion[max(0, idx - 50): min(len(transcripcion), idx + 80)].strip()
            if ctx not in sintomas:
                sintomas.append(ctx)

    for kw in diag_kw:
        idx = tl.find(kw)
        if idx >= 0:
            ctx = transcripcion[max(0, idx - 30): min(len(transcripcion), idx + 200)].strip()
            if ctx not in diagnosticos:
                diagnosticos.append(ctx)

    return {
        'sintomas': ' | '.join(sintomas[:5]),
        'diagnosticos': ' | '.join(diagnosticos[:3]),
    }


def procesar_dictado_resultado(transcripcion: str, detalle_orden=None) -> dict:
    """
    Mapea una transcripción de dictado a los parámetros de un estudio.
    Ejemplo: "glucosa 95, hemoglobina 14.5"
    """
    valores_mapeados = {}
    if detalle_orden and hasattr(detalle_orden, 'estudio') and detalle_orden.estudio:
        try:
            parametros = detalle_orden.estudio.parametros.all()
            for param in parametros:
                nombre = param.nombre.lower()
                if nombre in transcripcion.lower():
                    patron = re.compile(rf'{re.escape(nombre)}[:\s]+([\d.,]+)', re.IGNORECASE)
                    m = patron.search(transcripcion)
                    if m:
                        try:
                            valor = float(m.group(1).replace(',', '.'))
                            valores_mapeados[param.nombre] = {
                                'valor': valor,
                                'unidad': getattr(param, 'unidad', '') or '',
                                'parametro_id': param.id,
                            }
                        except ValueError:
                            pass
        except Exception as exc:
            logger.warning(f'[PrisAudio] procesar_dictado_resultado: {exc}')
    return valores_mapeados


def procesar_dictado_inventario(transcripcion: str, empresa=None, usuario=None) -> dict:
    """
    Extrae cantidades y productos de un dictado de inventario.
    Ejemplo: "5 cajas de amoxicilina y 3 piezas sueltas"
    """
    patron_cajas = re.compile(r'(\d+)\s*(?:cajas?|caja)', re.IGNORECASE)
    patron_piezas = re.compile(r'(\d+)\s*(?:piezas?|pieza|unidades?|unidad)', re.IGNORECASE)
    patron_producto = re.compile(
        r'(?:de|del|la|el)\s+([A-Za-záéíóúüñÁÉÍÓÚÜÑ\s]+?)(?:\s+y|\s+con|\s*$)', re.IGNORECASE
    )

    cantidad_cajas = 0
    cantidad_piezas = 0
    producto_nombre = None

    m = patron_cajas.search(transcripcion)
    if m:
        cantidad_cajas = int(m.group(1))
    m = patron_piezas.search(transcripcion)
    if m:
        cantidad_piezas = int(m.group(1))
    m = patron_producto.search(transcripcion)
    if m:
        producto_nombre = m.group(1).strip()

    return {
        'cantidad_cajas': cantidad_cajas,
        'cantidad_piezas': cantidad_piezas,
        'producto_nombre': producto_nombre,
        'transcripcion': transcripcion,
    }


# ─── Coach de Toma de Muestra ─────────────────────────────────────────────────

def evaluar_protocolo_toma_muestra(transcripcion: str, estudios: list[str], empresa=None) -> dict:
    """
    Evalúa si el analista siguió el protocolo de toma de muestra.
    Retorna un reporte de mejora continua (siempre positivo).
    """
    from core.services.feature_flags import flag_activo
    if not flag_activo('COACH_TOMA_MUESTRA_ACTIVO', empresa):
        return {'activo': False}

    checklist = _cargar_checklist(empresa)
    tl = transcripcion.lower()

    cumplidos = []
    sugerencias = []

    for item in checklist:
        aplica = _item_aplica(item, estudios)
        if not aplica:
            continue

        cumplido = any(kw.lower() in tl for kw in item.get('keywords', []))
        if cumplido:
            cumplidos.append(item['descripcion'])
        else:
            sugerencias.append({
                'punto': item['descripcion'],
                'sugerencia': item.get('sugerencia', f"Considera verificar: {item['descripcion']}"),
                'momento': item.get('momento', ''),
            })

    score = len(cumplidos) / max(len(cumplidos) + len(sugerencias), 1) * 100

    if score >= 90:
        mensaje_global = '¡Excelente protocolo de toma! El procedimiento fue impecable.'
    elif score >= 70:
        mensaje_global = 'Muy buen trabajo. Hay algunos puntos de mejora continua.'
    else:
        mensaje_global = 'Protocolo completado con oportunidades de mejora. ¡Juntos lo reforzamos!'

    return {
        'activo': True,
        'score_porcentaje': round(score, 1),
        'puntos_cumplidos': cumplidos,
        'sugerencias': sugerencias,
        'mensaje_global': mensaje_global,
    }


def _item_aplica(item: dict, estudios: list[str]) -> bool:
    aplica_si = item.get('aplica_si', 'SIEMPRE')
    if aplica_si == 'SIEMPRE':
        return True
    if isinstance(aplica_si, list):
        estudios_upper = [e.upper() for e in estudios]
        return any(kw.upper() in estudios_upper for kw in aplica_si)
    return False


def _cargar_checklist(empresa=None) -> list[dict]:
    """Carga el checklist desde reglas_negocio o usa el default ISO."""
    try:
        from reglas_negocio.models import ReglaNegocio
        qs = ReglaNegocio.objects.filter(codigo='CHECKLIST_TOMA_MUESTRA')
        if empresa:
            qs = qs.filter(empresa=empresa)
        regla = qs.first()
        if regla and regla.parametros:
            items = regla.parametros.get('items', [])
            if items:
                return items
    except Exception:
        pass
    return _CHECKLIST_DEFAULT


_CHECKLIST_DEFAULT = [
    {
        'descripcion': 'Verificar identidad del paciente con 2 datos',
        'keywords': ['nombre', 'identidad', 'identificación', 'paciente', 'confirmo', 'verifiqué'],
        'aplica_si': 'SIEMPRE',
        'momento': 'INICIO',
        'sugerencia': 'Al inicio de cada toma, confirma nombre completo y fecha de nacimiento del paciente.',
    },
    {
        'descripcion': 'Preguntar por ayuno (para estudios metabólicos)',
        'keywords': ['ayuno', 'comió', 'comio', 'última comida', 'hora', 'horas en ayuno'],
        'aplica_si': ['QS', 'GLUCOSA', 'QUIMICA', 'COLESTEROL', 'TRIGLICERIDOS', 'LIPIDOS', 'INSULINA'],
        'momento': 'ANTES_VENOPUNCION',
        'sugerencia': 'Para estudios metabólicos, verifica el tiempo de ayuno antes de proceder.',
    },
    {
        'descripcion': 'Confirmar orden correcta de tubos',
        'keywords': ['citrato', 'tubo azul', 'tubo rojo', 'tubo lila', 'tubo morado', 'orden de tubos'],
        'aplica_si': ['COAGULACION', 'TP', 'TTP', 'INR', 'FIBRINOGENO'],
        'momento': 'ANTES_VENOPUNCION',
        'sugerencia': 'Para coagulación, el tubo de citrato debe llenarse antes que los demás.',
    },
    {
        'descripcion': 'Registrar hora de toma de muestra',
        'keywords': ['hora', 'hora de toma', 'am', 'pm', 'registré', 'anote'],
        'aplica_si': 'SIEMPRE',
        'momento': 'POST_TOMA',
        'sugerencia': 'Registrar la hora exacta de toma es clave para la trazabilidad del proceso.',
    },
    {
        'descripcion': 'Verificar etiquetado correcto del tubo',
        'keywords': ['etiqueta', 'folio', 'etiquetado', 'código de barras'],
        'aplica_si': 'SIEMPRE',
        'momento': 'POST_TOMA',
        'sugerencia': 'Confirma que la etiqueta tiene el folio correcto antes de enviar al laboratorio.',
    },
]
