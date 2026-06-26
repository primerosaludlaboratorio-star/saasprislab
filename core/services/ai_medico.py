"""
PRISLAB V5.0 - SERVICIO DE INTELIGENCIA ARTIFICIAL MÉDICA
=========================================================
Fecha: 1 de Febrero de 2026
Objetivo: Integración con Google Gemini 1.5 Flash para procesamiento de audio médico

CARACTERÍSTICAS:
✅ Conexión con Google Gemini 1.5 Flash
✅ Prompts médicos especializados
✅ Procesamiento de audio a texto estructurado
✅ Validación y limpieza de datos
✅ Manejo robusto de errores
✅ Logging detallado

CASOS DE USO:
1. Consulta Médica: Extraer motivo, signos vitales, diagnóstico, tratamiento
2. Resultados de Laboratorio: Mapear valores dictados a parámetros
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile

# Importar Google Generative AI (SDK unificado google.genai)
try:
    from google import genai as _genai_sdk
    GEMINI_AVAILABLE = True
except ImportError:
    _genai_sdk = None
    GEMINI_AVAILABLE = False
    logging.warning("google-genai no está instalado. Instalarlo con: pip install google-genai")

from django.conf import settings

logger = logging.getLogger('ia')


# ==============================================================================
# UTILIDADES DE ERROR
# ==============================================================================

def _es_error_403(exc: Exception) -> bool:
    texto = f"{type(exc).__name__}: {exc}".lower()
    return any(token in texto for token in ('403', 'forbidden', 'permission denied', 'permissiondenied', 'insufficient permissions'))


def _mensaje_403_gemini(exc: Exception) -> str:
    return (
        "Gemini devolvió un error de permisos (403/Forbidden). "
        "Verifica que la API key esté permitida para generativelanguage.googleapis.com "
        "y que el proyecto tenga acceso activo al modelo. "
        f"Detalle técnico: {type(exc).__name__}: {exc}"
    )


# ==============================================================================
# CONFIGURACIÓN DE GEMINI
# ==============================================================================

def configurar_gemini():
    """
    Verifica que la API key de Gemini esté disponible.

    Returns:
        bool: True si está configurada correctamente, False si hay error
    """
    if not GEMINI_AVAILABLE:
        logger.error("google-genai no está disponible. Instalar con: pip install google-genai")
        return False
    try:
        from core.utils.gemini_client import _get_api_key
        api_key = _get_api_key()
        if not api_key:
            logger.error("GOOGLE_API_KEY no está configurada en settings o variables de entorno")
            return False
        logger.info("Google Gemini disponible")
        return True
    except Exception as e:
        logger.error("Error al verificar Gemini: %s", e, exc_info=True)
        return False


# ==============================================================================
# FUNCIÓN 1: PROCESAR CONSULTA MÉDICA
# ==============================================================================

def procesar_consulta_medica(audio_file) -> Dict[str, Any]:
    """
    Procesa audio de consulta médica y extrae información estructurada.
    
    Args:
        audio_file: Archivo de audio (File object o ruta)
        
    Returns:
        dict: Datos estructurados de la consulta
        {
            'motivo': str,
            'signos_vitales': {
                'temperatura': float,
                'frecuencia_cardiaca': int,
                'presion_arterial': str,
                'peso': float,
                'talla': float
            },
            'diagnostico': str,
            'tratamiento': str,
            'exploracion_fisica': str
        }
        
    Raises:
        Exception: Si hay error en el procesamiento
    """
    if not GEMINI_AVAILABLE:
        raise Exception("Google Generative AI no está instalado. Instalar con: pip install google-generativeai")
    
    if not configurar_gemini():
        raise Exception("Error al configurar Google Gemini")
    
    audio_path = None
    try:
        logger.info("Iniciando procesamiento de consulta médica con Gemini")
        
        # Guardar audio temporalmente si es necesario
        audio_path = _guardar_audio_temporal(audio_file)
        
        # Subir archivo a Gemini (nueva API: client.files.upload)
        logger.info("Subiendo archivo de audio: %s", audio_path)
        from core.utils.gemini_client import get_gemini_client
        client = get_gemini_client()
        try:
            with open(audio_path, 'rb') as f:
                audio_file_gemini = client.files.upload(
                    file=f,
                    config={'mime_type': 'audio/webm'},
                )
        except Exception as upload_exc:
            logging.getLogger(__name__).exception("Error inesperado en procesar_consulta_medica (ai_medico.py)")
            if _es_error_403(upload_exc):
                raise PermissionError(_mensaje_403_gemini(upload_exc)) from upload_exc
            raise

        # Prompt especializado para consulta médica
        prompt = """
Eres un asistente médico experto en transcripción y extracción de datos clínicos.

TAREA:
Transcribe el audio de esta consulta médica y extrae la siguiente información en formato JSON ESTRICTO.

FORMATO DE SALIDA (JSON):
{
    "motivo": "Motivo de consulta o síntomas reportados por el paciente",
    "signos_vitales": {
        "temperatura": 36.5,
        "frecuencia_cardiaca": 70,
        "frecuencia_respiratoria": 18,
        "presion_arterial": "120/80",
        "saturacion": 98,
        "peso": 70.0,
        "talla": 1.70
    },
    "exploracion_fisica": "Hallazgos de la exploración física",
    "diagnostico": "Diagnóstico principal",
    "tratamiento": "Indicaciones, medicamentos, dosis, frecuencia, duración"
}

REGLAS CRÍTICAS:
1. Solo incluye información mencionada explícitamente en el audio
2. Si un dato no se menciona, usa null
3. NO inventes información
4. Respeta el formato JSON exacto
5. Para presión arterial: "sistólica/diastólica" (ej: "120/80")
6. Para peso y talla: punto decimal (ej: 1.70)

DEVUELVE SOLO EL JSON, SIN TEXTO ADICIONAL.
"""

        # Generar respuesta con nueva API
        logger.info("Enviando audio a Gemini para análisis...")
        from google.genai import types as _genai_types
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[prompt, audio_file_gemini],
                config=_genai_types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=2000,
                ),
            )
        except Exception as gen_exc:
            logging.getLogger(__name__).exception("Error inesperado en procesar_consulta_medica (ai_medico.py)")
            if _es_error_403(gen_exc):
                raise PermissionError(_mensaje_403_gemini(gen_exc)) from gen_exc
            raise
        
        # Parsear respuesta
        response_text = response.text.strip()
        logger.info(f"Respuesta de Gemini: {response_text[:200]}...")
        
        # Extraer JSON de la respuesta
        data = _extraer_json_de_respuesta(response_text)
        
        # Validar y limpiar datos
        data = _validar_datos_consulta(data)
        
        logger.info("✓ Consulta médica procesada exitosamente")
        return data
        
    except Exception as e:
        logger.error(f"Error al procesar consulta médica: {e}", exc_info=True)
        raise Exception(f"Error al procesar audio médico: {str(e)}")
    finally:
        if audio_path is not None:
            _limpiar_archivo_temporal(audio_path, audio_file)


# ==============================================================================
# FUNCIÓN 2: PROCESAR RESULTADOS DE LABORATORIO
# ==============================================================================

def procesar_resultados_lab(audio_file, lista_parametros: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Procesa audio de dictado de resultados de laboratorio.
    
    Args:
        audio_file: Archivo de audio (File object o ruta)
        lista_parametros: Lista de parámetros disponibles
            [
                {'nombre': 'Glucosa', 'keywords': 'glucosa, azucar, glicemia'},
                {'nombre': 'Hemoglobina', 'keywords': 'hemoglobina, hb, sangre'},
                ...
            ]
        
    Returns:
        dict: Valores mapeados
        {
            'glucosa': 98,
            'hemoglobina': 14.5,
            'leucocitos': 7000,
            ...
        }
        
    Raises:
        Exception: Si hay error en el procesamiento
    """
    if not GEMINI_AVAILABLE:
        raise Exception("google-genai no está instalado. Instalar con: pip install google-genai")

    if not configurar_gemini():
        raise Exception("Error al verificar configuración de Gemini")

    audio_path = None
    try:
        logger.info("Iniciando procesamiento de resultados de laboratorio con Gemini")

        audio_path = _guardar_audio_temporal(audio_file)

        # Subir archivo con nueva API
        logger.info("Subiendo archivo de audio: %s", audio_path)
        from core.utils.gemini_client import get_gemini_client
        client = get_gemini_client()
        try:
            with open(audio_path, 'rb') as f:
                audio_file_gemini = client.files.upload(
                    file=f,
                    config={'mime_type': 'audio/webm'},
                )
        except Exception as upload_exc:
            logging.getLogger(__name__).exception("Error inesperado en procesar_resultados_lab (ai_medico.py)")
            if _es_error_403(upload_exc):
                raise PermissionError(_mensaje_403_gemini(upload_exc)) from upload_exc
            raise

        parametros_info = "\n".join([
            f"- {p['nombre']}: Keywords: {p['keywords']}"
            for p in lista_parametros
        ])

        prompt = f"""
Eres un asistente de laboratorio clínico experto en transcripción de resultados.

PARÁMETROS DISPONIBLES:
{parametros_info}

FORMATO DE SALIDA (JSON):
{{
    "nombre_parametro_en_minusculas": valor_numerico
}}

REGLAS CRÍTICAS:
1. Solo incluye valores mencionados explícitamente
2. Nombre del parámetro en minúsculas sin espacios ni acentos
3. Usa punto decimal para decimales
4. NO inventes valores

DEVUELVE SOLO EL JSON, SIN TEXTO ADICIONAL.
"""

        logger.info("Enviando audio a Gemini para análisis...")
        from google.genai import types as _genai_types
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[prompt, audio_file_gemini],
                config=_genai_types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1500,
                ),
            )
        except Exception as gen_exc:
            logging.getLogger(__name__).exception("Error inesperado en procesar_resultados_lab (ai_medico.py)")
            if _es_error_403(gen_exc):
                raise PermissionError(_mensaje_403_gemini(gen_exc)) from gen_exc
            raise

        response_text = response.text.strip()
        logger.info("Respuesta de Gemini: %s...", response_text[:200])

        data = _extraer_json_de_respuesta(response_text)
        data = _validar_datos_laboratorio(data, lista_parametros)

        logger.info("Resultados de laboratorio procesados: %d valores", len(data))
        return data

    except Exception as e:
        logger.error("Error al procesar resultados de laboratorio: %s", e, exc_info=True)
        raise Exception(f"Error al procesar audio de laboratorio: {str(e)}")
    finally:
        if audio_path is not None:
            _limpiar_archivo_temporal(audio_path, audio_file)


# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def _guardar_audio_temporal(audio_file) -> str:
    """
    Guarda el archivo de audio temporalmente.
    
    Returns:
        str: Ruta del archivo temporal
    """
    # Si ya es una ruta, retornarla
    if isinstance(audio_file, (str, Path)):
        return str(audio_file)
    
    # Si es un archivo Django, guardarlo temporalmente
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.webm')
    
    # Escribir contenido
    for chunk in audio_file.chunks():
        temp_file.write(chunk)
    
    temp_file.close()
    
    logger.info(f"Audio guardado temporalmente en: {temp_file.name}")
    return temp_file.name


def _limpiar_archivo_temporal(audio_path: str, audio_file_original):
    """
    Limpia el archivo temporal si fue creado.
    """
    # Solo limpiar si no era una ruta original
    if not isinstance(audio_file_original, (str, Path)):
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"Archivo temporal eliminado: {audio_path}")
        except Exception as e:
            logger.warning(f"No se pudo eliminar archivo temporal: {e}")


def _extraer_json_de_respuesta(response_text: str) -> Dict[str, Any]:
    """
    Extrae JSON de la respuesta de Gemini.
    
    Args:
        response_text: Texto de respuesta que puede contener JSON
        
    Returns:
        dict: Datos parseados
    """
    # Intentar parsear directamente
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Buscar JSON entre bloques de código
    import re
    
    # Patrón para JSON entre ```json ... ```
    pattern = r'```json\s*(.*?)\s*```'
    match = re.search(pattern, response_text, re.DOTALL)
    
    if match:
        json_text = match.group(1)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass
    
    # Patrón para JSON entre ``` ... ```
    pattern = r'```\s*(.*?)\s*```'
    match = re.search(pattern, response_text, re.DOTALL)
    
    if match:
        json_text = match.group(1)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass
    
    # Buscar cualquier cosa que parezca JSON (entre { y })
    pattern = r'\{.*\}'
    match = re.search(pattern, response_text, re.DOTALL)
    
    if match:
        json_text = match.group(0)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass
    
    # Si llegamos aquí, no se pudo extraer JSON
    raise Exception(f"No se pudo extraer JSON de la respuesta: {response_text[:200]}...")


def _validar_datos_consulta(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida y limpia los datos de consulta médica.
    """
    # Estructura esperada
    estructura_base = {
        'motivo': None,
        'signos_vitales': {
            'temperatura': None,
            'frecuencia_cardiaca': None,
            'frecuencia_respiratoria': None,
            'presion_arterial': None,
            'saturacion': None,
            'peso': None,
            'talla': None
        },
        'exploracion_fisica': None,
        'diagnostico': None,
        'tratamiento': None
    }
    
    # Fusionar con datos recibidos
    resultado = estructura_base.copy()
    
    if 'motivo' in data:
        resultado['motivo'] = data['motivo']
    
    if 'signos_vitales' in data and isinstance(data['signos_vitales'], dict):
        resultado['signos_vitales'].update(data['signos_vitales'])
    
    if 'exploracion_fisica' in data:
        resultado['exploracion_fisica'] = data['exploracion_fisica']
    
    if 'diagnostico' in data:
        resultado['diagnostico'] = data['diagnostico']
    
    if 'tratamiento' in data:
        resultado['tratamiento'] = data['tratamiento']
    
    return resultado


def _validar_datos_laboratorio(data: Dict[str, Any], lista_parametros: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Valida que los datos de laboratorio solo contengan claves válidas.
    """
    # Extraer nombres válidos de parámetros (en minúsculas, sin espacios)
    parametros_validos = set()
    
    for param in lista_parametros:
        # Nombre normalizado
        nombre_norm = param['nombre'].lower().replace(' ', '_').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        parametros_validos.add(nombre_norm)
        
        # También agregar keywords como alternativas
        keywords = param['keywords'].split(',')
        for kw in keywords:
            kw_norm = kw.strip().lower().replace(' ', '_')
            parametros_validos.add(kw_norm)
    
    # Filtrar solo claves válidas
    resultado = {}
    
    for key, value in data.items():
        key_norm = key.lower().replace(' ', '_')
        
        if key_norm in parametros_validos:
            # Convertir a número si es posible
            try:
                resultado[key_norm] = float(value) if '.' in str(value) else int(value)
            except (ValueError, TypeError):
                resultado[key_norm] = value
        else:
            logger.warning(f"Parámetro no válido ignorado: {key}")
    
    return resultado


# ==============================================================================
# FUNCIÓN DE PRUEBA
# ==============================================================================

def test_gemini_connection():
    """
    Prueba la conexión con Google Gemini.
    
    Returns:
        bool: True si la conexión es exitosa
    """
    try:
        # Hacer una prueba simple usando el proveedor central de IA.
        print("Probando conexion con proveedor IA...")
        from core.utils.gemini_client import generate_content

        response_text = generate_content(
            "Responde solo con 'OK' si me entiendes",
            temperature=0.1,
            max_tokens=10,
        )

        print(f"Proveedor IA responde: {response_text}")
        return True
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_gemini_connection (ai_medico.py)")
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    # Prueba de conexión
    print("Probando conexión con Google Gemini...")
    test_gemini_connection()