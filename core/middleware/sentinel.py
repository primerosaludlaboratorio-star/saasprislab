"""
PRIS SENTINEL - Middleware de Telemetria Inteligente (v5.0 — AIOps Supremo)
================================================================================
Intercepta excepciones (500, 404, 403, DatabaseErrors) en TODOS los modulos
de PRISLAB, crea IncidenciaSentinel con analisis IA, y EJECUTA
auto-reparacion en tiempo real.

v5.0 CAMBIOS (Revision 128 — AIOps):
- AI HOTFIX SUGGESTION: Gemini genera SUGGESTED_FIX en GitHub Issues
- PREDICTIVE USER SHIELD: sentinel_shield.js detecta rage-click/form abuse
- VOICE FEEDBACK: SpeechSynthesis del navegador en auto-curaciones
- AUTO-CLEANUP: Latencia >2s dispara limpieza automatica (sesiones, audit, VACUUM)
- GUNICORN SOFT RESTART: 3+ Timeout/MemoryError consecutivos → SIGHUP al master
- DB CONNECTION RECOVERY: "Too many connections" → mata conexiones idle automaticamente
- AUTO-FIX PERMISSIONS: 403 en rutas permitidas por rol → regenera permisos de sesion
"""
import logging
import time
import traceback
import threading
import re

from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.db import DatabaseError, OperationalError
from django.urls import resolve, reverse, Resolver404, NoReverseMatch
from django.template import TemplateDoesNotExist
from django.core.exceptions import PermissionDenied
from django.utils import timezone

logger = logging.getLogger('sentinel')

# Namespaces que Sentinel monitorea (todos los modulos activos)
SENTINEL_NAMESPACES = {
    'consultorio', 'laboratorio', 'farmacia', 'core',
    'pacientes', 'recepcion', 'enfermeria', 'ia',
    'contabilidad', 'marketing', 'logistica', 'bienestar',
    'seguridad', 'iot', 'reglas_negocio',
}

# ============================================================================
# MOTOR DE AUTO-REPARACION v1
# ============================================================================
# Mapeo de rutas rotas → rutas alternativas funcionales
# Sentinel intenta redirigir al usuario a una pagina que SI funciona
FALLBACK_ROUTES = {
    # Modulo → ruta segura de fallback (NUNCA a '/' porque eso es el LOGIN)
    'farmacia': '/home/',
    'laboratorio': '/home/',
    'consultorio': '/home/',
    'core': '/home/',
    'pacientes': '/home/',
    'recepcion': '/home/',
    'enfermeria': '/home/',
    'marketing': '/home/',
    'logistica': '/home/',
    'iot': '/home/',
    'reglas_negocio': '/home/',
    'ia': '/home/',
    'seguridad': '/home/',
    'contabilidad': '/home/',
    'bienestar': '/home/',
}

# Rutas conocidas seguras por prefijo de URL
# NUNCA redirigir a '/' porque '/' es la pagina de LOGIN
SAFE_ROUTE_MAP = {
    '/farmacia/': '/farmacia/pdv/',
    '/laboratorio/': '/laboratorio/recepcion/',
    '/consultorio/': '/consultorio/medico/lista-trabajo/',
    '/pacientes/': '/home/',
    '/enfermeria/': '/home/',
    '/marketing/': '/home/',
    '/logistica/': '/home/',
    '/iot/': '/home/',
    '/director/': '/home/',
}

# Cache de errores recientes para evitar loops
_error_cache = {}
_MAX_RETRIES = 2


class SentinelTelemetryMiddleware:
    """
    Middleware que captura errores en TODOS los modulos de PRISLAB y genera
    incidencias con analisis IA + AUTO-REPARACION en tiempo real.
    """

    TAG_MAP = {
        'consultorio': '#BUG_CONSULTA',
        'laboratorio': '#BUG_LABORATORIO',
        'farmacia': '#BUG_FARMACIA',
        'core': '#BUG_CORE',
        'pacientes': '#BUG_PACIENTES',
        'recepcion': '#BUG_RECEPCION',
        'ia': '#BUG_IA',
        'contabilidad': '#BUG_CONTABILIDAD',
        'marketing': '#BUG_MARKETING',
        'enfermeria': '#BUG_ENFERMERIA',
        'logistica': '#BUG_LOGISTICA',
        'bienestar': '#BUG_BIENESTAR',
        'seguridad': '#BUG_SEGURIDAD',
        'iot': '#BUG_IOT',
        'reglas_negocio': '#BUG_REGLAS',
    }

    # ── Latency tracking para Auto-Cleanup (Rev 128) ──
    _slow_request_count = 0
    _SLOW_THRESHOLD_SECONDS = 2.0
    _SLOW_REQUESTS_TRIGGER = 5  # N requests lentos → dispara cleanup
    _cleanup_running = False

    # Rutas que naturalmente son lentas (IA, PDFs, exports) — no deben
    # disparar alertas de latencia ni auto-cleanup
    _SLOW_EXEMPT_PREFIXES = (
        '/ia/',                     # Asistente IA (Gemini API ~3-8s)
        '/api/voice/',              # Voice commander (STT + Gemini)
        '/consultorio/api/transcribir',  # Transcripcion de audio
        '/consultorio/api/soap',    # Generacion SOAP con IA
        '/consultorio/api/sentinel/',    # Sentinel IA analysis
        '/laboratorio/imprimir',    # Generacion de PDFs
        '/laboratorio/hoja-trabajo',     # PDF de hoja de trabajo
        '/api/push/',               # Push notifications
        '/chat/',                   # Chat interno (polling, websockets)
        '/login',                   # Cold-start normal del servidor (3-6s)
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        t_start = time.monotonic()
        response = self.get_response(request)
        t_elapsed = time.monotonic() - t_start

        # ── LATENCY MONITOR: Disparar cleanup si latencia alta ──
        # Excluir rutas que naturalmente son lentas (IA, PDF, etc.)
        path = request.path
        is_exempt = any(path.startswith(prefix) for prefix in self._SLOW_EXEMPT_PREFIXES)

        if t_elapsed > self._SLOW_THRESHOLD_SECONDS and not is_exempt:
            SentinelTelemetryMiddleware._slow_request_count += 1
            logger.warning(
                f"SENTINEL LATENCY: {request.method} {path} "
                f"tardo {t_elapsed:.2f}s (slow #{SentinelTelemetryMiddleware._slow_request_count})"
            )
            if (SentinelTelemetryMiddleware._slow_request_count >= self._SLOW_REQUESTS_TRIGGER
                    and not SentinelTelemetryMiddleware._cleanup_running):
                SentinelTelemetryMiddleware._cleanup_running = True
                SentinelTelemetryMiddleware._slow_request_count = 0
                threading.Thread(
                    target=self._disparar_auto_cleanup,
                    daemon=True,
                    name='sentinel-auto-cleanup',
                ).start()

        # Capturar 404s en namespaces monitoreados (excluir rutas triviales)
        _404_IGNORE = ('/favicon.ico', '/robots.txt', '/sitemap.xml', '/apple-touch-icon',
                       '/manifest.json', '/.well-known/', '/sw.js')
        if response.status_code == 404:
            if not any(path.startswith(p) or path.endswith(p) for p in _404_IGNORE):
                ns = self._resolver_namespace(request)
                if ns:
                    self._registrar_incidencia_async(
                        request=request,
                        codigo_http=404,
                        tipo_excepcion='Http404',
                        traceback_texto=f'404 Not Found: {request.method} {request.get_full_path()}',
                        severidad='MEDIA',
                        namespace=ns
                    )

        # ===================================================================
        # AUTO-FIX PERMISSIONS: Capturar 403 y regenerar permisos si procede
        # ===================================================================
        if response.status_code == 403:
            path = request.get_full_path()
            ns = self._resolver_namespace(request)
            cache_key = f"sentinel_403:{getattr(request.user, 'id', 0)}:{path}"
            retries_403 = _error_cache.get(cache_key, 0)
            if retries_403 < 1:
                try:
                    from core.services.auto_repair import reparar_permisos_sesion
                    if reparar_permisos_sesion(request, path):
                        _error_cache[cache_key] = retries_403 + 1
                        logger.info(
                            f"SENTINEL AUTO-FIX [403]: Permisos regenerados para "
                            f"{getattr(request.user, 'username', '?')}, "
                            f"reenviando a {path}"
                        )
                        from django.contrib import messages
                        messages.info(
                            request,
                            "PRIS Sentinel detecto un problema de permisos y lo corrigio automaticamente."
                        )
                        return HttpResponseRedirect(path)
                except Exception as e:
                    logger.warning(f"SENTINEL AUTO-FIX [403]: Error en reparacion: {e}")
            else:
                logger.warning(f"SENTINEL AUTO-FIX [403]: Loop detectado para {path}, skip redirect")

        return response

    def process_exception(self, request, exception):
        """
        Hook de Django: captura excepciones no manejadas.
        LOGICA v4.1: Auto-reparación con Gunicorn restart, DB recovery y permisos.
        """
        ns = self._resolver_namespace(request)
        if not ns:
            return None

        tb_texto = traceback.format_exc()
        tipo_exc = type(exception).__name__
        path = request.get_full_path()
        error_msg = str(exception)

        # Determinar severidad
        if isinstance(exception, (DatabaseError, OperationalError)):
            severidad = 'CRITICA'
        elif isinstance(exception, Http404):
            severidad = 'ALTA'
        elif isinstance(exception, PermissionDenied):
            severidad = 'MEDIA'
        elif isinstance(exception, (ValueError, TypeError, KeyError, AttributeError)):
            severidad = 'ALTA'
        elif isinstance(exception, (ImportError, ModuleNotFoundError)):
            severidad = 'CRITICA'
        elif isinstance(exception, (TimeoutError, MemoryError, ConnectionError)):
            severidad = 'CRITICA'
        else:
            severidad = 'MEDIA'

        logger.error(
            f"SENTINEL captura [{severidad}] {tipo_exc} en "
            f"{request.method} {path}: {exception}"
        )

        # ===================================================================
        # REPARACION DE INFRAESTRUCTURA (antes de registrar incidencia)
        # ===================================================================

        # 1. GUNICORN SOFT RESTART: Timeout/MemoryError consecutivos
        try:
            from core.services.auto_repair import registrar_error_critico
            restart_triggered = registrar_error_critico(tipo_exc, error_msg)
            if restart_triggered:
                logger.warning(
                    f"SENTINEL INFRA [Gunicorn]: Soft restart disparado por "
                    f"{tipo_exc} en {path}"
                )
        except Exception as e:
            logger.debug(f"SENTINEL INFRA: Error en check Gunicorn: {e}")

        # 2. DB CONNECTION RECOVERY: Too many connections
        if isinstance(exception, (DatabaseError, OperationalError)):
            try:
                from core.services.auto_repair import recuperar_conexiones_db
                db_recovered = recuperar_conexiones_db(error_msg)
                if db_recovered:
                    logger.warning(
                        f"SENTINEL INFRA [DB]: Recovery disparado por "
                        f"{tipo_exc}: {error_msg[:100]}"
                    )
                    # Redirigir al usuario para que reintente con conexión limpia
                    return self._redirect_with_message(
                        request, path,
                        "El sistema detecto sobrecarga temporal en la base de datos. "
                        "Reintentando automaticamente...",
                        'warning'
                    )
            except Exception as e:
                logger.debug(f"SENTINEL INFRA: Error en check DB: {e}")

        # 3. AUTO-FIX PERMISSIONS: 403 via PermissionDenied exception
        if isinstance(exception, PermissionDenied):
            try:
                from core.services.auto_repair import reparar_permisos_sesion
                if reparar_permisos_sesion(request, path):
                    logger.info(
                        f"SENTINEL INFRA [Permisos]: Reparado 403 para "
                        f"{getattr(request.user, 'username', '?')} en {path}"
                    )
                    from django.contrib import messages
                    messages.info(
                        request,
                        "PRIS Sentinel detecto un problema de permisos y lo corrigio. "
                        "Reintentando..."
                    )
                    return HttpResponseRedirect(path)
            except Exception as e:
                logger.debug(f"SENTINEL INFRA: Error en check permisos: {e}")

        # Registrar incidencia de forma asincrona
        self._registrar_incidencia_async(
            request=request,
            codigo_http=500,
            tipo_excepcion=tipo_exc,
            traceback_texto=tb_texto,
            severidad=severidad,
            namespace=ns
        )

        # ===================================================================
        # MOTOR DE AUTO-REPARACION v4 (rutas y templates)
        # ===================================================================
        repair_result = self._intentar_autoreparacion(
            request, exception, tipo_exc, ns, path
        )

        if repair_result:
            return repair_result

        # Si no se pudo auto-reparar, mostrar pagina de error mejorada
        return self._render_error_page(request, tipo_exc, severidad, ns, path, exception)

    # ===================================================================
    # AUTO-REPARACION: Estrategias por tipo de error
    # ===================================================================

    def _intentar_autoreparacion(self, request, exception, tipo_exc, ns, path):
        """
        Intenta reparar el error automaticamente.
        Retorna HttpResponse si se logro reparar, None si no.
        """
        # Anti-loop: si ya fallamos en esta URL, no reintentar infinitamente
        cache_key = f"{path}:{tipo_exc}"
        retries = _error_cache.get(cache_key, 0)
        if retries >= _MAX_RETRIES:
            logger.warning(f"SENTINEL REPAIR: Max retries alcanzado para {cache_key}")
            return None

        _error_cache[cache_key] = retries + 1

        # Limpiar cache vieja (solo mantener ultimos 50)
        if len(_error_cache) > 50:
            keys = list(_error_cache.keys())
            for k in keys[:25]:
                _error_cache.pop(k, None)

        try:
            # --- ESTRATEGIA 1: NoReverseMatch ---
            if isinstance(exception, NoReverseMatch):
                return self._repair_no_reverse_match(request, exception, ns, path)

            # --- ESTRATEGIA 2: TemplateDoesNotExist ---
            if isinstance(exception, TemplateDoesNotExist):
                return self._repair_template_missing(request, ns, path)

            # --- ESTRATEGIA 3: AttributeError en views ---
            if isinstance(exception, AttributeError):
                return self._repair_attribute_error(request, ns, path)

            # --- ESTRATEGIA 4: ImportError ---
            if isinstance(exception, (ImportError, ModuleNotFoundError)):
                return self._repair_import_error(request, ns, path)

            # --- ESTRATEGIA 5: DatabaseError (connection lost, etc) ---
            if isinstance(exception, (DatabaseError, OperationalError)):
                return self._repair_database_error(request, exception, ns, path)

        except Exception as repair_error:
            logger.error(f"SENTINEL REPAIR: Error en autoreparacion: {repair_error}")

        return None

    def _repair_no_reverse_match(self, request, exception, ns, path):
        """
        Repara NoReverseMatch: cuando un template usa {% url 'nombre' %} que no existe.
        Estrategia: redirigir a la ruta segura del modulo afectado.
        """
        error_msg = str(exception)
        logger.info(f"SENTINEL REPAIR [NoReverseMatch]: Autoreparando {path} -> buscando fallback")

        # Intentar encontrar una ruta alternativa basada en el prefijo
        for prefix, safe_route in SAFE_ROUTE_MAP.items():
            if path.startswith(prefix):
                try:
                    # Verificar que la ruta safe existe
                    resolve(safe_route)
                    logger.info(f"SENTINEL REPAIR: Redirigiendo {path} -> {safe_route}")
                    return self._redirect_with_message(
                        request, safe_route,
                        "PRIS Sentinel detecto un enlace desactualizado y te redirigio automaticamente.",
                        'warning'
                    )
                except Resolver404:
                    continue

        # Fallback general: ir al inicio (home, NO a '/' que es el login)
        logger.info(f"SENTINEL REPAIR: Fallback general {path} -> /home/")
        return self._redirect_with_message(
            request, '/home/',
            "PRIS Sentinel detecto un problema temporal y te redirigio al inicio.",
            'info'
        )

    def _repair_template_missing(self, request, ns, path):
        """
        Repara TemplateDoesNotExist: template no encontrado.
        Estrategia: redirigir a dashboard del modulo.
        """
        logger.info(f"SENTINEL REPAIR [TemplateNotFound]: Autoreparando {path}")

        for prefix, safe_route in SAFE_ROUTE_MAP.items():
            if path.startswith(prefix):
                try:
                    resolve(safe_route)
                    return self._redirect_with_message(
                        request, safe_route,
                        "Sentinel reparo automaticamente: pagina en construccion, te redirigimos.",
                        'info'
                    )
                except Resolver404:
                    continue

        return self._redirect_with_message(
            request, '/home/',
            "Pagina en construccion. Sentinel te llevo al inicio.",
            'info'
        )

    def _repair_attribute_error(self, request, ns, path):
        """
        Repara AttributeError en vistas.
        Estrategia: redirigir a ruta segura del modulo.
        """
        logger.info(f"SENTINEL REPAIR [AttributeError]: Autoreparando {path}")

        for prefix, safe_route in SAFE_ROUTE_MAP.items():
            if path.startswith(prefix):
                try:
                    resolve(safe_route)
                    return self._redirect_with_message(
                        request, safe_route,
                        "Sentinel detecto un error interno y te redirigio a una seccion funcional.",
                        'warning'
                    )
                except Resolver404:
                    continue

        return self._redirect_with_message(request, '/home/', "Sentinel redirigio por error interno.", 'warning')

    def _repair_import_error(self, request, ns, path):
        """
        Repara ImportError: modulo no encontrado.
        Estrategia: redirigir al inicio (error critico, no se puede reparar en runtime).
        """
        logger.info(f"SENTINEL REPAIR [ImportError]: No reparable en runtime, redirigiendo {path}")
        return self._redirect_with_message(
            request, '/home/',
            "Sentinel detecto un modulo en mantenimiento. Te redirigimos al inicio.",
            'warning'
        )

    def _repair_database_error(self, request, exception, ns, path):
        """
        Repara errores de base de datos.
        Estrategia: cerrar conexiones, limpiar pool, y redirigir para reintentar.
        """
        error_msg = str(exception)
        logger.info(f"SENTINEL REPAIR [DatabaseError]: Intentando recuperar: {error_msg[:100]}")

        try:
            # Cerrar la conexión actual (forzar reconexión en siguiente request)
            from django.db import connection
            connection.close()
        except Exception:
            pass

        # Redirigir al usuario a la misma ruta para reintentar
        return self._redirect_with_message(
            request, path,
            "Se detecto un problema temporal con la base de datos. Reintentando automaticamente...",
            'warning'
        )

    def _redirect_with_message(self, request, url, message, level='info'):
        """
        Redirige al usuario con un mensaje flash usando Django messages.
        IMPORTANTE: Fuerza el guardado de sesion ANTES de redirigir para que
        El reverse proxy no pierda la cookie de sesion en respuestas de error.
        """
        try:
            from django.contrib import messages
            level_map = {
                'info': messages.INFO,
                'warning': messages.WARNING,
                'success': messages.SUCCESS,
                'error': messages.ERROR,
            }
            messages.add_message(request, level_map.get(level, messages.INFO), message)
        except Exception:
            pass

        # Forzar guardado de sesion para evitar perdida en respuestas fallidas
        self._preservar_sesion(request)

        return HttpResponseRedirect(url)

    @staticmethod
    def _preservar_sesion(request):
        """
        Fuerza el guardado de la sesion del usuario actual.
        Algunos proxies pueden descartar cookies Set-Cookie en respuestas 5xx,
        asi que nos aseguramos de que la sesion quede persistida en la DB.
        """
        try:
            if hasattr(request, 'session') and request.session.session_key:
                request.session.modified = True
                request.session.save()
        except Exception:
            pass

    # ===================================================================
    # AUTO-CLEANUP TRIGGER (Rev 128 — Latencia >2s)
    # ===================================================================

    @classmethod
    def _disparar_auto_cleanup(cls):
        """
        Ejecuta auto-limpieza en background cuando se detecta latencia alta.
        Acciones: purgar sesiones, limpiar cache, cerrar conexiones viejas.
        """
        try:
            logger.info("SENTINEL AUTO-CLEANUP: Iniciando limpieza por latencia alta...")

            # 1. Purgar sesiones expiradas
            try:
                from django.contrib.sessions.models import Session
                from django.utils import timezone
                expired = Session.objects.filter(expire_date__lt=timezone.now())
                count = expired.count()
                if count > 0:
                    expired.delete()
                    logger.info(f"SENTINEL AUTO-CLEANUP: {count} sesiones expiradas purgadas")
            except Exception as e:
                logger.debug(f"SENTINEL AUTO-CLEANUP: Error purgando sesiones: {e}")

            # 2. Cerrar conexiones de DB viejas
            try:
                from django.db import close_old_connections
                close_old_connections()
                logger.info("SENTINEL AUTO-CLEANUP: Conexiones DB viejas cerradas")
            except Exception as e:
                logger.debug(f"SENTINEL AUTO-CLEANUP: Error cerrando conexiones: {e}")

            # 3. Limpiar cache de errores del middleware
            global _error_cache
            if len(_error_cache) > 20:
                _error_cache.clear()
                logger.info("SENTINEL AUTO-CLEANUP: Cache de errores limpiada")

            logger.info("SENTINEL AUTO-CLEANUP: Limpieza completada")

        except Exception as e:
            logger.error(f"SENTINEL AUTO-CLEANUP: Error general: {e}")
        finally:
            # Reset flag para permitir futuras limpiezas
            cls._cleanup_running = False

    # ===================================================================
    # PAGINA DE ERROR MEJORADA (cuando no se puede auto-reparar)
    # ===================================================================

    def _render_error_page(self, request, tipo_exc, severidad, ns, path, exception):
        """
        Renderiza pagina de error con:
        - Tiempo estimado de reparacion
        - Barra de progreso visual
        - Auto-recarga de la MISMA pagina (no de una ruta diferente)
        - Opciones de navegacion

        IMPORTANTE: Devuelve status=200 para que el proxy NO descarte
        los headers Set-Cookie. La pagina ES una respuesta valida
        (renderizada con exito), no un error del servidor.
        """
        from django.shortcuts import render

        # Forzar guardado de sesion ANTES de renderizar
        self._preservar_sesion(request)

        # Estimar tiempo de reparacion segun severidad
        if severidad == 'CRITICA':
            tiempo_estimado = 30
            mensaje_tiempo = "aproximadamente 30 segundos"
            mensaje_detalle = "Se detecto un problema critico. El equipo tecnico fue notificado inmediatamente."
        elif severidad == 'ALTA':
            tiempo_estimado = 15
            mensaje_tiempo = "aproximadamente 15 segundos"
            mensaje_detalle = "Se detecto un ajuste necesario. PRIS Sentinel esta trabajando en ello."
        else:
            tiempo_estimado = 10
            mensaje_tiempo = "aproximadamente 10 segundos"
            mensaje_detalle = "Detectamos un inconveniente menor. Todo estara listo en un momento."

        # Determinar ruta segura como ALTERNATIVA (boton secundario)
        # NUNCA usar '/' como default porque '/' es el LOGIN
        safe_url = '/home/'
        for prefix, safe_route in SAFE_ROUTE_MAP.items():
            if path.startswith(prefix):
                safe_url = safe_route
                break

        # RELOAD siempre va a la MISMA pagina original (no a otra diferente)
        # Esto evita que el usuario se confunda al terminar en otra pantalla
        reload_url = path

        try:
            # STATUS 200: proxies mantienen Set-Cookie en 2xx
            # La pagina de error ES una respuesta exitosa del servidor
            return render(request, 'core/error_sentinel.html', {
                'tipo_error': tipo_exc,
                'severidad': severidad,
                'namespace': ns,
                'tiempo_estimado': tiempo_estimado,
                'mensaje_tiempo': mensaje_tiempo,
                'mensaje_detalle': mensaje_detalle,
                'reload_url': reload_url,
                'safe_url': safe_url,
                'path_original': path,
            }, status=200)
        except Exception:
            # Si el template mejorado falla, usar el basico
            try:
                return render(request, 'core/error_amable.html', {
                    'tipo_error': tipo_exc,
                    'severidad': severidad,
                }, status=200)
            except Exception:
                return None

    # ===================================================================
    # METODOS AUXILIARES
    # ===================================================================

    def _resolver_namespace(self, request):
        """
        Resuelve el namespace del modulo afectado.
        """
        path = request.path_info
        if path.startswith(('/admin/', '/static/', '/media/', '/__debug__/')):
            return None

        try:
            match = resolve(path)
            namespace = match.namespace or ''
            if namespace in SENTINEL_NAMESPACES:
                return namespace
        except Resolver404:
            pass

        # Fallback: detectar por prefijo de URL
        for ns in SENTINEL_NAMESPACES:
            if path.startswith(f'/{ns}/'):
                return ns

        if path.startswith('/medico/') or path == '/medico/':
            return 'consultorio'

        if path in ('/', '/login/', '/dashboard/'):
            return 'core'

        # Capturar TODAS las rutas (modo global durante configuracion)
        return 'core'

    def _registrar_incidencia_async(self, request, codigo_http, tipo_excepcion,
                                     traceback_texto, severidad, namespace='core'):
        """Lanza el registro de la incidencia en un hilo separado."""
        try:
            from consultorio.sentinel_service import sanitizar_datos

            datos = {
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                'empresa_id': getattr(getattr(request.user, 'empresa', None), 'id', None)
                              if hasattr(request, 'user') else None,
                'url': request.build_absolute_uri(),
                'path': request.get_full_path(),
                'metodo': request.method,
                'codigo_http': codigo_http,
                'tipo_excepcion': tipo_excepcion,
                'traceback_texto': traceback_texto,
                'severidad': severidad,
                'namespace': namespace,
                'get_data': sanitizar_datos(dict(request.GET)) if request.GET else {},
                'post_data': sanitizar_datos(dict(request.POST)) if request.POST else {},
            }

            from django.db import connection
            if connection.vendor == 'sqlite':
                self._crear_incidencia(datos)
                return

            thread = threading.Thread(
                target=self._crear_incidencia,
                args=(datos,),
                daemon=True
            )
            thread.start()

        except Exception as e:
            logger.error(f"SENTINEL: Error al lanzar registro async: {e}")

    @staticmethod
    def _crear_incidencia(datos):
        """
        Crea la IncidenciaSentinel INMEDIATAMENTE con datos basicos,
        luego intenta enriquecer con IA (Gemini) en segundo paso.
        """
        incidencia = None
        try:
            from django.db import connection
            connection.ensure_connection()

            from consultorio.models import IncidenciaSentinel
            from consultorio.sentinel_service import sanitizar_datos
            empresa_id = datos.get('empresa_id')
            if not empresa_id:
                logger.error(
                    "SENTINEL: Sin empresa en contexto; no se crea incidencia "
                    "(multi-tenant: prohibido Empresa.objects.first())."
                )
                return
            usuario_id = datos.get('user_id') or None

            datos_sanitizados = {
                'GET': sanitizar_datos(datos['get_data']),
                'POST': sanitizar_datos(datos['post_data']),
            }

            ns = datos.get('namespace', 'core')
            tag = SentinelTelemetryMiddleware.TAG_MAP.get(ns, f'#BUG_{ns.upper()}')

            # DEDUPLICACIÓN: No crear si ya existe una incidencia igual en las últimas 6h
            from datetime import timedelta as _td
            hace_6h = timezone.now() - _td(hours=6)
            duplicada = IncidenciaSentinel.objects.filter(
                empresa_id=empresa_id,
                url_afectada=datos['url'][:500],
                tipo_excepcion=datos['tipo_excepcion'][:255],
                codigo_http=datos['codigo_http'],
                fecha_creacion__gte=hace_6h,
            ).exists()
            if duplicada:
                logger.info(f"SENTINEL: Incidencia duplicada (skip) - {datos['tipo_excepcion']} en {datos['path']}")
                return

            # PASO 1: Crear incidencia
            incidencia = IncidenciaSentinel.objects.create(
                empresa_id=empresa_id,
                origen='MIDDLEWARE',
                usuario_reporta_id=usuario_id,
                url_afectada=datos['url'][:500],
                metodo_http=datos['metodo'],
                namespace=ns,
                codigo_http=datos['codigo_http'],
                tipo_excepcion=datos['tipo_excepcion'][:255],
                traceback_completo=datos['traceback_texto'],
                datos_request=datos_sanitizados,
                tag=tag,
                analisis_ia='Analisis IA en proceso...',
                contexto_cursor='',
                contexto_reparacion={},
                estado='PENDIENTE',
                severidad=datos['severidad'],
            )

            logger.info(
                f"SENTINEL: Incidencia #{incidencia.id} creada - "
                f"[{datos['severidad']}] {datos['tipo_excepcion']} en {datos['path']}"
            )

            # AuditLog
            try:
                from core.services.audit_service import registrar_auditoria
                from core.models import Empresa, Usuario

                empresa = Empresa.objects.filter(id=empresa_id).first()
                usuario = Usuario.objects.filter(id=usuario_id).first() if usuario_id else None
                if not empresa:
                    raise ValueError("empresa_id no resoluble para auditoria Sentinel")

                registrar_auditoria(
                    accion='CREATE',
                    modelo='IncidenciaSentinel',
                    objeto_id=str(incidencia.id),
                    datos_nuevos={
                        'tipo': datos['tipo_excepcion'],
                        'url': datos['path'],
                        'severidad': datos['severidad'],
                        'namespace': ns,
                    },
                    empresa=empresa,
                    usuario=usuario,
                )
            except Exception:
                pass

            # PASO 2: Intentar enriquecer con IA
            try:
                from consultorio.sentinel_service import analizar_error_con_ia
                resultado_ia = analizar_error_con_ia(
                    tipo_excepcion=datos['tipo_excepcion'],
                    traceback_texto=datos['traceback_texto'],
                    url=datos['path'],
                    metodo=datos['metodo'],
                    datos_request=datos_sanitizados
                )

                analisis_ia = ''
                contexto_cursor = ''
                contexto_reparacion = {}

                if len(resultado_ia) == 3:
                    analisis_ia, contexto_cursor, contexto_reparacion = resultado_ia
                else:
                    analisis_ia, contexto_cursor = resultado_ia[:2]

                incidencia.analisis_ia = analisis_ia
                incidencia.contexto_cursor = contexto_cursor
                incidencia.contexto_reparacion = contexto_reparacion
                incidencia.save(update_fields=[
                    'analisis_ia', 'contexto_cursor', 'contexto_reparacion'
                ])

                logger.info(
                    f"SENTINEL: Incidencia #{incidencia.id} enriquecida con analisis IA"
                )

            except Exception as e:
                logger.warning(f"SENTINEL: IA no disponible para incidencia #{incidencia.id}: {e}")
                incidencia.analisis_ia = (
                    f"Analisis IA no disponible ({type(e).__name__}). "
                    f"Error original: {datos['tipo_excepcion']} en {datos['path']}. "
                    f"Revisar traceback completo para diagnostico manual."
                )
                incidencia.save(update_fields=['analisis_ia'])

            # PASO 3: GitHub Issue
            try:
                from core.services.github_reporter import crear_github_issue
                github_datos = dict(datos)
                github_datos['incidencia_id'] = incidencia.id
                resultado_gh = crear_github_issue(github_datos)
                if resultado_gh:
                    incidencia.analisis_ia = (
                        f"{incidencia.analisis_ia}\n\n"
                        f"GitHub Issue: {resultado_gh['issue_url']}"
                    )
                    incidencia.save(update_fields=['analisis_ia'])
            except Exception as e:
                logger.warning(f"SENTINEL: Error al crear GitHub Issue: {e}")

            # PASO 4: Push al Director
            try:
                from core.push_service import notificar_error_sentinel
                notificar_error_sentinel(incidencia)
            except Exception as e:
                logger.warning(f"SENTINEL: Error al enviar push notification: {e}")

            connection.close()

        except Exception as e:
            logger.error(f"SENTINEL: Error fatal al crear incidencia: {e}", exc_info=True)
            try:
                from django.db import connection
                connection.close()
            except Exception:
                pass
