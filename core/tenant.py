"""
core/tenant.py
═══════════════════════════════════════════════════════════════════════════════
PRISLAB V6.0 — PILAR 1: AISLAMIENTO ESTRICTO DE DATOS
PRISLAB V8.5 Fase 1 — Shadow Mode: rayos X de consultas sin filtro tenant (log-only).

Motor central de Multi-Tenancy de Row-Level.

Patrón: Thread-Local Context + TenantManager automático.
El tenant se inyecta UNA VEZ en el middleware y automáticamente
filtra TODOS los QuerySets que usen TenantManager.

Shadow Mode (settings.PRISLAB_TENANT_SHADOW_MODE, default True):
  - El ORM sigue comportándose igual (no se bloquea la operación).
  - Si un TenantModel se consulta vía .objects sin empresa en contexto y sin bypass,
    se emite log con stack trace completo (WARNING/ERROR según caso).

CLI: PRISLAB_TENANT_SHADOW_LOG_CLI=1 para registrar stacks fuera de peticiones HTTP.
═══════════════════════════════════════════════════════════════════════════════
"""
import logging
import threading
import traceback
from functools import wraps

from django.db import models
from django.core.exceptions import PermissionDenied
from django.http import Http404

logger = logging.getLogger('core.tenant')


# ─── ESTADO GLOBAL POR HILO ─────────────────────────────────────────────────

_tenant_state = threading.local()


def get_current_empresa():
    """
    Retorna la Empresa del usuario en sesión para el hilo actual.
    Retorna None si no hay usuario autenticado o si el contexto está
    desactivado (ej. tareas Celery, comandos de gestión).
    """
    return getattr(_tenant_state, 'empresa', None)


def set_current_empresa(empresa):
    """Establece la empresa activa del hilo. Llamado por TenantMiddleware."""
    _tenant_state.empresa = empresa


def clear_current_empresa():
    """Limpia el contexto al final del request. Llamado por TenantMiddleware."""
    _tenant_state.empresa = None


def is_tenant_bypassed():
    """
    True si el contexto de tenant está desactivado deliberadamente.
    Se usa en tareas Celery, management commands y superusuario PRISLAB.
    """
    return getattr(_tenant_state, 'bypass', False)


def set_tenant_bypass(value: bool):
    """Activa/desactiva el bypass de tenant para el hilo actual."""
    _tenant_state.bypass = value


def _shadow_settings():
    try:
        from django.conf import settings
        return (
            getattr(settings, 'PRISLAB_TENANT_SHADOW_MODE', True),
            getattr(settings, 'PRISLAB_TENANT_SHADOW_LOG_CLI', False),
            getattr(settings, 'DEBUG', False),
        )
    except Exception:
        return True, False, False


def _get_http_request():
    try:
        from core.middleware import empresa as empresa_mw
        return empresa_mw.get_current_request()
    except Exception:
        return None


def _is_tenant_scoped_model(model):
    """True si el modelo hereda de TenantModel (resuelto en tiempo de llamada)."""
    if model is None or getattr(model._meta, 'abstract', False):
        return False
    m = model._meta.concrete_model if getattr(model._meta, 'proxy', False) else model
    TM = globals().get('TenantModel')
    if TM is None:
        return False
    try:
        return issubclass(m, TM)
    except TypeError:
        return False


def _log_tenant_shadow_unscoped(model):
    """
    Rayos X: consulta TenantManager sin filtro por empresa (empresa=None o bypass no aplica
    al camino de filtrado — aquí solo empresa None sin bypass).
    """
    import os

    shadow_on, log_cli, debug = _shadow_settings()
    if not shadow_on or not _is_tenant_scoped_model(model):
        return

    req = _get_http_request()
    user = getattr(req, 'user', None) if req is not None else None
    auth = bool(getattr(user, 'is_authenticated', False))
    superuser = bool(getattr(user, 'is_superuser', False)) if user is not None else False

    if req is None and not log_cli:
        return

    # v8.5: format_stack() en cada consulta caliente degrada PDV y APIs (502 por timeout).
    # Activar trazas completas solo con PRISLAB_TENANT_SHADOW_FULL_STACK=1.
    full_stack = os.environ.get('PRISLAB_TENANT_SHADOW_FULL_STACK', '').strip().lower() in (
        '1', 'true', 'yes', 'on',
    )
    stack = ''.join(traceback.format_stack()) if full_stack else ''

    if auth and not superuser:
        level = logging.ERROR if not debug else logging.WARNING
        msg = (
            'TENANT_SHADOW_UNSCOPED_QUERY modelo=%s usuario_id=%s username=%s '
            '— TenantModel.objects sin empresa en thread-local (posible fuga o bug de middleware).'
        )
        extra = (model.__name__, getattr(user, 'pk', '?'), getattr(user, 'username', '?'))
    elif superuser:
        level = logging.WARNING
        msg = (
            'TENANT_SHADOW_UNSCOPED_QUERY modelo=%s superuser=%s '
            '— consulta global esperada; revisar si el flujo debe filtrar.'
        )
        extra = (model.__name__, getattr(user, 'username', '?'))
    elif req is not None:
        level = logging.WARNING
        msg = 'TENANT_SHADOW_UNSCOPED_QUERY modelo=%s request_anon_or_sin_usuario=%s'
        extra = (model.__name__, req.path[:120] if hasattr(req, 'path') else '')
    else:
        level = logging.WARNING
        msg = 'TENANT_SHADOW_UNSCOPED_QUERY_CLI modelo=%s (sin HttpRequest; PRISLAB_TENANT_SHADOW_LOG_CLI=1)'
        extra = (model.__name__,)

    suffix = ('\nSTACK:\n' + stack) if stack else ''
    logger.log(level, (msg % extra) + suffix)


# ─── CONTEXT MANAGER PARA BYPASS TEMPORAL ───────────────────────────────────

class tenant_bypass:
    """
    Context manager para ejecutar código sin filtro de tenant.
    Útil en management commands y tareas de mantenimiento.

    Deja huella de auditoría (WARNING) con stack al entrar/salir del contexto.

    Uso:
        with tenant_bypass():
            todos_los_pacientes = Paciente.objects.all()  # sin filtro
    """
    def __enter__(self):
        self._prev = is_tenant_bypassed()
        self._outer = not self._prev
        set_tenant_bypass(True)
        if self._outer:
            stack = ''.join(traceback.format_stack())
            logger.warning(
                'TENANT_BYPASS_ENTER (auditoría Fase 1 v8.5)\nSTACK:\n%s',
                stack,
            )
        return self

    def __exit__(self, *args):
        set_tenant_bypass(self._prev)
        if getattr(self, '_outer', False):
            logger.warning(
                'TENANT_BYPASS_EXIT restaurado bypass_prev=%s',
                self._prev,
            )
        return False


# ─── QUERYSET Y MANAGER MULTI-TENANT ────────────────────────────────────────

class TenantQuerySet(models.QuerySet):
    """
    QuerySet que auto-filtra por empresa_actual del hilo.

    Si empresa_actual es None (usuario no autenticado o bypass activo),
    no aplica ningún filtro adicional.
    """

    def for_current_tenant(self):
        """Aplica el filtro de tenant explícitamente."""
        empresa = get_current_empresa()
        if empresa and not is_tenant_bypassed():
            return self.filter(empresa=empresa)
        return self


class TenantManager(models.Manager):
    """
    Manager que reemplaza el Manager default de modelos multi-tenant.

    IMPORTANTE: get_queryset() filtra automáticamente.
    Para obtener datos sin filtro usa Model.objects_all.all() o tenant_bypass().

    Herencia:
        class MiModelo(TenantModel):
            ...
        # Esto hace que MiModelo.objects.all() solo devuelva registros
        # de la empresa en sesión automáticamente.
    """

    def get_queryset(self):
        empresa = get_current_empresa()
        bypass = is_tenant_bypassed()
        qs = TenantQuerySet(self.model, using=self._db)
        if empresa and not bypass:
            return qs.filter(empresa=empresa)
        # Sin filtro por tenant: operación normal (superuser, Celery, etc.) pero Shadow Mode registra riesgo.
        if not bypass and empresa is None:
            _log_tenant_shadow_unscoped(self.model)
        return qs

    def for_tenant(self, empresa):
        """Fuerza el filtro a una empresa específica (para uso admin/sistema)."""
        return TenantQuerySet(self.model, using=self._db).filter(empresa=empresa)

    def all_tenants(self):
        """Devuelve QuerySet sin filtro de tenant (requiere is_superuser o bypass)."""
        return TenantQuerySet(self.model, using=self._db)


class UnfilteredManager(models.Manager):
    """
    Manager sin filtro de tenant.
    Siempre disponible como Model.objects_all para uso de señales/admin.
    """
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)


# ─── MODELO ABSTRACTO BASE MULTI-TENANT ─────────────────────────────────────

class TenantModel(models.Model):
    """
    Clase base abstracta para todos los modelos que pertenecen a un tenant.

    Al hacer Model.objects.filter(...) o Model.objects.all(),
    el resultado ya viene filtrado por la empresa en sesión.

    También expone Model.objects_all para consultas sin filtro (admin, comandos).

    Uso:
        class Paciente(TenantModel):
            nombre = models.CharField(...)
            # empresa ya viene incluido desde TenantModel
    """
    objects     = TenantManager()    # Auto-filtra por empresa en sesión
    objects_all = UnfilteredManager()  # Sin filtro (admin, señales, Celery)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Auto-asigna empresa si no está establecida."""
        if not getattr(self, 'empresa_id', None):
            empresa = get_current_empresa()
            if empresa:
                self.empresa = empresa
        super().save(*args, **kwargs)


# ─── VERIFICACIÓN DE ACCESO CROSS-TENANT ────────────────────────────────────

def assert_tenant_owns(obj, request=None):
    """
    Verifica que el objeto pertenezca al tenant en sesión.
    Lanza Http404 si el objeto pertenece a otro tenant.

    Uso en vistas:
        paciente = get_object_or_404(Paciente, pk=pk)
        assert_tenant_owns(paciente, request)

    Por qué Http404 y no 403:
        No queremos confirmarle al atacante que el recurso existe.
    """
    empresa_actual = get_current_empresa()
    if not empresa_actual:
        return  # Sin contexto (admin, superusuario), permitir

    obj_empresa = getattr(obj, 'empresa', None) or getattr(obj, 'empresa_id', None)
    if obj_empresa is None:
        return  # El objeto no tiene FK empresa, no aplica

    # Normalizar a ID para comparación
    empresa_id = empresa_actual.pk if hasattr(empresa_actual, 'pk') else empresa_actual
    obj_empresa_id = obj_empresa.pk if hasattr(obj_empresa, 'pk') else obj_empresa

    if empresa_id != obj_empresa_id:
        logger.warning(
            'CROSS-TENANT ATTEMPT: user=%s empresa=%s tried to access '
            '%s.pk=%s (empresa=%s)',
            request.user if request else 'unknown',
            empresa_id,
            obj.__class__.__name__,
            getattr(obj, 'pk', '?'),
            obj_empresa_id,
        )
        raise Http404


def tenant_protected_get(model_class, **kwargs):
    """
    Equivalente a get_object_or_404 con protección de cross-tenant.

    Uso:
        paciente = tenant_protected_get(Paciente, pk=pk_del_url)
        # Si el pk pertenece a otro tenant → Http404 automático
    """
    empresa = get_current_empresa()
    try:
        if empresa and not is_tenant_bypassed():
            return model_class.objects.get(empresa=empresa, **kwargs)
        return model_class.objects_all.get(**kwargs)
    except model_class.DoesNotExist:
        raise Http404


# ─── DECORADORES DE VISTA ────────────────────────────────────────────────────

def tenant_required(view_func):
    """
    Decorador de vista que verifica que el usuario tenga empresa asignada.
    Si no la tiene, redirige a login.

    Uso:
        @tenant_required
        def mi_vista(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        if not get_current_empresa() and not request.user.is_superuser:
            logger.error(
                'TENANT_REQUIRED: user=%s sin empresa asignada intentó acceder a %s',
                request.user, request.path,
            )
            raise PermissionDenied('Usuario sin empresa asignada.')

        return view_func(request, *args, **kwargs)
    return wrapper
