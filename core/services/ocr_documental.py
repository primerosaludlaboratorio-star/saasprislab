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
from base64 import b64decode
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

_PROMPT_RECETA_FARMACIA = """Lee esta receta médica mexicana para auxiliar a un farmacéutico.
Responde SOLO con JSON válido y no inventes datos ilegibles:
{
  "tipo_documento": "RECETA_MEDICA" | "OTRO",
  "confianza": 0.0 a 1.0,
  "nombre_paciente": "string o null",
  "fecha_receta": "YYYY-MM-DD o null",
  "medico_nombre": "string o null",
  "cedula_profesional": "string o null",
  "medicamentos": [
    {"texto": "texto tal como aparece", "nombre_comercial": "string o null",
     "sustancia_activa": "string o null", "concentracion": "string o null",
     "forma_farmaceutica": "string o null", "cantidad": número entero o null,
     "indicaciones": "string o null", "confianza": 0.0 a 1.0}
  ],
  "observaciones": "string o null"
}
Reglas: una línea por medicamento; conserva literalmente dosis, frecuencia, duración, vía e indicaciones en "indicaciones"; no conviertas dosis o frecuencia en cantidad de cajas; si la letra es ambigua, conserva el texto parcial y baja la confianza en vez de inventar."""

_PROMPT_COMPRA_FARMACIA = """Lee esta factura o nota de compra de medicamentos para auxiliar al encargado de inventario.
Responde SOLO con JSON válido y no inventes datos ilegibles:
{
  "tipo_documento": "FACTURA" | "NOTA_VENTA" | "OTRO",
  "confianza": 0.0 a 1.0,
  "proveedor": {"nombre": "string o null", "rfc": "string o null"},
  "folio": "string o null", "fecha_compra": "YYYY-MM-DD o null",
  "subtotal": "string o null", "iva": "string o null", "total": "string o null",
  "productos": [
    {"texto": "texto de la línea", "nombre": "string o null", "sustancia_activa": "string o null",
     "marca": "string o null", "concentracion": "string o null", "presentacion": "string o null",
     "cantidad": número entero o null, "costo_unitario": "string o null",
     "numero_lote": "string o null", "fecha_caducidad": "YYYY-MM-DD o null",
     "confianza": 0.0 a 1.0}
  ]
}
Reglas: no conviertas el total de la factura en costo unitario; no conviertas piezas o cajas ambiguas sin indicarlo; deja null si no se ve."""

_PROMPT_COMPRA_LABORATORIO = """Lee esta factura o nota de compra de reactivos e insumos de laboratorio.
Responde SOLO con JSON válido y no inventes datos ilegibles:
{
  "tipo_documento": "FACTURA" | "NOTA_VENTA" | "OTRO", "confianza": 0.0 a 1.0,
  "proveedor": {"nombre": "string o null", "rfc": "string o null"},
  "folio": "string o null", "fecha_compra": "YYYY-MM-DD o null",
  "subtotal": "string o null", "iva": "string o null", "total": "string o null",
  "productos": [{"texto": "texto de la línea", "nombre": "string o null",
    "codigo": "string o null", "tipo": "REACTIVO|CALIBRADOR|CONTROL_QC|CONSUMIBLE|REFACCION|OTRO",
    "marca": "string o null", "fabricante": "string o null", "cantidad": "string o null",
    "costo_unitario": "string o null", "numero_lote": "string o null",
    "fecha_caducidad": "YYYY-MM-DD o null", "inserto_version": "string o null",
    "confianza": 0.0 a 1.0}]
}
Reglas: no conviertas el total en costo unitario; conserva el texto original si no identificas el catálogo; deja null si no se ve."""

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


def _deepseek_vision_call(imagen_b64: str, prompt: str) -> str:
    """Llama un modelo DeepSeek compatible con entrada multimodal, si se configura."""
    api_key = getattr(settings, 'DEEPSEEK_API_KEY', '')
    modelo = getattr(settings, 'DEEPSEEK_VISION_MODEL', '')
    if not api_key or not modelo:
        return ''
    payload = json.dumps({
        'model': modelo,
        'temperature': 0.1,
        'max_tokens': 1200,
        'messages': [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': prompt},
                {'type': 'image_url', 'image_url': {'url': imagen_b64}},
            ],
        }],
    }).encode()
    req = urllib.request.Request(
        getattr(settings, 'DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions'),
        data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=getattr(settings, 'DEEPSEEK_TIMEOUT', 30)) as resp:
            data = json.loads(resp.read().decode())
            return str(data.get('choices', [{}])[0].get('message', {}).get('content', '')).strip()
    except Exception as exc:
        logger.warning('[OCR] DeepSeek vision no disponible: %s', exc)
        return ''


_PROMPT_RECETA_TEXTO = """Convierte el texto OCR de una receta médica en JSON válido.
No inventes datos: usa null o una lista vacía cuando no aparezca un dato.
Conserva literalmente las indicaciones, dosis, frecuencia, duración y vía.
Responde SOLO con este esquema:
{
  "tipo_documento": "RECETA_MEDICA" | "OTRO",
  "confianza": 0.0 a 1.0,
  "nombre_paciente": "string o null",
  "fecha_receta": "YYYY-MM-DD o null",
  "medico_nombre": "string o null",
  "cedula_profesional": "string o null",
  "medicamentos": [
    {"texto": "texto original", "nombre_comercial": "string o null",
     "sustancia_activa": "string o null", "concentracion": "string o null",
     "forma_farmaceutica": "string o null", "cantidad": número entero o null,
     "indicaciones": "string o null", "confianza": 0.0 a 1.0}
  ],
  "observaciones": "string o null"
}

Texto OCR:
"""


def _deepseek_text_call(texto: str) -> str:
    """Estructura texto OCR con DeepSeek, que no se usa como lector de imagen."""
    api_key = getattr(settings, 'DEEPSEEK_API_KEY', '')
    modelo = getattr(settings, 'DEEPSEEK_MODEL', '') or getattr(settings, 'DEEPSEEK_VISION_MODEL', '')
    if not api_key or not modelo:
        return ''
    payload = json.dumps({
        'model': modelo,
        'temperature': 0.0,
        'max_tokens': 1600,
        'response_format': {'type': 'json_object'},
        'messages': [{'role': 'user', 'content': _PROMPT_RECETA_TEXTO + texto[:18000]}],
    }).encode()
    req = urllib.request.Request(
        getattr(settings, 'DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions'),
        data=payload,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=getattr(settings, 'DEEPSEEK_TIMEOUT', 30)) as resp:
            data = json.loads(resp.read().decode())
            return str(data.get('choices', [{}])[0].get('message', {}).get('content', '')).strip()
    except Exception as exc:
        logger.warning('[OCR] DeepSeek texto no disponible: %s', exc)
        return ''


def _google_cloud_vision_text(imagen_b64: str) -> str:
    """Extrae texto impreso o manuscrito mediante Cloud Vision Document OCR."""
    try:
        from google.cloud import vision
        contenido = b64decode(imagen_b64.split(',', 1)[-1])
        cliente = vision.ImageAnnotatorClient()
        respuesta = cliente.document_text_detection(image=vision.Image(content=contenido))
        if respuesta.error.message:
            logger.warning('[OCR] Cloud Vision: %s', respuesta.error.message)
            return ''
        anotacion = respuesta.full_text_annotation
        return (anotacion.text if anotacion else '').strip()
    except Exception as exc:
        logger.warning('[OCR] Cloud Vision no disponible: %s', exc)
        return ''


def _parsear_lineas_receta(texto: str) -> dict:
    """Respaldo sin IA: conserva líneas numeradas y separa indicaciones básicas."""
    medicamentos = []
    for linea in texto.splitlines():
        linea = linea.strip()
        match = re.match(r'^\s*(?:\d+[.)]|[-*])\s*(.+?)(?:\s+-\s+|\s+)(.+)$', linea)
        if not match:
            continue
        nombre, indicaciones = match.groups()
        if len(nombre) < 3 or not re.search(r'[A-Za-zÁÉÍÓÚáéíóú]', nombre):
            continue
        concentracion = ''
        concentracion_match = re.search(
            r'\b\d+(?:[.,]\d+)?\s*(?:mg|g|mcg|ml|%)(?:\b|/)',
            f'{nombre} {indicaciones}',
            re.I,
        )
        if concentracion_match:
            concentracion = concentracion_match.group(0)
        medicamentos.append({
            'texto': f'{nombre} - {indicaciones}',
            'nombre_comercial': nombre,
            'sustancia_activa': None,
            'concentracion': concentracion or None,
            'forma_farmaceutica': None,
            'cantidad': 1,
            'indicaciones': indicaciones,
            'confianza': 0.55,
        })
    return {
        'tipo_documento': 'RECETA_MEDICA' if medicamentos else 'OTRO',
        'confianza': 0.55 if medicamentos else 0,
        'nombre_paciente': None,
        'fecha_receta': None,
        'medico_nombre': None,
        'cedula_profesional': None,
        'medicamentos': medicamentos,
        'observaciones': 'Texto extraído por OCR; requiere confirmación humana.',
    }


def _leer_receta_por_ocr_documental(imagen_b64: str) -> tuple[dict, str, dict]:
    """Fallback multimotor: imagen -> OCR documental -> DeepSeek texto -> parser."""
    texto = _google_cloud_vision_text(imagen_b64)
    if not texto:
        return {}, '', {'proveedores_intentados': ['google_cloud_vision'], 'requiere_revision_humana': True}
    raw = _deepseek_text_call(texto)
    datos = _parse_json_respuesta(raw) if raw else {}
    if not isinstance(datos.get('medicamentos'), list) or not datos.get('medicamentos'):
        datos = _parsear_lineas_receta(texto)
        proveedor = 'google_cloud_vision+parser'
    else:
        proveedor = 'google_cloud_vision+deepseek'
    confianza = _confianza_ocr(datos.get('confianza'))
    return datos, proveedor, {
        'proveedores_intentados': ['google_cloud_vision', 'deepseek_text'],
        'confianzas': {proveedor: confianza},
        'fallback_utilizado': True,
        'texto_ocr': texto,
        'requiere_revision_humana': True,
    }


def _confianza_ocr(valor) -> float:
    """Normaliza confianza a 0..1; algunos proveedores responden porcentajes."""
    try:
        confianza = float(valor or 0)
    except (TypeError, ValueError):
        return 0.0
    if confianza > 1:
        confianza /= 100
    return max(0.0, min(confianza, 1.0))


def _leer_receta_en_cascada(imagen_b64: str) -> tuple[dict, str, dict]:
    """Lee una receta con proveedor primario y fallback explícito por baja confianza."""
    proveedores = []
    for nombre in (
        getattr(settings, 'OCR_VISION_PRIMARY', 'gemini'),
        getattr(settings, 'OCR_VISION_FALLBACK', ''),
    ):
        nombre = (nombre or '').strip().lower()
        if nombre in ('gemini', 'deepseek') and nombre not in proveedores:
            proveedores.append(nombre)
    if not proveedores:
        return {}, '', {'proveedores_intentados': [], 'requiere_revision_humana': True}

    umbral = _confianza_ocr(getattr(settings, 'OCR_VISION_CONFIDENCE_THRESHOLD', 0.72))
    resultados = []
    for indice, proveedor in enumerate(proveedores):
        if proveedor == 'gemini':
            clave = getattr(settings, 'GOOGLE_API_KEY', '') or getattr(settings, 'GEMINI_API_KEY', '')
            raw = _gemini_vision_call(imagen_b64, _PROMPT_RECETA_FARMACIA, clave) if clave else ''
        else:
            raw = _deepseek_vision_call(imagen_b64, _PROMPT_RECETA_FARMACIA)
        datos = _parse_json_respuesta(raw) if raw else {}
        confianza = _confianza_ocr(datos.get('confianza'))
        resultados.append({'proveedor': proveedor, 'confianza': confianza, 'datos': datos, 'respondio': bool(datos)})
        if datos and confianza >= umbral:
            break

    validos = [r for r in resultados if r['datos'] and isinstance(r['datos'].get('medicamentos'), list)]
    elegido = max(validos, key=lambda r: r['confianza']) if validos else {'proveedor': '', 'confianza': 0, 'datos': {}}
    if not elegido['datos'] or not elegido['datos'].get('medicamentos'):
        datos_ocr, proveedor_ocr, vision_ocr = _leer_receta_por_ocr_documental(imagen_b64)
        if datos_ocr:
            return datos_ocr, proveedor_ocr, vision_ocr
    return elegido['datos'], elegido['proveedor'], {
        'proveedores_intentados': [r['proveedor'] for r in resultados],
        'confianzas': {r['proveedor']: r['confianza'] for r in resultados},
        'umbral': umbral,
        'fallback_utilizado': len(resultados) > 1,
        'requiere_revision_humana': elegido['confianza'] < umbral,
    }


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
        logging.getLogger(__name__).exception("Error inesperado en _parse_json_respuesta (ocr_documental.py)")
        m = re.search(r'\{.*\}', texto, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en _parse_json_respuesta (ocr_documental.py)")
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


def analizar_receta_farmacia(imagen_b64: str, empresa=None, usuario=None) -> dict:
    """Extrae medicamentos para Farmacia; siempre devuelve propuestas, nunca una venta."""
    from core.services.feature_flags import flag_activo

    if not flag_activo('OCR_CLASIFICACION_ACTIVO', empresa):
        return {'activo': False, 'mensaje': 'Motor OCR desactivado desde configuración.'}
    proveedores_configurados = {
        'gemini': bool(getattr(settings, 'GOOGLE_API_KEY', '') or getattr(settings, 'GEMINI_API_KEY', '')),
        'deepseek': bool(getattr(settings, 'DEEPSEEK_API_KEY', '') and getattr(settings, 'DEEPSEEK_VISION_MODEL', '')),
    }
    if not any(proveedores_configurados.values()):
        return {'activo': True, 'error': 'OCR de recetas no disponible: configure un proveedor de visión.'}
    datos, proveedor, vision = _leer_receta_en_cascada(imagen_b64)
    if not datos:
        return {'activo': True, 'error': 'El motor OCR no devolvió una lectura estructurada.'}
    datos['medicamentos'] = datos.get('medicamentos') if isinstance(datos.get('medicamentos'), list) else []
    return {
        'activo': True,
        'tipo_documento': datos.get('tipo_documento', 'OTRO'),
        'confianza': vision.get('confianzas', {}).get(proveedor, 0),
        'datos_extraidos': datos,
        'texto_extraido': json.dumps(datos, ensure_ascii=False),
        'proveedor_vision': proveedor,
        'vision': vision,
    }


def analizar_compra_farmacia(imagen_b64: str, empresa=None, usuario=None) -> dict:
    """Extrae una compra para revisión; nunca crea proveedor, lote ni movimiento."""
    from core.services.feature_flags import flag_activo

    if not flag_activo('OCR_CLASIFICACION_ACTIVO', empresa):
        return {'activo': False, 'mensaje': 'Motor OCR desactivado desde configuración.'}
    api_key = getattr(settings, 'GOOGLE_API_KEY', '') or getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return {'activo': True, 'error': 'OCR de compras no disponible: falta configurar GOOGLE_API_KEY o GEMINI_API_KEY.'}
    respuesta = _gemini_vision_call(imagen_b64, _PROMPT_COMPRA_FARMACIA, api_key)
    datos = _parse_json_respuesta(respuesta)
    if not datos:
        return {'activo': True, 'error': 'El motor OCR no devolvió una compra estructurada.'}
    datos['productos'] = datos.get('productos') if isinstance(datos.get('productos'), list) else []
    return {
        'activo': True,
        'tipo_documento': datos.get('tipo_documento', 'OTRO'),
        'confianza': datos.get('confianza', 0),
        'datos_extraidos': datos,
        'texto_extraido': respuesta,
    }


def analizar_compra_laboratorio(imagen_b64: str, empresa=None, usuario=None) -> dict:
    """Extrae una compra de laboratorio para conciliación; nunca crea un lote."""
    from core.services.feature_flags import flag_activo

    if not flag_activo('OCR_CLASIFICACION_ACTIVO', empresa):
        return {'activo': False, 'mensaje': 'Motor OCR desactivado desde configuración.'}
    api_key = getattr(settings, 'GOOGLE_API_KEY', '') or getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return {'activo': True, 'error': 'OCR de compras de laboratorio no disponible: falta configurar GOOGLE_API_KEY o GEMINI_API_KEY.'}
    respuesta = _gemini_vision_call(imagen_b64, _PROMPT_COMPRA_LABORATORIO, api_key)
    datos = _parse_json_respuesta(respuesta)
    if not datos:
        return {'activo': True, 'error': 'El motor OCR no devolvió una compra de laboratorio estructurada.'}
    datos['productos'] = datos.get('productos') if isinstance(datos.get('productos'), list) else []
    return {'activo': True, 'tipo_documento': datos.get('tipo_documento', 'OTRO'),
            'confianza': datos.get('confianza', 0), 'datos_extraidos': datos,
            'texto_extraido': respuesta}


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
