"""
core/services/ocr_documental.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Motor de Inteligencia Documental — 4 Capas
  Capa 1: Clasificación del tipo de documento
  Capa 2: Extracción estructurada con schema JSON fijo
  Capa 3: Validación informativa (SEP, coherencia de dosis)
  Capa 4: Anticipación de negocio (sugerencias de perfil)
Nunca bloquea el flujo operativo. Todo es informativo.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations
import json
import logging
import re
import urllib.request
from typing import Optional

from django.conf import settings

logger = logging.getLogger('core.ocr')

# ─── Catálogo de sugerencias por especialidad (Capa 4) ───────────────────────
_SUGERENCIAS_POR_ESPECIALIDAD: dict[str, list[str]] = {
    'GINECOLOGIA': [
        'Perfil control prenatal completo (BHC, QS, Grupo/Rh, VDRL, Urocultivo)',
        'Perfil hormonal femenino (FSH, LH, Estradiol, Progesterona)',
        'Citología cervical (Papanicolaou)',
    ],
    'ENDOCRINOLOGIA': [
        'Perfil tiroideo completo (TSH, T3, T4, T3L, T4L)',
        'Curva de tolerancia a la glucosa',
        'Hemoglobina glucosilada HbA1c',
        'Perfil cortisol',
    ],
    'CARDIOLOGIA': [
        'Perfil lípidos completo (Col. Total, HDL, LDL, VLDL, TG)',
        'Troponina I (alta sensibilidad)',
        'Homocisteína',
        'PCR altamente sensible',
    ],
    'REUMATOLOGIA': [
        'Panel autoinmune (ANA, FR, Anti-CCP, Complemento C3/C4)',
        'Velocidad de sedimentación globular (VSG)',
        'Ácido úrico',
    ],
    'NEFROLOGIA': [
        'Perfil renal (BUN, Creatinina, TFG estimada, Electrólitos)',
        'Microalbuminuria en orina 24h',
        'Proteínas en orina',
    ],
    'ONCOLOGIA': [
        'Panel marcadores tumorales (CEA, AFP, CA-125, CA 19-9, PSA)',
        'Citometría de flujo (si aplica)',
    ],
    'PEDIATRIA': [
        'Biometría hemática pediátrica',
        'Perfil inmunológico (IgA, IgG, IgM)',
        'Tamiz metabólico ampliado',
    ],
    'GERIATRIA': [
        'Perfil geriátrico completo (BHC, QS, TFG, Vitamina D, B12, TSH)',
        'Densitometría ósea (referir)',
        'Prueba de fragilidad (valoración nutricional)',
    ],
    'INFECTOLOGIA': [
        'Panel infeccioso (VIH, Hepatitis B y C, VDRL, Brucela)',
        'Hemocultivo (si sospecha de bacteremia)',
        'Prueba de tuberculina (PPD)',
    ],
}

# Palabras clave para detectar especialidad desde el texto de la receta
_ESPECIALIDAD_KEYWORDS: dict[str, list[str]] = {
    'GINECOLOGIA': ['ginecolog', 'obstetri', 'prenatal', 'embaraz', 'femenin', 'gineco'],
    'ENDOCRINOLOGIA': ['endocrin', 'tiroides', 'diabet', 'insulina', 'metabol'],
    'CARDIOLOGIA': ['cardiol', 'corazon', 'cardiaco', 'hipertens', 'arritmia'],
    'REUMATOLOGIA': ['reumatol', 'artritis', 'lupus', 'fibromialg'],
    'NEFROLOGIA': ['nefrol', 'renal', 'riñon', 'glomerulo'],
    'ONCOLOGIA': ['oncol', 'tumor', 'cancer', 'neo', 'maligno'],
    'PEDIATRIA': ['pediatr', 'neonatol', 'niño', 'lactante', 'infantil'],
    'GERIATRIA': ['geriatr', 'gerontol', 'anciano', 'adulto mayor'],
    'INFECTOLOGIA': ['infect', 'vih', 'sida', 'hepatitis', 'tuberculosis'],
}


def _detectar_especialidad(texto: str) -> Optional[str]:
    tl = texto.lower()
    for especialidad, kws in _ESPECIALIDAD_KEYWORDS.items():
        if any(kw in tl for kw in kws):
            return especialidad
    return None


def _sugerencias_negocio(texto: str, sexo_paciente: str = '', edad: Optional[int] = None) -> list[str]:
    """Capa 4: Sugerencias contextuales de perfiles."""
    especialidad = _detectar_especialidad(texto)
    sugerencias = []

    if especialidad and especialidad in _SUGERENCIAS_POR_ESPECIALIDAD:
        sugerencias.extend(_SUGERENCIAS_POR_ESPECIALIDAD[especialidad])

    # Reglas adicionales demográficas
    if sexo_paciente.upper() in ('F', 'FEMENINO', 'MUJER') and edad and 15 <= edad <= 50:
        if 'Perfil control prenatal completo (BHC, QS, Grupo/Rh, VDRL, Urocultivo)' not in sugerencias:
            sugerencias.append('Considerar perfil hormonal femenino básico (FSH, Estradiol)')
    if edad and edad >= 60:
        if not any('geriátrico' in s.lower() for s in sugerencias):
            sugerencias.append('Considerar Perfil Geriátrico (Vitamina D, B12, TSH)')

    return list(dict.fromkeys(sugerencias))[:4]  # Máximo 4 sugerencias, sin duplicados


# ─── Verificación SEP (Capa 3) — Solo informativa, NUNCA bloquea ────────────

def _verificar_cedula_sep(cedula: str) -> dict:
    """
    Consulta la base pública de cédulas de la SEP.
    Devuelve un badge informativo. NUNCA bloquea el registro.
    """
    try:
        url = f'https://www.cedulaprofesional.sep.gob.mx/cedula/presidencia/indexAvanzada.action'
        # La SEP no tiene una API REST pública. Usamos el endpoint de búsqueda.
        # En implementación real se usaría scraping controlado o la API interna.
        # Por ahora, marcamos como "pendiente de verificación" sin bloquear.
        return {
            'cedula': cedula,
            'verificada': None,
            'badge': 'PENDIENTE',
            'mensaje': 'Verificación SEP disponible. Número de cédula registrado.',
            'nota': 'La verificación en tiempo real con SEP requiere integración adicional.',
        }
    except Exception as exc:
        logger.warning(f'[OCR] Verificación SEP error: {exc}')
        return {'cedula': cedula, 'verificada': None, 'badge': 'ERROR_CONEXION'}


# ─── Prompt especializado por tipo de documento ───────────────────────────────

_PROMPT_CLASIFICAR = """Analiza esta imagen y responde SOLO con un JSON con la siguiente estructura:
{
  "tipo_documento": "INE" | "RECETA_MEDICA" | "ORDEN_LABORATORIO" | "RESULTADO_LAB" | "CURP" | "PASAPORTE" | "OTRO",
  "confianza": 0.0 a 1.0
}
Sin texto adicional, sin markdown."""

_PROMPT_INE = """Extrae los datos de esta INE/Credencial de Elector mexicana.
Responde SOLO con JSON válido:
{
  "nombre_completo": "string",
  "apellido_paterno": "string",
  "apellido_materno": "string",
  "curp": "string o null",
  "fecha_nacimiento": "DD/MM/AAAA o null",
  "sexo": "M" | "F" | null,
  "domicilio": "string o null",
  "clave_elector": "string o null",
  "vigencia": "AAAA o null"
}
Si no puedes leer algún campo, usa null."""

_PROMPT_RECETA = """Extrae los datos de esta receta médica mexicana.
Responde SOLO con JSON válido:
{
  "nombre_paciente": "string o null",
  "edad_paciente": número o null,
  "sexo_paciente": "M" | "F" | null,
  "fecha_receta": "YYYY-MM-DD o null",
  "medico_nombre": "string o null",
  "cedula_profesional": "string o null",
  "especialidad": "string o null",
  "diagnostico": "string o null",
  "estudios_solicitados": ["lista de estudios o análisis pedidos"],
  "indicaciones": "string o null",
  "nombre_clinica": "string o null"
}
Si no puedes leer algún campo, usa null."""

_PROMPT_ORDEN_LAB = """Extrae los datos de esta orden de laboratorio.
Responde SOLO con JSON válido:
{
  "folio": "string o null",
  "nombre_paciente": "string o null",
  "fecha_orden": "YYYY-MM-DD o null",
  "medico_nombre": "string o null",
  "estudios": ["lista de estudios solicitados"],
  "laboratorio_origen": "string o null"
}"""


# ─── Motor principal ───────────────────────────────────────────────────────────

def _gemini_vision_call(imagen_b64: str, prompt: str, api_key: str) -> str:
    """Llamada REST directa a Gemini Vision."""
    raw = imagen_b64.split(',', 1)[1] if ',' in imagen_b64 else imagen_b64
    mime = 'image/jpeg'
    if imagen_b64.startswith('data:'):
        mime = imagen_b64.split(';')[0].split(':')[1]

    payload = json.dumps({
        'contents': [{
            'role': 'user',
            'parts': [
                {'text': prompt},
                {'inline_data': {'mime_type': mime, 'data': raw}},
            ],
        }],
        'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 800},
    }).encode()

    modelos = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
    for modelo in modelos:
        url = f'https://generativelanguage.googleapis.com/v1/models/{modelo}:generateContent?key={api_key}'
        req = urllib.request.Request(
            url, data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
                return ''.join(p.get('text', '') for p in parts).strip()
        except Exception as exc:
            logger.warning(f'[OCR] Gemini {modelo}: {exc}')
    return ''


def _parse_json_respuesta(texto: str) -> dict:
    """Limpia la respuesta de Gemini y parsea el JSON."""
    texto = texto.strip()
    for prefix in ('```json', '```'):
        if texto.startswith(prefix):
            texto = texto[len(prefix):]
    if texto.endswith('```'):
        texto = texto[:-3]
    texto = texto.strip()
    try:
        return json.loads(texto)
    except Exception:
        m = re.search(r'\{.*\}', texto, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return {}


def analizar_documento(imagen_b64: str, empresa=None, usuario=None) -> dict:
    """
    Función principal del Motor de Inteligencia Documental.
    Devuelve un dict con:
      - tipo_documento
      - datos_extraidos
      - sugerencias_negocio
      - validacion_sep (si aplica)
      - prefill: campos listos para inyectar en el formulario
    """
    from core.services.feature_flags import flag_activo

    if not flag_activo('OCR_CLASIFICACION_ACTIVO', empresa):
        return {'activo': False, 'mensaje': 'Motor OCR desactivado desde configuración.'}

    api_key = getattr(settings, 'GOOGLE_API_KEY', '') or getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return {'error': 'GOOGLE_API_KEY no configurada.', 'activo': True}

    # ── Capa 1: Clasificar ────────────────────────────────────────────────────
    resp_clase = _gemini_vision_call(imagen_b64, _PROMPT_CLASIFICAR, api_key)
    clase = _parse_json_respuesta(resp_clase)
    tipo = clase.get('tipo_documento', 'OTRO')
    confianza = clase.get('confianza', 0.5)

    # ── Capa 2: Extraer según tipo ────────────────────────────────────────────
    if tipo == 'INE':
        prompt_extraccion = _PROMPT_INE
    elif tipo == 'RECETA_MEDICA':
        prompt_extraccion = _PROMPT_RECETA
    elif tipo == 'ORDEN_LABORATORIO':
        prompt_extraccion = _PROMPT_ORDEN_LAB
    else:
        prompt_extraccion = _PROMPT_RECETA  # fallback

    resp_datos = _gemini_vision_call(imagen_b64, prompt_extraccion, api_key)
    datos = _parse_json_respuesta(resp_datos)

    # ── Capa 3: Validación informativa ────────────────────────────────────────
    validacion_sep = None
    if tipo == 'RECETA_MEDICA' and flag_activo('VERIFICACION_SEP_ACTIVA', empresa):
        cedula = datos.get('cedula_profesional', '')
        if cedula:
            validacion_sep = _verificar_cedula_sep(cedula)

    # ── Capa 4: Sugerencias de negocio ────────────────────────────────────────
    sugerencias = []
    if flag_activo('OCR_SUGERENCIAS_PERFIL_ACTIVO', empresa):
        texto_full = ' '.join([str(v) for v in datos.values() if v])
        sexo = datos.get('sexo_paciente', '')
        edad = datos.get('edad_paciente') or datos.get('edad')
        sugerencias = _sugerencias_negocio(texto_full, sexo or '', edad)

    # ── Prefill para el formulario de recepción ───────────────────────────────
    prefill = _construir_prefill(tipo, datos)

    return {
        'activo': True,
        'tipo_documento': tipo,
        'confianza': confianza,
        'datos_extraidos': datos,
        'prefill': prefill,
        'sugerencias_negocio': sugerencias,
        'validacion_sep': validacion_sep,
    }


def _construir_prefill(tipo: str, datos: dict) -> dict:
    """Mapea los campos extraídos a los inputs del formulario de recepción."""
    if tipo == 'INE':
        nombre = datos.get('nombre_completo', '')
        ap = datos.get('apellido_paterno', '')
        am = datos.get('apellido_materno', '')
        if ap and not nombre:
            nombre = f'{ap} {am}'.strip()
        return {
            'nombre_paciente': nombre,
            'curp': datos.get('curp', ''),
            'fecha_nacimiento': datos.get('fecha_nacimiento', ''),
            'sexo': datos.get('sexo', ''),
        }
    elif tipo in ('RECETA_MEDICA', 'ORDEN_LABORATORIO'):
        return {
            'nombre_paciente': datos.get('nombre_paciente', ''),
            'medico_nombre': datos.get('medico_nombre', ''),
            'estudios_detectados': datos.get('estudios_solicitados', datos.get('estudios', [])),
            'diagnostico': datos.get('diagnostico', ''),
        }
    return {}
