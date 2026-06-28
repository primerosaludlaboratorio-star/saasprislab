"""
PRIS SENTINEL - Servicio de Análisis Inteligente de Incidencias (v3 — Autocuración SSH)
========================================================================================
Usa Gemini para traducir tracebacks técnicos en reportes ejecutivos
legibles por el Director y bloques de contexto exportables para Cursor.

v3: Genera contexto_reparacion (JSON) con archivo, línea, código propuesto,
instrucciones SSH y prompt optimizado para Cursor Remote SSH. Soporta
reparaciones en vivo en el servidor de producción de la VPS.
"""
import json
import logging
import os
import re
import traceback as tb_module

from django.conf import settings

logger = logging.getLogger('sentinel')

# Campos sensibles que NUNCA se deben capturar
CAMPOS_SENSIBLES = {
    'password', 'password1', 'password2', 'passwd', 'secret', 'token', 'api_key', 'apikey',
    'authorization', 'csrfmiddlewaretoken', 'pin', 'credit_card',
    'card_number', 'cvv', 'ssn', 'cedula', 'contrasena', 'contraseña', 'otp',
}


def sanitizar_datos(data: dict) -> dict:
    """Elimina campos sensibles de un diccionario de request."""
    if not data:
        return {}
    sanitizado = {}
    for key, value in data.items():
        key_lower = key.lower().replace('-', '_')
        if any(campo in key_lower for campo in CAMPOS_SENSIBLES):
            sanitizado[key] = '***REDACTED***'
        elif isinstance(value, (list, tuple)) and len(value) > 5:
            sanitizado[key] = f'[{len(value)} items - truncated]'
        elif isinstance(value, str) and len(value) > 500:
            sanitizado[key] = value[:500] + '...[TRUNCATED]'
        else:
            sanitizado[key] = value
    return sanitizado


def obtener_api_key():
    """Obtiene la API key de Gemini de multiples fuentes (con strip para limpiar \\r\\n)."""
    key = (
        getattr(settings, 'GOOGLE_GEMINI_API_KEY', None) or
        getattr(settings, 'GOOGLE_API_KEY', None) or
        os.environ.get('GOOGLE_GEMINI_API_KEY') or
        os.environ.get('GOOGLE_API_KEY') or
        os.environ.get('GEMINI_API_KEY')
    )
    return key.strip().replace('\r', '').replace('\n', '') if key else None


def _extraer_archivos_del_traceback(traceback_texto):
    """
    Parsea el traceback y extrae las rutas de archivo y líneas relevantes.
    Retorna lista de dicts: [{'archivo': '...', 'linea': N, 'codigo': '...'}]
    """
    entradas = []
    # Patrón: File "ruta/archivo.py", line N, in funcion
    pattern = re.compile(r'File "([^"]+)", line (\d+), in (.+)')
    lineas = traceback_texto.split('\n')

    for i, linea in enumerate(lineas):
        match = pattern.search(linea.strip())
        if match:
            archivo = match.group(1)
            num_linea = int(match.group(2))
            funcion = match.group(3).strip()
            # La siguiente línea suele ser el código que falló
            codigo_linea = ''
            if i + 1 < len(lineas):
                codigo_linea = lineas[i + 1].strip()
            entradas.append({
                'archivo': archivo,
                'linea': num_linea,
                'funcion': funcion,
                'codigo': codigo_linea,
            })

    return entradas


def _filtrar_archivos_proyecto(entradas):
    """Filtra solo archivos del proyecto PRISLAB (no de librerías)."""
    proyecto = []
    for e in entradas:
        ruta = e['archivo']
        # Ignorar venv, site-packages, lib de Python
        if any(excl in ruta for excl in [
            'site-packages', 'venv/', '/lib/python', '\\lib\\python',
            'django/core', 'django/utils', 'django/template',
            'django/db/', 'gunicorn/', 'whitenoise/',
        ]):
            continue
        proyecto.append(e)
    return proyecto


def analizar_error_con_ia(tipo_excepcion, traceback_texto, url, metodo, datos_request):
    """
    Envía el traceback a Gemini y genera:
    1. analisis_ia: Resumen ejecutivo para el Director
    2. contexto_cursor: Bloque técnico exportable para Cursor
    3. contexto_reparacion: JSON estructurado para autocuración

    Returns:
        tuple: (analisis_ia: str, contexto_cursor: str, contexto_reparacion: dict)
    """
    # Siempre extraer archivos del traceback (funciona offline)
    todas_entradas = _extraer_archivos_del_traceback(traceback_texto)
    entradas_proyecto = _filtrar_archivos_proyecto(todas_entradas)

    api_key = obtener_api_key()
    if not api_key:
        logger.warning("SENTINEL: Sin API key de Gemini, generando análisis offline")
        analisis, contexto = _analisis_offline(tipo_excepcion, traceback_texto, url, metodo)
        reparacion = _contexto_reparacion_offline(
            tipo_excepcion, traceback_texto, url, entradas_proyecto
        )
        return (analisis, contexto, reparacion)

    try:
        from core.utils.gemini_client import generate_content

        # ── Archivos involucrados (para el prompt) ──
        archivos_info = ""
        if entradas_proyecto:
            archivos_info = "ARCHIVOS DEL PROYECTO EN EL TRACEBACK:\n"
            for e in entradas_proyecto:
                archivos_info += f"  - {e['archivo']} línea {e['linea']} en {e['funcion']}: {e['codigo']}\n"

        prompt = f"""Eres PRIS Sentinel, el sistema de telemetría inteligente de PRISLAB (Sistema Clínico SaaS en Django 5 + Python 3.12).
El servidor de producción está en una VPS Ubuntu (contenedor Docker o Gunicorn). El código fuente se edita via Cursor con Remote SSH.
La ruta del proyecto en el contenedor es /app/ y en desarrollo local es el directorio raíz del workspace.

CONTEXTO DEL ERROR:
- URL: {url}
- Método HTTP: {metodo}
- Tipo de Excepción: {tipo_excepcion}
- Datos del Request (sanitizados): {str(datos_request)[:800]}

{archivos_info}

TRACEBACK COMPLETO:
{traceback_texto[:4000]}

GENERA TRES BLOQUES SEPARADOS. Usa EXACTAMENTE estos delimitadores:

---BLOQUE_ANALISIS---
Escribe un resumen ejecutivo para el Director Jonathan Alonso:
1. ¿Qué falló? (lenguaje humano, sin jerga excesiva)
2. ¿Qué impacto tiene para la doctora/paciente?
3. Severidad estimada (CRÍTICA / ALTA / MEDIA / BAJA)
4. ¿Qué debe corregirse?

---BLOQUE_CURSOR---
Genera un bloque técnico que Jonathan pueda copiar y pegar directamente en Cursor:
1. Archivo(s) involucrado(s) (usar ruta relativa al proyecto, ej: consultorio/views.py)
2. Línea(s) específica(s) del error
3. Causa raíz probable
4. Instrucción concreta para Cursor

---BLOQUE_REPARACION_JSON---
Genera un JSON válido (sin markdown, sin ```json, SOLO el JSON puro) con esta estructura:
{{
  "archivo_principal": "ruta/relativa/al/archivo.py",
  "linea_error": <número>,
  "funcion_afectada": "nombre_de_la_funcion",
  "causa_raiz": "Descripción corta de la causa",
  "codigo_original": "La línea de código que está fallando (tal cual)",
  "codigo_propuesto": "El código corregido que debería reemplazar la línea que falla. Si son múltiples líneas usa \\n como separador.",
  "archivos_relacionados": ["otros/archivos/que/tocar.py"],
  "instrucciones_ssh": "Pasos concretos para aplicar via SSH: cd /app && nano archivo.py ... etc",
  "prompt_cursor": "El prompt optimizado para pegar en Cursor que resuelva el bug de una sola vez",
  "riesgo_regresion": "BAJO|MEDIO|ALTO",
  "tiempo_estimado": "5 min | 15 min | 30 min | 1 hora"
}}
"""

        texto_respuesta = generate_content(prompt, max_tokens=2048)

        # Separar los tres bloques
        analisis_ia = ''
        contexto_cursor = ''
        contexto_reparacion = {}

        # Extraer BLOQUE_ANALISIS
        if '---BLOQUE_ANALISIS---' in texto_respuesta:
            partes_analisis = texto_respuesta.split('---BLOQUE_ANALISIS---')
            resto = partes_analisis[1] if len(partes_analisis) > 1 else ''
        else:
            resto = texto_respuesta

        # Extraer BLOQUE_CURSOR
        if '---BLOQUE_CURSOR---' in resto:
            partes_cursor = resto.split('---BLOQUE_CURSOR---')
            analisis_ia = partes_cursor[0].strip()
            resto_cursor = partes_cursor[1] if len(partes_cursor) > 1 else ''
        else:
            analisis_ia = resto.strip()
            resto_cursor = ''

        # Extraer BLOQUE_REPARACION_JSON
        if '---BLOQUE_REPARACION_JSON---' in resto_cursor:
            partes_json = resto_cursor.split('---BLOQUE_REPARACION_JSON---')
            contexto_cursor = partes_json[0].strip()
            json_texto = partes_json[1].strip() if len(partes_json) > 1 else ''
        else:
            contexto_cursor = resto_cursor.strip()
            json_texto = ''

        # Parsear JSON de reparación
        if json_texto:
            try:
                # Limpiar posibles backticks de markdown
                json_limpio = json_texto.strip()
                if json_limpio.startswith('```'):
                    # Remover bloques de código markdown
                    json_limpio = re.sub(r'^```\w*\n?', '', json_limpio)
                    json_limpio = re.sub(r'\n?```$', '', json_limpio.strip())
                contexto_reparacion = json.loads(json_limpio)
            except json.JSONDecodeError as je:
                logger.warning(f"SENTINEL: JSON de reparación inválido: {je}")
                contexto_reparacion = {
                    'error_parsing': str(je),
                    'raw_response': json_texto[:2000],
                    # Fallback: usar datos del traceback
                    'archivo_principal': entradas_proyecto[-1]['archivo'] if entradas_proyecto else 'desconocido',
                    'linea_error': entradas_proyecto[-1]['linea'] if entradas_proyecto else 0,
                    'funcion_afectada': entradas_proyecto[-1]['funcion'] if entradas_proyecto else 'desconocida',
                }

        # Enriquecer con datos extraídos del traceback (siempre fiables)
        if entradas_proyecto:
            contexto_reparacion['_traceback_archivos'] = [
                {'archivo': e['archivo'], 'linea': e['linea'], 'funcion': e['funcion']}
                for e in entradas_proyecto
            ]

        return (analisis_ia, contexto_cursor, contexto_reparacion)

    except (ImportError, AttributeError, ValueError, RuntimeError) as e:
        logger.error(f"SENTINEL: Error al consultar Gemini: {e}")
        analisis, contexto = _analisis_offline(tipo_excepcion, traceback_texto, url, metodo)
        reparacion = _contexto_reparacion_offline(
            tipo_excepcion, traceback_texto, url, entradas_proyecto
        )
        return (analisis, contexto, reparacion)


def _contexto_reparacion_offline(tipo_excepcion, traceback_texto, url, entradas_proyecto):
    """Genera contexto de reparación estructurado sin IA."""
    archivo_principal = 'desconocido'
    linea_error = 0
    funcion_afectada = 'desconocida'
    codigo_original = ''

    if entradas_proyecto:
        ultimo = entradas_proyecto[-1]
        archivo_principal = ultimo['archivo']
        linea_error = ultimo['linea']
        funcion_afectada = ultimo['funcion']
        codigo_original = ultimo['codigo']

    # Normalizar ruta del contenedor a ruta relativa
    ruta_relativa = archivo_principal
    for prefijo in ['/app/', 'C:\\Users\\jonil\\Desktop\\PRISLAB_SaaS\\']:
        if ruta_relativa.startswith(prefijo):
            ruta_relativa = ruta_relativa[len(prefijo):]

    return {
        'archivo_principal': ruta_relativa.replace('\\', '/'),
        'linea_error': linea_error,
        'funcion_afectada': funcion_afectada,
        'causa_raiz': f'{tipo_excepcion} — análisis IA no disponible, revisar traceback manualmente',
        'codigo_original': codigo_original,
        'codigo_propuesto': '# Corrección automática no disponible — revisar traceback manualmente',
        'archivos_relacionados': [
            e['archivo'] for e in entradas_proyecto[:-1]
        ] if len(entradas_proyecto) > 1 else [],
        'instrucciones_ssh': (
            f'# Conectar via SSH y editar:\n'
            f'cd /app\n'
            f'nano {ruta_relativa} +{linea_error}\n'
            f'# Buscar la función: {funcion_afectada}\n'
            f'# Corregir la línea {linea_error} y reiniciar:\n'
            f'# kill -HUP 1  # Reiniciar Gunicorn gracefully'
        ),
        'prompt_cursor': (
            f'@Codebase PRIS SENTINEL detectó un {tipo_excepcion} en '
            f'{ruta_relativa} línea {linea_error} (función {funcion_afectada}). '
            f'URL afectada: {url}. '
            f'Código que falla: `{codigo_original}`. '
            f'Corrige este error sin romper otras funcionalidades.'
        ),
        'riesgo_regresion': 'MEDIO',
        'tiempo_estimado': '15 min',
        '_traceback_archivos': [
            {'archivo': e['archivo'], 'linea': e['linea'], 'funcion': e['funcion']}
            for e in entradas_proyecto
        ],
        '_generado_offline': True,
    }


def _analisis_offline(tipo_excepcion, traceback_texto, url, metodo):
    """Genera análisis básico sin IA cuando Gemini no está disponible."""
    # Extraer archivo y línea del traceback
    lineas_archivo = []
    for line in traceback_texto.split('\n'):
        stripped = line.strip()
        if stripped.startswith('File "'):
            lineas_archivo.append(stripped)

    ultima_linea = lineas_archivo[-1] if lineas_archivo else 'No identificado'

    analisis = (
        f"ERROR DETECTADO (análisis offline - Gemini no disponible)\n\n"
        f"Tipo: {tipo_excepcion}\n"
        f"URL afectada: {metodo} {url}\n"
        f"Ubicación probable: {ultima_linea}\n\n"
        f"Impacto: La funcionalidad en {url} no está operativa. "
        f"La doctora verá un error al intentar usar esta sección.\n\n"
        f"Acción requerida: Revisar el traceback completo y corregir."
    )

    contexto = (
        f"@Codebase PRIS SENTINEL detectó un error:\n\n"
        f"URL: {metodo} {url}\n"
        f"Excepción: {tipo_excepcion}\n"
        f"Ubicación: {ultima_linea}\n\n"
        f"Traceback (últimas líneas):\n"
        f"{chr(10).join(traceback_texto.split(chr(10))[-15:])}\n\n"
        f"Corrige este error manteniendo la estabilidad del sistema."
    )

    return (analisis, contexto)


def cruzar_feedback_con_error(descripcion_usuario, ultima_incidencia):
    """
    Cruza el comentario en lenguaje natural del usuario con el último
    log de error registrado para crear un 'Ticket de Reparación Maestro'.

    Args:
        descripcion_usuario: Lo que la doctora escribió
        ultima_incidencia: Instancia de IncidenciaSentinel más reciente

    Returns:
        str: Contexto enriquecido para Cursor
    """
    api_key = obtener_api_key()

    traceback_ref = ''
    if ultima_incidencia:
        traceback_ref = (
            f"Último error registrado:\n"
            f"- URL: {ultima_incidencia.url_afectada}\n"
            f"- Excepción: {ultima_incidencia.tipo_excepcion}\n"
            f"- Código HTTP: {ultima_incidencia.codigo_http}\n"
            f"- Traceback (extracto): {ultima_incidencia.traceback_completo[:1500]}\n"
        )

    if not api_key:
        return (
            f"TICKET DE REPARACIÓN MAESTRO (sin IA)\n\n"
            f"Reporte del usuario: {descripcion_usuario}\n\n"
            f"{traceback_ref}\n"
            f"Instrucción: Correlacionar el reporte del usuario con el traceback "
            f"y corregir la causa raíz."
        )

    try:
        from core.utils.gemini_client import generate_content

        prompt = f"""Eres PRIS Sentinel. Una doctora reportó un problema con el sistema:

REPORTE DE LA DOCTORA:
"{descripcion_usuario}"

{traceback_ref}

GENERA UN "TICKET DE REPARACIÓN MAESTRO":
1. Correlación: ¿El reporte de la doctora coincide con el error técnico?
2. Si coincide: Genera instrucciones precisas para Cursor (archivo, línea, corrección)
3. Si NO coincide: Indica que puede ser un bug no capturado y sugiere dónde buscar
4. Prioridad sugerida y tiempo estimado de corrección

El ticket debe ser copiable directamente a Cursor por Jonathan Alonso.
"""

        return generate_content(prompt, max_tokens=1200)

    except (ImportError, AttributeError, ValueError, RuntimeError) as e:
        logger.error(f"SENTINEL: Error al generar ticket maestro: {e}")
        return (
            f"TICKET DE REPARACIÓN MAESTRO (IA no disponible)\n\n"
            f"Reporte: {descripcion_usuario}\n\n"
            f"{traceback_ref}\n"
            f"Correlacionar manualmente y corregir."
        )


def generar_prompt_cursor_reparacion(incidencia):
    """
    Genera un prompt optimizado para Cursor Remote SSH a partir de una incidencia.
    Diseñado para que Jonathan lo pegue en Cursor conectado via SSH al servidor
    y la IA aplique la corrección directamente en producción.

    Args:
        incidencia: IncidenciaSentinel instance

    Returns:
        str: Prompt listo para pegar en Cursor
    """
    ctx = incidencia.contexto_reparacion or {}

    archivo = ctx.get('archivo_principal', 'desconocido')
    linea = ctx.get('linea_error', '?')
    funcion = ctx.get('funcion_afectada', '?')
    causa = ctx.get('causa_raiz', 'Ver traceback')
    codigo_original = ctx.get('codigo_original', '')
    codigo_propuesto = ctx.get('codigo_propuesto', '')
    archivos_rel = ctx.get('archivos_relacionados', [])
    riesgo = ctx.get('riesgo_regresion', 'MEDIO')
    tiempo = ctx.get('tiempo_estimado', '15 min')
    instrucciones_ssh = ctx.get('instrucciones_ssh', '')

    prompt = (
        f"@Codebase PRIS SENTINEL — TICKET DE REPARACIÓN EN VIVO #{incidencia.id}\n"
        f"{'=' * 70}\n"
        f"MODO: REPARACIÓN REMOTA (Remote SSH → Servidor Ubuntu)\n"
        f"SEVERIDAD: {incidencia.get_severidad_display()}\n"
        f"MÓDULO: {incidencia.namespace.upper()}\n"
        f"TAG: {incidencia.tag}\n"
        f"FECHA: {incidencia.fecha_creacion.strftime('%Y-%m-%d %H:%M')}\n"
        f"RIESGO REGRESIÓN: {riesgo}\n"
        f"TIEMPO ESTIMADO: {tiempo}\n"
        f"{'=' * 70}\n\n"
        f"CONTEXTO DE CONEXIÓN:\n"
        f"  - Estás conectado via Remote SSH al servidor de producción\n"
        f"  - Ruta del proyecto en servidor: /app/\n"
        f"  - Ruta del proyecto en local: C:\\Users\\jonil\\Desktop\\PRISLAB_SaaS\\\n"
        f"  - Cualquier cambio que hagas se aplica EN VIVO\n\n"
        f"ARCHIVO PRINCIPAL: {archivo}\n"
        f"LÍNEA DEL ERROR: {linea}\n"
        f"FUNCIÓN AFECTADA: {funcion}\n"
        f"URL AFECTADA: {incidencia.metodo_http} {incidencia.url_afectada}\n"
        f"EXCEPCIÓN: {incidencia.tipo_excepcion}\n\n"
        f"CAUSA RAÍZ:\n{causa}\n\n"
    )

    if codigo_original:
        prompt += f"CÓDIGO QUE FALLA:\n```python\n{codigo_original}\n```\n\n"

    if codigo_propuesto:
        prompt += (
            f"CÓDIGO PROPUESTO POR IA (aplica este reemplazo):\n"
            f"```python\n{codigo_propuesto}\n```\n\n"
        )

    if archivos_rel:
        prompt += f"ARCHIVOS RELACIONADOS QUE REVISAR: {', '.join(archivos_rel)}\n\n"

    if incidencia.descripcion_usuario:
        prompt += (
            f"REPORTE DEL USUARIO (lenguaje natural):\n"
            f'"{incidencia.descripcion_usuario}"\n\n'
        )

    prompt += (
        f"TRACEBACK (últimas 25 líneas):\n"
        f"{chr(10).join(incidencia.traceback_completo.split(chr(10))[-25:])}\n\n"
    )

    if instrucciones_ssh:
        prompt += (
            f"{'=' * 70}\n"
            f"INSTRUCCIONES SSH (si necesitas terminal):\n"
            f"{instrucciones_ssh}\n\n"
        )

    prompt += (
        f"{'=' * 70}\n"
        f"INSTRUCCIÓN PARA CURSOR:\n"
        f"1. Abre el archivo `{archivo}` y ve a la línea {linea}\n"
        f"2. Busca la función `{funcion}`\n"
        f"3. Aplica la corrección propuesta arriba\n"
        f"4. Verifica que no se rompan otros módulos ({incidencia.namespace})\n"
        f"5. Si estás en Remote SSH, los cambios se aplican en vivo\n"
        f"6. Para reiniciar Gunicorn sin downtime: kill -HUP 1\n"
        f"{'=' * 70}\n"
    )

    return prompt


def generar_resumen_ssh_rapido(incidencia):
    """
    Genera un resumen ultra-compacto para corrección rápida via SSH terminal.
    Ideal para cuando Jonathan no tiene Cursor a mano y necesita arreglar
    directamente desde la terminal SSH.

    Args:
        incidencia: IncidenciaSentinel instance

    Returns:
        str: Comandos SSH listos para ejecutar
    """
    ctx = incidencia.contexto_reparacion or {}
    archivo = ctx.get('archivo_principal', 'desconocido')
    linea = ctx.get('linea_error', 0)
    funcion = ctx.get('funcion_afectada', '?')

    return (
        f"# PRIS SENTINEL — FIX RÁPIDO #{incidencia.id}\n"
        f"# {incidencia.get_severidad_display()} | {incidencia.tipo_excepcion}\n"
        f"# URL: {incidencia.url_afectada}\n"
        f"cd /app\n"
        f"nano +{linea} {archivo}  # Buscar: {funcion}\n"
        f"# Después de editar:\n"
        f"python manage.py check --deploy 2>&1 | head -20\n"
        f"kill -HUP 1  # Reiniciar Gunicorn sin downtime\n"
    )
