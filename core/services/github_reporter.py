"""
PRIS SENTINEL -> GITHUB ISSUES: Auto-reporte de errores en produccion.
=====================================================================
Cuando PRIS detecta un error 500, crea automaticamente un Issue en GitHub.
El usuario recibe notificacion en la App movil de GitHub.

Configuracion (variables de entorno):
    GITHUB_TOKEN   = Personal Access Token con permisos 'repo'
    GITHUB_REPO    = owner/repo (ej: 'jonilsam/PRISLAB_SaaS')

Flujo:
    Error 500 -> Sentinel -> crear_github_issue() -> GitHub REST API -> Issue creado
    -> Notificacion en App GitHub del celular -> Cursor ve el issue y propone fix
"""
import hashlib
import json
import logging
import os
from django.utils import timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import quote

logger = logging.getLogger('sentinel.github')

# ── Configuracion ──────────────────────────────────────────────────────────
GITHUB_API = 'https://api.github.com'
# Limpieza agresiva de tokens (algunos entornos pueden inyectar \r\n invisibles)
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '').strip().replace('\r', '').replace('\n', '')
GITHUB_REPO = os.environ.get('GITHUB_REPO', '').strip().replace('\r', '').replace('\n', '')  # formato: owner/repo

# Rate limit: maximo N issues por hora para no saturar
MAX_ISSUES_PER_HOUR = 10
_issue_cache = {}  # fingerprint -> timestamp (deduplicacion)
_issue_count_this_hour = 0
_hour_marker = 0


def _github_headers():
    """Headers para GitHub API v3."""
    return {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'PRIS-Sentinel/1.0',
    }


def _error_fingerprint(tipo_exc, url, traceback_texto):
    """
    Genera un fingerprint unico para deduplicar errores repetidos.
    Mismo error en la misma URL = mismo fingerprint = no duplicar issue.
    """
    # Extraer la linea clave del traceback (ultima linea de error)
    lines = traceback_texto.strip().split('\n')
    key_line = lines[-1] if lines else tipo_exc
    raw = f"{tipo_exc}:{url}:{key_line}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _is_rate_limited(fingerprint):
    """
    Verifica si este error ya fue reportado recientemente.
    - Mismo fingerprint en los ultimos 30 minutos -> skip
    - Mas de MAX_ISSUES_PER_HOUR issues esta hora -> skip
    """
    global _issue_count_this_hour, _hour_marker
    now = timezone.now()
    current_hour = now.hour

    # Reset contador cada hora
    if current_hour != _hour_marker:
        _hour_marker = current_hour
        _issue_count_this_hour = 0
        _issue_cache.clear()

    # Check rate limit global
    if _issue_count_this_hour >= MAX_ISSUES_PER_HOUR:
        logger.warning(f'SENTINEL-GITHUB: Rate limit alcanzado ({MAX_ISSUES_PER_HOUR}/hora)')
        return True

    # Check deduplicacion
    if fingerprint in _issue_cache:
        elapsed = (now - _issue_cache[fingerprint]).total_seconds()
        if elapsed < 1800:  # 30 minutos
            logger.info(f'SENTINEL-GITHUB: Error duplicado (fp={fingerprint}), skip')
            return True

    return False


def _check_existing_issue(fingerprint):
    """
    Busca si ya existe un issue abierto con este fingerprint en GitHub.
    Evita crear duplicados incluso entre reinicios del servidor.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False

    try:
        search_url = (
            f"{GITHUB_API}/search/issues?"
            f"q={quote(f'repo:{GITHUB_REPO} is:issue is:open SENTINEL-{fingerprint}')}"
        )
        req = Request(search_url, headers=_github_headers(), method='GET')
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get('total_count', 0) > 0
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en _check_existing_issue (github_reporter.py)")
        logger.debug(f'SENTINEL-GITHUB: Error buscando issue existente: {e}')
        return False


def _severity_label(severidad):
    """Mapea severidad de Sentinel a label + emoji de GitHub."""
    mapping = {
        'CRITICA': ('bug-critical', 'CRITICO'),
        'ALTA': ('bug', 'ALTO'),
        'MEDIA': ('bug', 'MEDIO'),
        'BAJA': ('enhancement', 'BAJO'),
    }
    return mapping.get(severidad, ('bug', severidad))


def crear_github_issue(datos):
    """
    Crea un Issue en GitHub con toda la informacion del error.

    Args:
        datos (dict): Diccionario con:
            - tipo_excepcion (str)
            - traceback_texto (str)
            - url (str)
            - path (str)
            - metodo (str)
            - severidad (str): CRITICA, ALTA, MEDIA, BAJA
            - namespace (str): modulo afectado
            - codigo_http (int)
            - user_id (int|None)
            - incidencia_id (int|None): ID de IncidenciaSentinel si existe

    Returns:
        dict|None: Datos del issue creado, o None si no se pudo crear.
    """
    global _issue_count_this_hour

    # Validar configuracion
    if not GITHUB_TOKEN:
        logger.debug('SENTINEL-GITHUB: GITHUB_TOKEN no configurado, skip')
        return None
    if not GITHUB_REPO:
        logger.debug('SENTINEL-GITHUB: GITHUB_REPO no configurado, skip')
        return None

    tipo_exc = datos.get('tipo_excepcion', 'Unknown')
    tb = datos.get('traceback_texto', '')
    url = datos.get('path', datos.get('url', '/'))
    metodo = datos.get('metodo', 'GET')
    severidad = datos.get('severidad', 'MEDIA')
    namespace = datos.get('namespace', 'core')
    codigo = datos.get('codigo_http', 500)
    user_id = datos.get('user_id')
    incidencia_id = datos.get('incidencia_id')

    # Generar fingerprint
    fingerprint = _error_fingerprint(tipo_exc, url, tb)

    # Rate limiting + deduplicacion
    if _is_rate_limited(fingerprint):
        return None

    # Check si ya existe issue abierto en GitHub
    if _check_existing_issue(fingerprint):
        logger.info(f'SENTINEL-GITHUB: Issue abierto ya existe (fp={fingerprint}), skip')
        _issue_cache[fingerprint] = timezone.now()
        return None

    # ── Construir Issue ────────────────────────────────────────────────
    label_name, sev_text = _severity_label(severidad)
    tag = f'#BUG_{namespace.upper()}'
    now = timezone.now().strftime('%Y-%m-%d %H:%M UTC')

    # Titulo conciso
    title = f"[SENTINEL-{fingerprint}] {sev_text}: {tipo_exc} en {metodo} {url}"

    # Truncar traceback si es muy largo
    tb_display = tb[-3000:] if len(tb) > 3000 else tb

    # ── AI HOTFIX SUGGESTION (Pilar 1 — Rev 128) ──────────────────────
    suggested_fix = _generar_hotfix_ia(tipo_exc, tb_display, url, namespace)

    # Body con formato Markdown rico
    body = f"""## PRIS Sentinel - Auto-Reporte de Error

| Campo | Valor |
|-------|-------|
| **Severidad** | {sev_text} |
| **Modulo** | `{namespace}` {tag} |
| **Tipo** | `{tipo_exc}` |
| **HTTP** | `{codigo} {metodo}` |
| **URL** | `{url}` |
| **Usuario ID** | {user_id or 'N/A'} |
| **Incidencia DB** | #{incidencia_id or 'N/A'} |
| **Timestamp** | {now} |
| **Fingerprint** | `{fingerprint}` |

### Traceback Completo

```python
{tb_display}
```

### Contexto de Reparacion

- **Archivo probable**: Buscar en `{namespace}/views.py` o `{namespace}/models.py`
- **Tipo de error**: `{tipo_exc}` — {_error_hint(tipo_exc)}

{suggested_fix}

---
*Auto-generado por PRIS Sentinel v5 (AIOps). Para cerrar este issue, aplica el SUGGESTED_FIX y haz deploy.*
"""

    # ── Crear Issue via API ────────────────────────────────────────────
    try:
        api_url = f"{GITHUB_API}/repos/{GITHUB_REPO}/issues"
        payload = json.dumps({
            'title': title[:256],
            'body': body,
            'labels': [label_name, f'module-{namespace}', 'auto-sentinel'],
        }).encode('utf-8')

        req = Request(api_url, data=payload, headers=_github_headers(), method='POST')

        with urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            issue_number = result.get('number')
            issue_url = result.get('html_url')

            # Actualizar cache y contador
            _issue_cache[fingerprint] = timezone.now()
            _issue_count_this_hour += 1

            logger.info(
                f'SENTINEL-GITHUB: Issue #{issue_number} creado -> {issue_url}'
            )

            return {
                'issue_number': issue_number,
                'issue_url': issue_url,
                'fingerprint': fingerprint,
            }

    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ''
        logger.error(
            f'SENTINEL-GITHUB: HTTP {e.code} al crear issue: {error_body[:500]}'
        )
        # Si es 422 (Validation failed) por labels que no existen, reintentar sin labels
        if e.code == 422:
            return _crear_issue_sin_labels(title, body, fingerprint)
        return None

    except (URLError, TimeoutError) as e:
        logger.error(f'SENTINEL-GITHUB: Error de red al crear issue: {e}')
        return None

    except Exception as e:
        logger.error(f'SENTINEL-GITHUB: Error inesperado: {e}')
        return None


def _crear_issue_sin_labels(title, body, fingerprint):
    """Fallback: crear issue sin labels si la validacion fallo."""
    global _issue_count_this_hour
    try:
        api_url = f"{GITHUB_API}/repos/{GITHUB_REPO}/issues"
        payload = json.dumps({
            'title': title[:256],
            'body': body,
        }).encode('utf-8')

        req = Request(api_url, data=payload, headers=_github_headers(), method='POST')

        with urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            _issue_cache[fingerprint] = timezone.now()
            _issue_count_this_hour += 1
            issue_url = result.get('html_url')
            logger.info(f'SENTINEL-GITHUB: Issue creado (sin labels) -> {issue_url}')
            return {
                'issue_number': result.get('number'),
                'issue_url': issue_url,
                'fingerprint': fingerprint,
            }
    except Exception as e:
        logger.error(f'SENTINEL-GITHUB: Fallback sin labels tambien fallo: {e}')
        return None


def _error_hint(tipo_exc):
    """Genera un hint rapido basado en el tipo de excepcion."""
    hints = {
        'ValueError': 'Dato invalido o conversion fallida. Revisar inputs del usuario.',
        'TypeError': 'Tipo de dato incorrecto. Posible None donde se esperaba objeto.',
        'KeyError': 'Clave no encontrada en diccionario. Verificar keys del request.',
        'AttributeError': 'Atributo inexistente. Posible modelo sin campo o None.',
        'DoesNotExist': 'Registro no encontrado en DB. Usar get_or_404 o filter.',
        'IntegrityError': 'Violacion de constraint en DB. Dato duplicado o FK rota.',
        'OperationalError': 'Error de conexion a DB. Verificar PostgreSQL.',
        'PermissionDenied': 'Permiso denegado. Verificar roles y decoradores.',
        'Http404': 'Ruta no encontrada. Verificar urls.py.',
        'ImportError': 'Modulo no encontrado. Verificar requirements.txt.',
        'MultiValueDictKeyError': 'Campo faltante en POST/GET. Usar .get() en lugar de [].',
    }
    for key, hint in hints.items():
        if key in tipo_exc:
            return hint
    return 'Revisar traceback para diagnostico detallado.'


def _generar_hotfix_ia(tipo_exc, traceback_texto, url, namespace):
    """
    Usa Gemini AI para generar un SUGGESTED_FIX basado en el traceback.
    El fix se incluye en el Issue de GitHub para que el Director
    solo tenga que copiar y pegar la solucion.

    Returns:
        str: Bloque Markdown con la sugerencia, o string vacio si falla.
    """
    try:
        from core.utils.gemini_client import generate_content

        # Extraer archivo y linea del traceback
        archivo_afectado = 'desconocido'
        linea_afectada = '?'
        for line in traceback_texto.split('\n'):
            stripped = line.strip()
            if stripped.startswith('File "') and ', line ' in stripped:
                parts = stripped.split('"')
                if len(parts) >= 2:
                    archivo_afectado = parts[1]
                linea_match = stripped.split(', line ')
                if len(linea_match) >= 2:
                    linea_afectada = linea_match[1].split(',')[0].strip()

        prompt = (
            "Eres un ingeniero senior de Django/Python. Analiza este error de produccion "
            "y genera un parche concreto que lo resuelva.\n\n"
            f"MODULO: {namespace}\n"
            f"URL: {url}\n"
            f"TIPO DE ERROR: {tipo_exc}\n"
            f"ARCHIVO: {archivo_afectado}\n"
            f"LINEA: {linea_afectada}\n\n"
            f"TRACEBACK:\n{traceback_texto[-2000:]}\n\n"
            "REGLAS:\n"
            "1. Responde SOLO con el bloque de codigo corregido (maximo 30 lineas)\n"
            "2. Indica el archivo exacto y la linea donde aplicar el cambio\n"
            "3. Explica en 1-2 lineas que cambiaste y por que\n"
            "4. Si necesitas agregar imports, incluyelos\n"
            "5. No incluyas el traceback en tu respuesta\n"
            "6. Usa formato Markdown con bloques de codigo Python\n"
        )

        fix_text = (generate_content(prompt, max_tokens=1200) or "").strip()

        if fix_text:
            # Limitar a 3000 chars para no saturar el issue
            if len(fix_text) > 3000:
                fix_text = fix_text[:3000] + '\n... (truncado)'

            return (
                f"### SUGGESTED_FIX (Generado por PRIS Sentinel IA)\n\n"
                f"> **Archivo**: `{archivo_afectado}` linea `{linea_afectada}`\n\n"
                f"{fix_text}\n"
            )

    except Exception as e:
        logger.warning(f'SENTINEL-GITHUB: IA Hotfix no disponible: {e}')

    return (
        "### SUGGESTED_FIX\n\n"
        "> IA no disponible en este momento. Revisar traceback manualmente.\n"
    )


def test_github_connection():
    """
    Test rapido de la conexion a GitHub. Util para diagnostico.
    Retorna True si la conexion es valida.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, 'GITHUB_TOKEN o GITHUB_REPO no configurados'

    try:
        api_url = f"{GITHUB_API}/repos/{GITHUB_REPO}"
        req = Request(api_url, headers=_github_headers(), method='GET')
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return True, f"Conectado a {data.get('full_name')} (privado={data.get('private')})"
    except HTTPError as e:
        return False, f'HTTP {e.code}: Token invalido o repo no accesible'
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_github_connection (github_reporter.py)")
        return False, str(e)