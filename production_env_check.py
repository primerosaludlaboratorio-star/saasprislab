"""
production_env_check.py — PRISLAB v5.2
════════════════════════════════════════════════════════════════════
Validador de variables de entorno para producción en Google Cloud Run.
Genera un informe completo al arranque: qué está configurado, qué falta,
qué funcionalidades quedan desactivadas.

USO:
    python production_env_check.py             → solo reporte
    python production_env_check.py --generar   → genera FERNET_KEY nueva
    python production_env_check.py --strict    → falla con exit(1) si hay CRITICOS

Se integra automáticamente en Django via AppConfig.ready() cuando
GOOGLE_CLOUD_PROJECT está definido.
════════════════════════════════════════════════════════════════════
"""
import os
import sys
import logging

logger = logging.getLogger('core.production_check')

# ── Catálogo de variables requeridas ──────────────────────────────────────────
ENV_CATALOG = [
    {
        'nombre': 'SECRET_KEY',
        'nivel': 'CRITICO',
        'impacto': 'El sistema NO puede arrancar sin esta variable. Genera con: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"',
        'como_configurar': 'Secret Manager → crear secreto "django-secret-key"',
    },
    {
        'nombre': 'DATABASE_URL',
        'nivel': 'CRITICO',
        'alias': ['DB_NAME', 'DB_USER', 'DB_PASSWORD', 'CLOUD_SQL_CONNECTION_NAME'],
        'impacto': 'Sin base de datos el sistema no funciona.',
        'como_configurar': 'Secret Manager → "db-password". Variables en Cloud Run → DB_NAME, DB_USER, CLOUD_SQL_CONNECTION_NAME',
    },
    {
        'nombre': 'GEMINI_API_KEY',
        'nivel': 'ALTO',
        'alias': ['GOOGLE_API_KEY'],
        'impacto': 'PRIS-Jarvis no puede procesar lenguaje natural. El Orb activará modo contingencia (rojo).',
        'como_configurar': 'console.cloud.google.com → APIs → Gemini → Crear clave. Secret Manager → "gemini-api-key"',
    },
    {
        'nombre': 'FERNET_KEY',
        'nivel': 'ALTO',
        'impacto': 'El módulo Bienestar Staff usará cifrado de fallback (menos seguro). Datos existentes pueden no descifrarse correctamente.',
        'como_configurar': 'Ejecutar: python production_env_check.py --generar → copiar la clave generada → Secret Manager → "fernet-key"',
    },
    {
        'nombre': 'REDIS_URL',
        'nivel': 'MODERADO',
        'impacto': 'Celery corre en modo síncrono (eager). Las subidas a Google Drive serán lentas (bloquean al usuario).',
        'como_configurar': 'Cloud Memorystore → crear instancia Redis → copiar URL → variable de entorno REDIS_URL',
    },
    {
        'nombre': 'TELEGRAM_BOT_TOKEN',
        'nivel': 'MODERADO',
        'impacto': 'Alertas CISO de >10 accesos/hora no se envían por Telegram. El War Room sigue funcionando.',
        'como_configurar': 'Telegram → @BotFather → /newbot → copiar token → Secret Manager → "telegram-bot-token"',
    },
    {
        'nombre': 'TELEGRAM_CISO_CHAT_ID',
        'nivel': 'BAJO',
        'impacto': 'Necesario junto con TELEGRAM_BOT_TOKEN para las alertas CISO.',
        'como_configurar': 'Telegram → @userinfobot → copiar tu chat_id',
    },
    {
        'nombre': 'VAPID_PUBLIC_KEY',
        'nivel': 'BAJO',
        'impacto': 'Notificaciones Web Push desactivadas.',
        'como_configurar': 'py-vapid → vapid --gen → copiar claves → Secret Manager',
    },
    {
        'nombre': 'DRIVE_FOLDER_ID',
        'nivel': 'BAJO',
        'impacto': 'Los archivos se guardan solo en local. El respaldo a Google Drive (20TB) no funciona.',
        'como_configurar': 'Google Drive → crear carpeta PRISLAB → copiar el ID de la URL → Secret Manager → "drive-folder-id"',
    },
]


def _tiene_variable(nombre: str, entry: dict) -> bool:
    """Verifica si la variable o alguno de sus alias existe y no está vacía."""
    nombres_a_probar = [nombre] + entry.get('alias', [])
    return any(bool(os.environ.get(n, '').strip()) for n in nombres_a_probar)


def verificar_entorno(strict: bool = False) -> dict:
    """
    Analiza el entorno y retorna un diccionario con el estado de cada variable.
    """
    resultado = {
        'criticos_faltantes': [],
        'altos_faltantes': [],
        'moderados_faltantes': [],
        'bajos_faltantes': [],
        'configurados': [],
        'ok': True,
    }

    for entry in ENV_CATALOG:
        nombre = entry['nombre']
        if _tiene_variable(nombre, entry):
            resultado['configurados'].append(nombre)
        else:
            nivel = entry['nivel']
            if nivel == 'CRITICO':
                resultado['criticos_faltantes'].append(entry)
                resultado['ok'] = False
            elif nivel == 'ALTO':
                resultado['altos_faltantes'].append(entry)
            elif nivel == 'MODERADO':
                resultado['moderados_faltantes'].append(entry)
            else:
                resultado['bajos_faltantes'].append(entry)

    return resultado


def generar_fernet_key() -> str:
    """Genera una nueva clave Fernet válida para AES-256."""
    try:
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()
    except ImportError:
        import base64
        import secrets
        raw = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(raw).decode()


def imprimir_reporte(resultado: dict, para_logs: bool = False) -> None:
    """Imprime un reporte legible del estado del entorno."""
    sep = '═' * 64
    log = logger.info if para_logs else print

    log(sep)
    log('PRISLAB v5.2 — VERIFICACIÓN DE ENTORNO DE PRODUCCIÓN')
    log(sep)

    if resultado['configurados']:
        log(f"[OK] Variables configuradas ({len(resultado['configurados'])}):")
        for v in resultado['configurados']:
            log(f"     + {v}")

    if resultado['criticos_faltantes']:
        log('')
        log('[CRITICO] Variables CRITICAS faltantes — el sistema no funcionará correctamente:')
        for e in resultado['criticos_faltantes']:
            log(f"     ✗ {e['nombre']}")
            log(f"       Impacto: {e['impacto']}")
            log(f"       Solución: {e['como_configurar']}")

    if resultado['altos_faltantes']:
        log('')
        log('[ALTO] Variables de ALTO impacto faltantes — funcionalidades desactivadas:')
        for e in resultado['altos_faltantes']:
            log(f"     ! {e['nombre']}")
            log(f"       Impacto: {e['impacto']}")
            log(f"       Solución: {e['como_configurar']}")

    if resultado['moderados_faltantes']:
        log('')
        log('[MODERADO] Variables de impacto moderado faltantes:')
        for e in resultado['moderados_faltantes']:
            log(f"     ~ {e['nombre']} — {e['impacto']}")

    if resultado['bajos_faltantes']:
        log('')
        log('[INFO] Variables opcionales no configuradas:')
        for e in resultado['bajos_faltantes']:
            log(f"     - {e['nombre']} — {e['impacto']}")

    log('')
    total_faltantes = (
        len(resultado['criticos_faltantes']) +
        len(resultado['altos_faltantes']) +
        len(resultado['moderados_faltantes'])
    )
    if total_faltantes == 0:
        log('ESTADO: SISTEMA EN VUELO — Todas las variables criticas configuradas.')
    elif resultado['criticos_faltantes']:
        log(f'ESTADO: DEGRADADO CRITICO — {len(resultado["criticos_faltantes"])} variables criticas faltantes.')
    else:
        log(f'ESTADO: OPERATIVO CON LIMITACIONES — {total_faltantes} variables de alto/moderado impacto faltantes.')
    log(sep)


def verificar_y_loguear():
    """Hook para Django AppConfig.ready() — solo loguea, no bloquea."""
    if not os.environ.get('GOOGLE_CLOUD_PROJECT'):
        return  # Solo en producción
    resultado = verificar_entorno(strict=False)
    imprimir_reporte(resultado, para_logs=True)
    return resultado


# ── Ejecución standalone ───────────────────────────────────────────────────────
if __name__ == '__main__':
    args = sys.argv[1:]

    if '--generar' in args:
        print()
        print('=' * 64)
        print('GENERADOR DE CLAVES — PRISLAB v5.2')
        print('=' * 64)

        # FERNET_KEY
        fernet_key = generar_fernet_key()
        print(f'\n[FERNET_KEY] Clave AES-256 para módulo Bienestar:')
        print(f'  {fernet_key}')
        print(f'  -> Guardar en Secret Manager como: fernet-key')

        # SECRET_KEY de Django (si no está configurada)
        if not os.environ.get('SECRET_KEY'):
            try:
                import django
                import sys as _sys
                _sys.path.insert(0, '.')
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
                from django.core.management.utils import get_random_secret_key
                secret_key = get_random_secret_key()
                print(f'\n[SECRET_KEY] Clave secreta de Django:')
                print(f'  {secret_key}')
                print(f'  -> Guardar en Secret Manager como: django-secret-key')
            except Exception:
                pass

        print()
        print('INSTRUCCIONES PARA GOOGLE CLOUD:')
        print('  1. Abre: console.cloud.google.com → Secret Manager')
        print('  2. Crea secreto "fernet-key" con el valor de FERNET_KEY de arriba')
        print('  3. En cloudbuild.yaml agrega: FERNET_KEY=fernet-key:latest')
        print('  4. Re-despliega con: gcloud builds submit --config cloudbuild.yaml .')
        print('=' * 64)
        sys.exit(0)

    # Reporte normal
    strict = '--strict' in args
    resultado = verificar_entorno(strict=strict)
    imprimir_reporte(resultado, para_logs=False)

    if strict and not resultado['ok']:
        sys.exit(1)
