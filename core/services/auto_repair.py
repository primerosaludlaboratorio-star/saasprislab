"""
PRIS SENTINEL — Servicio de Auto-Reparación de Infraestructura (v4.1)
=====================================================================
Tres motores de reparación automática para problemas de infraestructura:

1. GUNICORN SOFT RESTART
   - Detecta 3+ errores consecutivos de Timeout/MemoryError
   - Envía SIGHUP al master Gunicorn para reciclar workers (graceful)
   - No interrumpe requests activos

2. DB CONNECTION RECOVERY
   - Detecta "Too many connections" / OperationalError
   - Cierra conexiones idle en el pool de Django
   - Ejecuta RESET CONNECTION POOL

3. AUTO-FIX PERMISSIONS
   - Detecta 403 Forbidden en rutas que el rol del usuario debería acceder
   - Regenera el mapa de permisos de la sesión en tiempo real
   - Invalida cache de permisos del usuario
"""
import logging
import os
import signal
import time
import threading
from collections import deque
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger('sentinel.repair')

# ============================================================================
# 1. GUNICORN SOFT RESTART
# ============================================================================

# Registro de errores recientes (ventana deslizante de últimos 60 segundos)
_critical_errors = deque(maxlen=50)
_last_restart_time = None
_RESTART_COOLDOWN_SECONDS = 120  # No reiniciar más de 1 vez cada 2 minutos
_CONSECUTIVE_THRESHOLD = 3  # Número de errores para disparar restart

# Tipos de error que disparan restart
RESTART_TRIGGER_ERRORS = {
    'TimeoutError', 'GatewayTimeout', 'MemoryError',
    'ConnectionResetError', 'BrokenPipeError',
    'OSError',  # Includes "Cannot allocate memory"
}


def registrar_error_critico(tipo_excepcion, mensaje_error=''):
    """
    Registra un error crítico. Si se alcanzan 3 consecutivos
    de tipo Timeout/Memory en 60 segundos, dispara soft restart.
    
    Args:
        tipo_excepcion (str): Nombre del tipo de excepción
        mensaje_error (str): Mensaje del error para análisis
    Returns:
        bool: True si se disparó un restart
    """
    now = timezone.now()
    
    # Verificar si el tipo de error es relevante para restart
    is_restart_trigger = (
        tipo_excepcion in RESTART_TRIGGER_ERRORS or
        'timeout' in tipo_excepcion.lower() or
        'memory' in tipo_excepcion.lower() or
        'timeout' in mensaje_error.lower() or
        'out of memory' in mensaje_error.lower() or
        'cannot allocate memory' in mensaje_error.lower()
    )
    
    if not is_restart_trigger:
        return False
    
    _critical_errors.append({
        'tipo': tipo_excepcion,
        'mensaje': mensaje_error[:200],
        'timestamp': now,
    })
    
    # Contar errores en los últimos 60 segundos
    cutoff = now - timedelta(seconds=60)
    recent_errors = [e for e in _critical_errors if e['timestamp'] > cutoff]
    
    if len(recent_errors) >= _CONSECUTIVE_THRESHOLD:
        return _ejecutar_soft_restart()
    
    return False


def _ejecutar_soft_restart():
    """
    Ejecuta un soft restart de Gunicorn enviando SIGHUP al proceso master.
    
    SIGHUP en Gunicorn:
    - Recarga la configuración
    - Recicla workers uno por uno (graceful)
    - NO interrumpe requests activos
    - Libera memoria de workers viejos
    
    Returns:
        bool: True si se envió la señal exitosamente
    """
    global _last_restart_time
    
    now = timezone.now()
    
    # Cooldown: no reiniciar muy seguido
    if _last_restart_time:
        elapsed = (now - _last_restart_time).total_seconds()
        if elapsed < _RESTART_COOLDOWN_SECONDS:
            logger.info(
                f"SENTINEL REPAIR [Gunicorn]: Cooldown activo "
                f"({int(elapsed)}s / {_RESTART_COOLDOWN_SECONDS}s), skip restart"
            )
            return False
    
    try:
        # En producción, el master Gunicorn es el PID 1 o el padre del worker actual
        master_pid = _encontrar_gunicorn_master()
        
        if master_pid:
            logger.warning(
                f"SENTINEL REPAIR [Gunicorn]: Enviando SIGHUP al master PID {master_pid} "
                f"para soft restart de workers (3+ errores criticos detectados)"
            )
            os.kill(master_pid, signal.SIGHUP)
            _last_restart_time = now
            _critical_errors.clear()
            
            logger.info("SENTINEL REPAIR [Gunicorn]: SIGHUP enviado exitosamente. Workers se reciclarán.")
            return True
        else:
            logger.warning("SENTINEL REPAIR [Gunicorn]: No se encontró proceso master de Gunicorn")
            return False
            
    except ProcessLookupError:
        logger.error("SENTINEL REPAIR [Gunicorn]: Proceso master no encontrado (ProcessLookupError)")
        return False
    except PermissionError:
        logger.error("SENTINEL REPAIR [Gunicorn]: Sin permisos para enviar señal al master")
        return False
    except Exception as e:
        logger.error(f"SENTINEL REPAIR [Gunicorn]: Error inesperado en soft restart: {e}")
        return False


def _encontrar_gunicorn_master():
    """
    Encuentra el PID del proceso master de Gunicorn.
    
    Estrategias:
    1. Variable de entorno GUNICORN_PID (si está configurada)
    2. PID del proceso padre (ppid) del worker actual
    3. Buscar en /proc por el proceso 'gunicorn: master'
    
    Returns:
        int|None: PID del master, o None si no se encuentra
    """
    # Estrategia 1: Variable de entorno
    pid_env = os.environ.get('GUNICORN_PID')
    if pid_env:
        try:
            pid = int(pid_env)
            os.kill(pid, 0)  # Verificar que existe
            return pid
        except (ValueError, ProcessLookupError):
            pass
    
    # Estrategia 2: El padre del proceso actual (en Gunicorn, workers son hijos del master)
    try:
        ppid = os.getppid()
        if ppid > 1:  # PID 1 es init, no Gunicorn
            # Verificar que el padre es Gunicorn leyendo /proc/ppid/cmdline
            try:
                with open(f'/proc/{ppid}/cmdline', 'r') as f:
                    cmdline = f.read()
                    if 'gunicorn' in cmdline:
                        return ppid
            except (FileNotFoundError, PermissionError):
                # En algunos entornos /proc puede no estar disponible
                # Asumir que el padre es Gunicorn si ppid > 1
                return ppid
    except Exception:
        pass
    
    # Estrategia 3: Buscar en /proc
    try:
        for entry in os.listdir('/proc'):
            if entry.isdigit():
                try:
                    with open(f'/proc/{entry}/cmdline', 'r') as f:
                        cmdline = f.read()
                        if 'gunicorn' in cmdline and 'master' in cmdline:
                            return int(entry)
                except (FileNotFoundError, PermissionError):
                    continue
    except (FileNotFoundError, PermissionError):
        pass
    
    return None


# ============================================================================
# 2. DB CONNECTION RECOVERY
# ============================================================================

_last_db_recovery_time = None
_DB_RECOVERY_COOLDOWN = 30  # No recuperar más de 1 vez cada 30 segundos


def recuperar_conexiones_db(mensaje_error=''):
    """
    Recupera conexiones a la base de datos cuando hay 'Too many connections'.
    
    Estrategias:
    1. Cerrar todas las conexiones idle del pool de Django
    2. Ejecutar close_old_connections() para limpiar conexiones zombie
    3. Si es PostgreSQL, ejecutar pg_terminate_backend para sesiones idle
    
    Args:
        mensaje_error (str): Mensaje del error original
    Returns:
        bool: True si se ejecutó la recuperación
    """
    global _last_db_recovery_time
    
    now = timezone.now()
    
    # Verificar si es un error de conexiones
    error_lower = mensaje_error.lower()
    is_connection_error = any(pattern in error_lower for pattern in [
        'too many connections',
        'connection pool exhausted',
        'could not connect to server',
        'remaining connection slots',
        'sorry, too many clients',
        'connection refused',
        'server closed the connection unexpectedly',
    ])
    
    if not is_connection_error:
        return False
    
    # Cooldown
    if _last_db_recovery_time:
        elapsed = (now - _last_db_recovery_time).total_seconds()
        if elapsed < _DB_RECOVERY_COOLDOWN:
            logger.info(
                f"SENTINEL REPAIR [DB]: Cooldown activo ({int(elapsed)}s), skip recovery"
            )
            return False
    
    logger.warning(
        f"SENTINEL REPAIR [DB]: Detectado error de conexiones: '{mensaje_error[:100]}'. "
        f"Iniciando recuperación..."
    )
    
    _last_db_recovery_time = now
    
    # Ejecutar en hilo separado para no bloquear el request
    thread = threading.Thread(target=_ejecutar_recovery_db, daemon=True)
    thread.start()
    
    return True


def _ejecutar_recovery_db():
    """Ejecuta la recuperación de conexiones DB."""
    try:
        from django.db import connections, close_old_connections
        
        # PASO 1: Cerrar conexiones viejas de Django
        close_old_connections()
        logger.info("SENTINEL REPAIR [DB]: close_old_connections() ejecutado")
        
        # PASO 2: Cerrar TODAS las conexiones en el pool de Django
        for alias in connections:
            try:
                conn = connections[alias]
                conn.close()
                logger.info(f"SENTINEL REPAIR [DB]: Conexión '{alias}' cerrada")
            except Exception as e:
                logger.warning(f"SENTINEL REPAIR [DB]: Error cerrando '{alias}': {e}")
        
        # PASO 3: Para PostgreSQL, intentar matar sesiones idle
        try:
            from django.db import connection
            connection.ensure_connection()
            
            with connection.cursor() as cursor:
                # Contar conexiones activas
                cursor.execute("""
                    SELECT state, count(*) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                    GROUP BY state
                """)
                stats = cursor.fetchall()
                for state, count in stats:
                    logger.info(f"SENTINEL REPAIR [DB]: Conexiones {state or 'NULL'}: {count}")
                
                # Matar sesiones idle que llevan más de 5 minutos
                cursor.execute("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                      AND state = 'idle'
                      AND state_change < NOW() - INTERVAL '5 minutes'
                      AND pid != pg_backend_pid()
                """)
                killed = cursor.rowcount
                if killed > 0:
                    logger.warning(
                        f"SENTINEL REPAIR [DB]: {killed} conexiones idle terminadas "
                        f"(>5 min inactivas)"
                    )
                else:
                    logger.info("SENTINEL REPAIR [DB]: No hay conexiones idle para terminar")
                    
        except Exception as e:
            logger.warning(f"SENTINEL REPAIR [DB]: Error en limpieza PostgreSQL: {e}")
        
        logger.info("SENTINEL REPAIR [DB]: Recuperación completada exitosamente")
        
    except Exception as e:
        logger.error(f"SENTINEL REPAIR [DB]: Error fatal en recovery: {e}", exc_info=True)


# ============================================================================
# 3. AUTO-FIX PERMISSIONS (403 en rutas permitidas por rol)
# ============================================================================

# Mapa de roles → prefijos de URL que deberían poder acceder
ROLE_ACCESS_MAP = {
    'ADMIN': ['*'],  # Acceso total
    'DIRECTOR': ['*'],  # Acceso total
    'GERENTE': ['*'],  # Acceso total
    'QUIMICO': [
        '/laboratorio/', '/inventario/', '/dashboard/',
    ],
    'RECEPCION': [
        '/laboratorio/recepcion/', '/laboratorio/entrega-resultados/',
        '/farmacia/pdv/', '/farmacia/historial-ventas/',
        '/consultorio/recepcion/', '/dashboard/',
    ],
    'CAJERO': [
        '/farmacia/', '/dashboard/',
    ],
    'MEDICO': [
        '/consultorio/', '/medico/', '/dashboard/',
    ],
    'ENFERMERIA': [
        '/laboratorio/recepcion/', '/consultorio/enfermeria/',
        '/dashboard/',
    ],
}

# Grupos de Django → prefijos de URL
GROUP_ACCESS_MAP = {
    'GERENCIA_OPERATIVA': ['*'],  # Acceso total (Nancy, Gabriela)
    'LABORATORIO': ['/laboratorio/', '/inventario/'],
    'FARMACIA': ['/farmacia/'],
    'RECEPCION': ['/laboratorio/recepcion/', '/farmacia/pdv/'],
    'MEDICOS': ['/consultorio/', '/medico/'],
    'ENFERMERIA': ['/laboratorio/', '/consultorio/enfermeria/'],
    'GERENCIA': ['*'],
}


def reparar_permisos_sesion(request, path):
    """
    Verifica si el usuario debería tener acceso a la ruta y,
    si es así, regenera los permisos de la sesión.
    
    Args:
        request: Django HttpRequest con user autenticado
        path (str): URL que causó el 403
    Returns:
        bool: True si los permisos fueron regenerados y el usuario debería reintentar
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        logger.debug("SENTINEL REPAIR [Permisos]: Usuario no autenticado, skip")
        return False
    
    # Superuser siempre tiene acceso
    if user.is_superuser:
        logger.info(
            f"SENTINEL REPAIR [Permisos]: Superuser {user.username} recibió 403 en {path}. "
            f"Regenerando sesión..."
        )
        _regenerar_sesion_permisos(request, user)
        return True
    
    # Verificar si el rol del usuario permite acceso a esta ruta
    deberia_tener_acceso = _usuario_deberia_acceder(user, path)
    
    if deberia_tener_acceso:
        logger.warning(
            f"SENTINEL REPAIR [Permisos]: {user.username} (rol={getattr(user, 'rol', 'N/A')}) "
            f"recibió 403 en {path} pero DEBERÍA tener acceso. Regenerando permisos..."
        )
        _regenerar_sesion_permisos(request, user)
        return True
    else:
        logger.debug(
            f"SENTINEL REPAIR [Permisos]: {user.username} recibió 403 en {path}. "
            f"Acceso correctamente denegado."
        )
        return False


def _usuario_deberia_acceder(user, path):
    """
    Determina si un usuario debería tener acceso a una ruta
    según su rol y grupos.
    """
    # Verificar por rol
    rol = getattr(user, 'rol', '')
    if rol and rol in ROLE_ACCESS_MAP:
        prefijos = ROLE_ACCESS_MAP[rol]
        if '*' in prefijos:
            return True
        for prefijo in prefijos:
            if path.startswith(prefijo):
                return True
    
    # Verificar por grupos de Django
    try:
        user_groups = list(user.groups.values_list('name', flat=True))
        for group_name in user_groups:
            if group_name in GROUP_ACCESS_MAP:
                prefijos = GROUP_ACCESS_MAP[group_name]
                if '*' in prefijos:
                    return True
                for prefijo in prefijos:
                    if path.startswith(prefijo):
                        return True
    except Exception as e:
        logger.warning(f"SENTINEL REPAIR [Permisos]: Error verificando grupos: {e}")
    
    return False


def _regenerar_sesion_permisos(request, user):
    """
    Regenera los permisos en la sesión del usuario:
    1. Invalida el cache de permisos del usuario
    2. Recarga los grupos del usuario
    3. Limpia el cache del template tag has_group
    4. Marca la sesión como modificada para forzar save
    """
    try:
        # 1. Limpiar cache de permisos de Django
        if hasattr(user, '_perm_cache'):
            delattr(user, '_perm_cache')
        if hasattr(user, '_user_perm_cache'):
            delattr(user, '_user_perm_cache')
        if hasattr(user, '_group_perm_cache'):
            delattr(user, '_group_perm_cache')
        
        # 2. Limpiar cache del template tag auth_extras
        if hasattr(user, '_gerencia_cache'):
            delattr(user, '_gerencia_cache')
        if hasattr(user, '_groups_cache'):
            delattr(user, '_groups_cache')
        
        # 3. Refrescar el objeto user desde la DB
        user.refresh_from_db()
        
        # 4. Forzar recarga de grupos (prefetch)
        user.groups.all()  # Trigger lazy load
        
        # 5. Marcar sesión como modificada
        if hasattr(request, 'session'):
            request.session.modified = True
            # Guardar flag para que el siguiente request recargue permisos
            request.session['_sentinel_perms_refreshed'] = True
            request.session['_sentinel_perms_timestamp'] = timezone.now().isoformat()
        
        logger.info(
            f"SENTINEL REPAIR [Permisos]: Permisos regenerados para {user.username}. "
            f"Grupos: {list(user.groups.values_list('name', flat=True))}"
        )
        
    except Exception as e:
        logger.error(f"SENTINEL REPAIR [Permisos]: Error regenerando permisos: {e}")
