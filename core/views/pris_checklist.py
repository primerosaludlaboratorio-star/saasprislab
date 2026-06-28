"""
PRIS — Motor de Escucha Activa para Cubículo de Flebotomía
===========================================================
Detecta en tiempo real si el protocolo de bioseguridad se cumplió
durante la conversación flebotomista-paciente.

Flujo:
  Browser SpeechRecognition → transcript parcial/final →
  POST /pris/api/checklist-nlp/ → intent detection (regex + Gemini) →
  JSON { intents_detectados, confianza } → frontend auto-marca casillas

Dos capas de detección:
  1. Regex rápido (sin costo, sin latencia) — alta precisión en frases comunes
  2. Gemini (solo para transcriptos ambiguos) — costoso, se activa solo en casos borde
"""
import re
import json
import logging
import urllib.request
import urllib.error

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.conf import settings

logger = logging.getLogger('core')

# ─────────────────────────────────────────────────────────────────────────────
# MAPA DE INTENTS — Conversación Flebotomía (español México)
# Cada intent tiene:
#   trigger_patterns  → frases que el flebotomista dice (pregunta al paciente)
#   confirm_patterns  → respuestas positivas del paciente
#   deny_patterns     → respuestas negativas (requieren acción del flebotomista)
#   standalone_ok     → frases que por sí solas confirman el intent
#   pregunta_guia     → sugerencia que aparece en pantalla para el flebotomista
# ─────────────────────────────────────────────────────────────────────────────

INTENTS_MAP = {
    "IDENTIDAD": {
        "label": "Identidad Verificada",
        "pregunta_guia": "\"Confirme por favor su nombre completo y fecha de nacimiento\"",
        "trigger_patterns": [
            r"(cómo\s+se\s+llama|nombre\s+completo|confírme\s+su\s+nombre|cuál\s+es\s+su\s+nombre|me\s+dice\s+su\s+nombre)",
            r"(fecha\s+de\s+nacimiento|cuándo\s+nació|año\s+de\s+nacimiento)",
        ],
        "confirm_patterns": [
            r"(sí[,.]?\s*(eso\s+es|así\s+es|correcto|exacto|yo\s+soy|me\s+llamo))",
            r"(correcto|así\s+es|exactamente|es\s+correcto|datos\s+correctos)",
            r"(me\s+llamo\s+\w+|yo\s+soy\s+\w+|mi\s+nombre\s+es\s+\w+)",
            r"(nací\s+el|mi\s+fecha\s+es|nacimiento\s+es)",
        ],
        "standalone_ok": [
            r"identidad\s+(verificada|confirmada|correcta)",
            r"paciente\s+(identificado|confirmado)",
        ],
        "confianza_base": 0.90,
    },
    "AYUNO": {
        "label": "Ayuno Confirmado",
        "pregunta_guia": "\"¿Viene usted en ayuno? ¿Cuántas horas lleva sin comer?\"",
        "trigger_patterns": [
            r"(viene?\s+en\s+ayuno|está\s+en\s+ayuno|ayuno)",
            r"(cuántas?\s+horas?\s+(lleva|tiene|sin\s+comer)|último\s+alimento|última\s+vez\s+que\s+comió)",
            r"(ha\s+comido|comió\s+algo|tomado\s+agua|tomó\s+café)",
        ],
        "confirm_patterns": [
            r"(sí[,.]?\s*(estoy|llevo|tengo|vine|vengo)\s+en\s+ayuno)",
            r"(llevo\s+\d+\s+horas?)",
            r"(desde\s+(anoche|ayer|las\s+\d+))",
            r"(no\s+(he\s+comido|comí|desayuné|tomé\s+nada))",
            r"(en\s+ayuno\s+de\s+\d+\s+horas?)",
        ],
        "deny_patterns": [
            r"(no[,.]?\s*no\s+estoy\s+en\s+ayuno)",
            r"(comí\s+hace\s+(poco|un\s+rato|unas?\s+horas?))",
            r"(desayuné|almorcé|ya\s+comí)",
        ],
        "standalone_ok": [
            r"ayuno\s+(confirmado|verificado|de\s+\d+\s+horas?)",
        ],
        "confianza_base": 0.88,
    },
    "CONSENTIMIENTO": {
        "label": "Consentimiento Firmado",
        "pregunta_guia": "\"¿Ya firmó el documento de consentimiento que le entregaron?\"",
        "trigger_patterns": [
            r"(firmó\s+el\s+(documento|consentimiento|formato)|ya\s+firmó)",
            r"(consentimiento\s+(informado|firmado))",
        ],
        "confirm_patterns": [
            r"(sí[,.]?\s*(ya\s+firmé|firmé|lo\s+firmé))",
            r"(ya\s+está\s+firmado|lo\s+firmé|está\s+firmado)",
            r"(aquí\s+está|aquí\s+lo\s+tiene)",
        ],
        "standalone_ok": [
            r"consentimiento\s+(firmado|autorizado|completo)",
            r"(ya\s+)?(firmado|firmé)\s+el\s+(consentimiento|formato|documento)",
        ],
        "confianza_base": 0.92,
    },
    "MEDICAMENTOS": {
        "label": "Medicamentos / tratamiento",
        "pregunta_guia": "\"¿Toma medicamentos, anticoagulantes, suplementos o antibióticos recientes?\"",
        "trigger_patterns": [
            r"(toma\s+algún\s+medicamento|está\s+tomando\s+(algún\s+)?medicamento|tiene\s+medicamentos)",
            r"(medicamento[s]?|pastilla[s]?|tableta[s]?|tratamiento\s+médico|anticoagulante|warfarina|aspirina|metformina|insulina)",
            r"(suplemento|vitamina|antibiótico)",
        ],
        "confirm_patterns": [
            r"(sí[,.]?\s*(tomo|estoy\s+tomando|tengo))",
            r"(tomo\s+\w+|estoy\s+en\s+tratamiento)",
            r"(no[,.]?\s*(tomo\s+nada|estoy\s+sin\s+medicamento|sin\s+medicamento))",
            r"(sólo\s+tomo|únicamente\s+tomo)",
        ],
        "standalone_ok": [
            r"medicamentos?\s+(registrados?|anotados?|revisados?)",
            r"(no\s+tomo\s+nada|sin\s+medicamentos?|no\s+estoy\s+tomando)",
            r"sin\s+medicamentos?\s+actuales?",
        ],
        "confianza_base": 0.82,
    },
    "SINTOMAS": {
        "label": "Síntomas / motivo de estudios",
        "pregunta_guia": "\"¿Tiene fiebre, dolor, mareo, debilidad o algún síntoma que debamos anotar para correlación con sus estudios?\"",
        "trigger_patterns": [
            r"(síntoma|se\s+siente|siente|le\s+duele|dolor|fiebre|mareo|náusea|vómito|debilidad)",
            r"(motivo\s+de\s+(sus\s+)?estudios|para\s+qué\s+le\s+hicieron|por\s+qué\s+viene)",
        ],
        "confirm_patterns": [
            r"(sí[,.]?\s*(tengo|me\s+siento|sí\s+tengo))",
            r"(me\s+siento\s+\w+|tengo\s+(fiebre|dolor|mareo))",
            r"(no[,.]?\s*(tengo\s+síntomas|estoy\s+bien|me\s+siento\s+bien))",
            r"(asintomático|sin\s+síntomas)",
        ],
        "standalone_ok": [
            r"síntomas?\s+(registrados?|anotados?|relevantes)",
            r"(sin\s+síntomas|asintomático|control\s+rutinario)",
        ],
        "confianza_base": 0.78,
    },
    "PADECIMIENTOS": {
        "label": "Padecimientos crónicos",
        "pregunta_guia": "\"¿Padece diabetes, hipertensión, problemas de riñón, tiroides u otra condición crónica?\"",
        "trigger_patterns": [
            r"(padece|tiene\s+diagnosticad|enfermedad\s+crónica|condición\s+médica)",
            r"(diabetes|hipertensión|hipotiroidismo|hipertiroidismo|riñón|renal|cardiopatía|epilepsia)",
        ],
        "confirm_patterns": [
            r"(sí[,.]?\s*(tengo\s+diabetes|soy\s+diabético|tengo\s+hipertensión))",
            r"(tengo\s+\w+|me\s+diagnosticaron)",
            r"(no[,.]?\s*(tengo\s+nada|estoy\s+sano|sin\s+padecimientos))",
            r"(no\s+padezco|ninguna\s+enfermedad)",
        ],
        "standalone_ok": [
            r"padecimientos?\s+(registrados?|anotados?)",
            r"(sin\s+antecedentes|sin\s+patología\s+crónica|ninguno)",
        ],
        "confianza_base": 0.78,
    },
}


def _normalizar(texto: str) -> str:
    """Normaliza el texto para la detección: minúsculas, sin tildes extras."""
    import unicodedata
    texto = texto.lower().strip()
    # Preservar tildes relevantes (ó, á, etc.) para mejor matching
    return texto


def _detectar_por_regex(texto_norm: str) -> dict:
    """
    Capa 1: detección rápida por regex.
    Retorna {intent_id: {'confianza': float, 'evidencia': str}} para cada intent detectado.
    """
    detectados = {}

    for intent_id, cfg in INTENTS_MAP.items():
        evidencias = []

        # Verificar standalone_ok (alta confianza sin contexto)
        for pat in cfg.get("standalone_ok", []):
            if re.search(pat, texto_norm, re.IGNORECASE):
                detectados[intent_id] = {
                    'confianza': 0.97,
                    'evidencia': f'standalone: {re.search(pat, texto_norm, re.IGNORECASE).group()}',
                }
                break

        if intent_id in detectados:
            continue

        # Verificar si hay trigger + confirmación (conversación completa)
        trigger_ok = any(re.search(p, texto_norm, re.IGNORECASE) for p in cfg.get("trigger_patterns", []))
        confirm_ok = any(re.search(p, texto_norm, re.IGNORECASE) for p in cfg.get("confirm_patterns", []))

        if trigger_ok and confirm_ok:
            detectados[intent_id] = {
                'confianza': cfg["confianza_base"],
                'evidencia': 'trigger+confirmación detectados',
            }
        elif confirm_ok:
            # Confirmación sin pregunta explícita (ej. paciente dice espontáneamente)
            detectados[intent_id] = {
                'confianza': cfg["confianza_base"] - 0.15,
                'evidencia': 'solo confirmación',
            }

    return detectados


def _detectar_negaciones(texto_norm: str) -> list:
    """Detecta respuestas negativas que requieren atención del flebotomista."""
    alertas = []
    for intent_id, cfg in INTENTS_MAP.items():
        for pat in cfg.get("deny_patterns", []):
            if re.search(pat, texto_norm, re.IGNORECASE):
                alertas.append({
                    'intent': intent_id,
                    'label': cfg['label'],
                    'tipo': 'NEGACION',
                    'mensaje': f"⚠️ Paciente indicó: {re.search(pat, texto_norm, re.IGNORECASE).group()}",
                })
    return alertas


def _detectar_con_gemini(texto: str, intents_pendientes: list) -> dict:
    """
    Capa 2 (opcional): usa Gemini para analizar conversación ambigua.
    Solo se invoca si hay transcripción suficiente (>100 chars) y
    al menos 2 intents pendientes.
    Retorna el mismo formato que _detectar_por_regex.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key or len(texto) < 80:
        return {}

    pendientes_str = "\n".join(
        f'- {INTENTS_MAP[i]["label"]} (ID: {i}): {INTENTS_MAP[i]["pregunta_guia"]}'
        for i in intents_pendientes
        if i in INTENTS_MAP
    )

    prompt = f"""Eres un asistente clínico especializado en protocolos de flebotomía.
Analiza la siguiente transcripción de una conversación entre un flebotomista y un paciente.
Determina si cada protocolo de bioseguridad fue cumplido SOLO basándote en lo que se dice.

TRANSCRIPCIÓN:
{texto[:600]}

PROTOCOLOS PENDIENTES DE VERIFICAR:
{pendientes_str}

Responde ÚNICAMENTE con JSON en este formato exacto, sin texto adicional:
{{
  "detectados": [
    {{"id": "IDENTIDAD", "confianza": 0.85, "evidencia": "el paciente confirmó su nombre"}},
    {{"id": "AYUNO", "confianza": 0.90, "evidencia": "paciente dijo lleva 8 horas"}}
  ]
}}
Si no se detecta ningún protocolo cumplido, responde: {{"detectados": []}}
"""

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-lite:generateContent?key={api_key}"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 300},
    }).encode()

    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=4) as resp:
            raw = json.loads(resp.read().decode())
            texto_resp = raw["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Extraer JSON de la respuesta
            json_match = re.search(r'\{.*\}', texto_resp, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                resultado = {}
                for item in data.get("detectados", []):
                    resultado[item["id"]] = {
                        'confianza': float(item.get("confianza", 0.75)),
                        'evidencia': item.get("evidencia", "Gemini"),
                    }
                return resultado
    except Exception as e:
        logger.warning("Gemini checklist NLP falló: %s", e)

    return {}


# ─────────────────────────────────────────────────────────────────────────────
# VIEW PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def api_detectar_intents_checklist(request):
    """
    Recibe transcript de texto del browser y retorna los intents detectados.

    Request body:
        { "texto": "transcripción...", "orden_id": 123, "usar_gemini": false }

    Response:
        {
            "intents_detectados": ["IDENTIDAD", "AYUNO"],
            "detalles": {"IDENTIDAD": {"confianza": 0.90, "evidencia": "..."}},
            "alertas": [{"intent": "AYUNO", "tipo": "NEGACION", "mensaje": "..."}],
            "total_detectados": 2,
        }
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    texto_raw = data.get('texto', '').strip()
    if not texto_raw:
        return JsonResponse({'intents_detectados': [], 'detalles': {}, 'alertas': []})

    usar_gemini = data.get('usar_gemini', False)
    texto_norm = _normalizar(texto_raw)

    # ── Capa 1: detección por regex ──────────────────────────────────────
    detectados = _detectar_por_regex(texto_norm)

    # ── Capa 2: Gemini para intents pendientes (si se solicita) ──────────
    if usar_gemini and len(texto_norm) > 100:
        todos_intents = list(INTENTS_MAP.keys())
        pendientes = [i for i in todos_intents if i not in detectados]
        if pendientes:
            gemini_result = _detectar_con_gemini(texto_raw, pendientes)
            for intent_id, info in gemini_result.items():
                if intent_id not in detectados:
                    detectados[intent_id] = {**info, 'fuente': 'gemini'}

    # ── Negaciones / alertas ──────────────────────────────────────────────
    alertas = _detectar_negaciones(texto_norm)

    # ── Filtrar por umbral mínimo de confianza ────────────────────────────
    UMBRAL_CONFIANZA = 0.65
    detectados_filtrados = {
        k: v for k, v in detectados.items()
        if v.get('confianza', 0) >= UMBRAL_CONFIANZA
    }

    logger.info(
        "ChecklistNLP orden=%s detectados=%s alertas=%d",
        data.get('orden_id', '?'),
        list(detectados_filtrados.keys()),
        len(alertas),
    )

    return JsonResponse({
        'intents_detectados': list(detectados_filtrados.keys()),
        'detalles': detectados_filtrados,
        'alertas': alertas,
        'total_detectados': len(detectados_filtrados),
        'texto_procesado': texto_raw[:200],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Exportar preguntas guía para el frontend (inicialización de la consola)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def api_guia_preguntas(request):
    """Retorna el mapa de intents con sus preguntas guía para el frontend."""
    return JsonResponse({
        'intents': {
            k: {'label': v['label'], 'pregunta_guia': v['pregunta_guia']}
            for k, v in INTENTS_MAP.items()
        }
    })
