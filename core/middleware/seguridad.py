"""
core/middleware/seguridad.py
════════════════════════════════════════════════════════════════════════════════
Middlewares de Seguridad PRISLAB — FASE 4

1. SessionTimeoutMiddleware   — Fuerza logout tras N horas de inactividad
2. TenantStorageMiddleware    — Inyecta empresa_slug en contexto Drive (multi-tenant)
3. LogAccesoExpedienteMiddleware — Registra cada acceso a expedientes (NOM-024)

NOM-024-SSA3-2012 / HIPAA: Todo acceso a datos clínicos queda registrado con
usuario, timestamp, IP, sección y tipo de acción.
════════════════════════════════════════════════════════════════════════════════
"""
import logging
import re
import threading
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseRedirect

logger = logging.getLogger('core.seguridad')


# ══════════════════════════════════════════════════════════════════════════════
# 1. SESSION TIMEOUT — Protección de turnos clínicos (8 horas)
# ══════════════════════════════════════════════════════════════════════════════

SESSION_TIMEOUT_SECONDS = getattr(settings, 'SESSION_TIMEOUT_SECONDS', 8 * 3600)  # 8h default

# Rutas que nunca deben disparar el timeout check (login, static, etc.)
_TIMEOUT_EXEMPT_PATTERNS = [
    r'^/static/', r'^/media/', r'^/favicon', r'^/__debug__/',
    r'^/accounts/login/', r'^/login/',
]
_TIMEOUT_EXEMPT_RE = [re.compile(p) for p in _TIMEOUT_EXEMPT_PATTERNS]


class SessionTimeoutMiddleware:
    """
    Cierra automáticamente la sesión de un usuario autenticado que lleva
    más de SESSION_TIMEOUT_SECONDS sin actividad.

    Default: 8 horas (un turno clínico completo).
    Ajustable por empresa en settings: SESSION_TIMEOUT_SECONDS.

    Al expirar, redirige a login con mensaje informativo.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Verificar si la ruta está exenta
            path = request.path_info
            if not any(p.match(path) for p in _TIMEOUT_EXEMPT_RE):
                self._check_timeout(request)

        response = self.get_response(request)

        # Actualizar timestamp de última actividad (solo para usuarios autenticados)
        if request.user.is_authenticated:
            request.session['_last_activity'] = timezone.now().isoformat()

        return response

    def _check_timeout(self, request):
        last_activity_str = request.session.get('_last_activity')
        if not last_activity_str:
            # Primera request de la sesión — inicializar
            request.session['_last_activity'] = timezone.now().isoformat()
            return

        try:
            last_activity = datetime.fromisoformat(last_activity_str)
            if timezone.is_naive(last_activity):
                last_activity = timezone.make_aware(last_activity)

            inactividad = (timezone.now() - last_activity).total_seconds()
            if inactividad > SESSION_TIMEOUT_SECONDS:
                horas = SESSION_TIMEOUT_SECONDS // 3600
                username = request.user.username
                logout(request)
                logger.info(
                    f"SessionTimeout: usuario '{username}' cerrado por inactividad "
                    f"({inactividad/3600:.1f}h > {horas}h límite)"
                )
                # Django redirect — el middleware lo interceptará antes de continuar
                # Nota: para que funcione correctamente, el middleware debe estar ANTES
                # de MessageMiddleware si quieres mostrar un mensaje.
                request.session['timeout_message'] = (
                    f'Tu sesión se cerró automáticamente por inactividad de más de {horas} horas.'
                )
        except Exception as exc:
            logger.warning(f"SessionTimeoutMiddleware error: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. TENANT STORAGE — Inyecta empresa_slug en contexto Drive
# ══════════════════════════════════════════════════════════════════════════════

class TenantStorageMiddleware:
    """
    Inyecta el slug de la empresa del usuario autenticado en el contexto
    de Thread-local de TenantDriveStorage, de forma que cada archivo
    subido quede en su carpeta correspondiente en Drive:
      PRISLAB_Media/{empresa_slug}/...
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        empresa_slug = None
        if request.user.is_authenticated:
            empresa = getattr(request.user, 'empresa', None)
            if empresa:
                # Normalizar slug: nombre → slug seguro para carpeta
                nombre = getattr(empresa, 'nombre', '') or ''
                empresa_slug = (
                    nombre.lower()
                    .replace(' ', '_')
                    .replace('/', '_')
                    .replace('\\', '_')
                )[:50]

        # Inyectar en thread-local del storage
        try:
            from config.storage_backends import set_tenant_context
            set_tenant_context(empresa_slug or 'default')
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en __call__ (seguridad.py)")
            pass

        return self.get_response(request)


# ══════════════════════════════════════════════════════════════════════════════
# 3. LOG ACCESO EXPEDIENTE — Trazabilidad NOM-024-SSA3-2012
# ══════════════════════════════════════════════════════════════════════════════

# Patrones de URL que corresponden a acceso de expediente clínico
_EXPEDIENTE_PATTERNS = [
    # Patrones específicos primero (evitar que genérico capture subdirectorios)
    (re.compile(r'/expediente/(\d+)/editar/'), 'MODIFICACION', 'Expediente — Edición'),
    (re.compile(r'/expediente/(\d+)/pdf/'), 'EXPORTACION', 'Expediente — PDF'),
    (re.compile(r'/expediente/(\d+)/imprimir/'), 'IMPRESION', 'Expediente — Impresión'),
    # Vista unificada de hub de expediente (config/urls.py: pacientes/<pk>/expediente/)
    (re.compile(r'/pacientes/(\d+)/expediente/'), 'LECTURA', 'Expediente — Hub Unificado'),
    (re.compile(r'/paciente/(\d+)/historia-clinica/'), 'LECTURA', 'Historia Clínica'),
    (re.compile(r'/consultorio/expediente/(\d+)/'), 'LECTURA', 'Consultorio — Expediente'),
    (re.compile(r'/laboratorio/orden/(\d+)/resultado/'), 'LECTURA', 'Resultado de Laboratorio'),
    (re.compile(r'/captura-resultados/(\d+)/'), 'MODIFICACION', 'Captura de Resultados'),
    # Genérico al final para no solapar con los específicos de arriba
    (re.compile(r'/expediente/(\d+)/'), 'LECTURA', 'Expediente Clínico'),
]


class LogAccesoExpedienteMiddleware:
    """
    Registra en LogAccesoExpediente cada acceso a vistas de expedientes clínicos.
    NOM-024-SSA3-2012: Todo acceso queda firmado con usuario + IP + timestamp.

    Opera en modo "fire-and-forget": si falla el registro no interrumpe la request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Solo registrar accesos exitosos de usuarios autenticados
        if (
            request.user.is_authenticated
            and request.method == 'GET'
            and response.status_code == 200
        ):
            self._intentar_registro(request)

        return response

    def _intentar_registro(self, request):
        """Detecta si la URL es de expediente y registra acceso. No bloquea."""
        path = request.path_info
        for patron, tipo_acceso, seccion in _EXPEDIENTE_PATTERNS:
            match = patron.search(path)
            if match:
                historia_id_candidato = match.group(1) if match.lastindex else None
                self._registrar(request, tipo_acceso, seccion, historia_id_candidato)
                break  # Solo registrar una vez por request

    def _registrar(self, request, tipo_acceso: str, seccion: str, historia_id: str | None):
        """Crea el registro en DB de forma asíncrona (thread separado para no bloquear)."""
        threading.Thread(
            target=self._crear_log,
            args=(request.user.pk, tipo_acceso, seccion, historia_id,
                  _get_client_ip(request)),
            daemon=True,
        ).start()

    @staticmethod
    def _crear_log(usuario_id: int, tipo_acceso: str, seccion: str,
                   historia_id: str | None, ip: str):
        """Ejecutado en thread separado. Crea LogAccesoExpediente en DB y chequea alertas."""
        try:
            from core.models import LogAccesoExpediente, HistoriaClinica, Usuario

            historia = None
            if historia_id:
                historia = HistoriaClinica.objects.filter(pk=historia_id).first()

            if not historia:
                return

            usuario = Usuario.objects.filter(pk=usuario_id).first()
            LogAccesoExpediente.objects.create(
                historia_clinica=historia,
                usuario=usuario,
                ip_origen=ip or '0.0.0.0',
                tipo_acceso=tipo_acceso,
                seccion_accedida=seccion[:100],
            )

            # ── Alerta CISO: >10 accesos a expedientes en 1 hora ─────────────
            LogAccesoExpedienteMiddleware._verificar_alerta_ciso(usuario_id)

        except Exception as exc:
            logger.warning(f"LogAccesoExpediente no pudo registrarse: {exc}")

    @staticmethod
    def _verificar_alerta_ciso(usuario_id: int, umbral: int = 10, ventana_min: int = 60):
        """
        Revisa si el usuario superó el umbral de accesos a expedientes en la última hora.
        Si supera, notifica al CISO (email + Telegram).
        Usa caché Redis para no consultar DB en cada request.
        """
        try:
            from django.core.cache import cache
            from django.utils import timezone
            from datetime import timedelta
            from core.models import LogAccesoExpediente

            clave_cache = f'alerta_ciso_expediente:{usuario_id}'
            # Evitar notificaciones duplicadas (alerta máximo cada 30 min)
            if cache.get(clave_cache):
                return

            hace_una_hora = timezone.now() - timedelta(minutes=ventana_min)
            count = LogAccesoExpediente.objects.filter(
                usuario_id=usuario_id,
                fecha_acceso__gte=hace_una_hora,
            ).count()

            if count > umbral:
                cache.set(clave_cache, True, timeout=1800)  # silenciar 30 min
                # Notificar en background (no bloquear el thread actual)
                threading.Thread(
                    target=_disparar_alerta_ciso,
                    args=(usuario_id, count, ventana_min),
                    daemon=True,
                ).start()
        except Exception as exc:
            logger.warning(f'_verificar_alerta_ciso error: {exc}')


def _get_client_ip(request) -> str:
    """
    Extrae la IP real del cliente. Usa REMOTE_ADDR (la IP que Nginx ve
    directamente, no falsificable por el cliente) — este valor alimenta
    alertas CISO de acceso masivo a expedientes (NOM-024) y no debe
    depender de un header que el cliente puede manipular.
    """
    return request.META.get('REMOTE_ADDR', '')


def _disparar_alerta_ciso(usuario_id: int, count: int, ventana_min: int):
    """Llama a la función de alerta del módulo 2FA (evitar import circular)."""
    try:
        from core.views.autenticacion_2fa import notificar_alerta_ciso_expedientes
        notificar_alerta_ciso_expedientes(usuario_id, count, ventana_min)
    except Exception as exc:
        logger.warning(f'_disparar_alerta_ciso error: {exc}')