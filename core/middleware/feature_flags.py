"""
core/middleware/feature_flags.py
═══════════════════════════════════════════════════════════════════════════════
PRISLAB V6.0 — PILAR 2: AMPUTACIÓN LÓGICA DE MÓDULOS

Middleware guardián que bloquea peticiones HTTP a módulos que la empresa
NO tiene contratados, devolviendo HTTP 403 con página informativa.

PRIS-Jarvis también es consciente de este middleware: las herramientas de
módulos inactivos se filtran antes de enviarlas al LLM.

MAPA DE RUTAS → MÓDULO:
    Cada URL-prefix queda vinculado a un módulo de ConfiguracionModulos.
    Si el módulo está apagado → 403 inmediato.

EXCEPCIONES (nunca bloquear):
    - Rutas de autenticación (/login/, /logout/)
    - Admin Django (/admin/)
    - Static/media
    - API de heartbeat / health check

DISEÑO:
    EmpresaIdentityMiddleware ya cargó request.modulos_activos.
    Este middleware solo consulta ese dict → sin queries DB adicionales.
═══════════════════════════════════════════════════════════════════════════════
"""
import re
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('core.middleware.feature_flags')


# ─── MAPA: URL-PREFIX → MÓDULO ───────────────────────────────────────────────
# El primer patrón que coincida determina qué módulo se verifica.
# Orden importa: más específico primero.

_ROUTE_MODULE_MAP = [
    # Laboratorio
    (re.compile(r'^/laboratorio/'),         'laboratorio'),
    (re.compile(r'^/captura/'),             'laboratorio'),
    (re.compile(r'^/resultados/'),          'laboratorio'),
    (re.compile(r'^/lista-trabajo/'),       'laboratorio'),
    (re.compile(r'^/control-calidad/'),     'laboratorio'),
    (re.compile(r'^/director/analizadores'), 'laboratorio'),
    (re.compile(r'^/api/hl7/'),             'laboratorio'),
    (re.compile(r'^/api/resultados/'),      'laboratorio'),
    (re.compile(r'^/kiosko/'),              'laboratorio'),
    (re.compile(r'^/consentimiento/'),      'laboratorio'),
    # Farmacia
    (re.compile(r'^/farmacia/'),            'farmacia'),
    (re.compile(r'^/pdv/'),                 'farmacia'),
    (re.compile(r'^/pdv-farmacia/'),        'farmacia'),
    (re.compile(r'^/inventario/'),          'farmacia'),
    (re.compile(r'^/proveedor/'),           'farmacia'),
    # Consultorio / Expediente
    (re.compile(r'^/consultorio/'),         'consultorio'),
    (re.compile(r'^/medico/'),              'consultorio'),
    (re.compile(r'^/receta/'),              'consultorio'),
    (re.compile(r'^/expediente/'),          'expediente'),
    (re.compile(r'^/paciente/expediente/'), 'expediente'),
    # Citas
    (re.compile(r'^/citas/'),               'citas'),
    (re.compile(r'^/agenda/'),              'citas'),
    # RRHH / Nómina / Bienestar
    (re.compile(r'^/rrhh/'),               'rrhh'),
    (re.compile(r'^/nomina/'),             'nomina'),
    (re.compile(r'^/bienestar/'),          'bienestar'),
    (re.compile(r'^/capacitacion/'),       'rrhh'),
    # Contabilidad / Finanzas
    (re.compile(r'^/finanzas/'),           'contabilidad'),
    (re.compile(r'^/contabilidad/'),       'contabilidad'),
    (re.compile(r'^/director/war-room/'),  'war_room'),
    (re.compile(r'^/facturacion/'),        'contabilidad'),
    # IA
    (re.compile(r'^/ia/'),                 'ia'),
    (re.compile(r'^/api/pris/'),           'ia'),
    (re.compile(r'^/api/chat/'),           'ia'),
    # IoT / Kiosko
    (re.compile(r'^/iot/'),                'iot'),
    (re.compile(r'^/kiosko/'),             'iot'),
]

# Rutas que NUNCA se bloquean (auth, admin, static, health)
_ALWAYS_ALLOWED = re.compile(
    r'^(/login|/logout|/admin|/static|/media|/favicon|/health|'
    r'/service-worker|/__debug__|/api/push|/2fa|/autofactura|'
    r'/verificar|/api/flags)'
)


class FeatureFlagMiddleware:
    """
    Bloquea acceso HTTP a módulos apagados en ConfiguracionModulos.

    Comportamiento:
    - Petición AJAX/API: devuelve JSON 403 con módulo faltante.
    - Petición normal: renderiza 403.html con mensaje institucional.
    - Superusuario PRISLAB: bypassa siempre.
    - Sin empresa asignada: no bloquea (usuario nuevo, login, etc.)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ── Siempre permitir rutas exentas ────────────────────────────────
        if _ALWAYS_ALLOWED.match(request.path_info):
            return self.get_response(request)

        # ── Superusuario PRISLAB: acceso total ────────────────────────────
        if getattr(request, 'user', None) and request.user.is_superuser:
            return self.get_response(request)

        # ── Verificar si la ruta requiere un módulo ────────────────────────
        modulo_requerido = self._get_modulo_requerido(request.path_info)
        if modulo_requerido:
            modulos_activos = getattr(request, 'modulos_activos', {})
            if not modulos_activos.get(modulo_requerido, True):
                return self._bloquear(request, modulo_requerido)

        return self.get_response(request)

    def _get_modulo_requerido(self, path: str):
        """Retorna el módulo requerido para la ruta, o None si no aplica."""
        for pattern, modulo in _ROUTE_MODULE_MAP:
            if pattern.match(path):
                return modulo
        return None

    def _bloquear(self, request, modulo: str):
        """
        Genera la respuesta de bloqueo.
        API → JSON 403. Navegador → Página HTML 403 con mensaje amigable.
        """
        nombre_modulo = _MODULO_NOMBRES.get(modulo, modulo.capitalize())

        logger.warning(
            '[FEATURE_FLAG] BLOQUEADO: user=%s empresa=%s módulo=%s path=%s',
            getattr(request.user, 'username', 'anon'),
            getattr(getattr(request, 'empresa_actual', None), 'nombre', 'N/A'),
            modulo,
            request.path,
        )

        # Respuesta para llamadas AJAX / API
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or 'application/json' in request.headers.get('Accept', '')
            or request.path.startswith('/api/')
        )
        if is_ajax:
            return JsonResponse({
                'error': 'modulo_inactivo',
                'modulo': modulo,
                'mensaje': (
                    f'El módulo "{nombre_modulo}" no está habilitado para tu empresa. '
                    f'Contacta a soporte PRISLAB para activarlo.'
                ),
            }, status=403)

        # Respuesta HTML para navegador
        try:
            return render(request, 'core/modulo_inactivo.html', {
                'modulo': modulo,
                'nombre_modulo': nombre_modulo,
                'empresa': getattr(request, 'empresa_actual', None),
            }, status=403)
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en _bloquear (feature_flags.py)")
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden(
                f'Módulo {nombre_modulo} no disponible en tu plan.'
            )


# ─── NOMBRES LEGIBLES DE MÓDULOS ────────────────────────────────────────────

_MODULO_NOMBRES = {
    'laboratorio':     'Laboratorio Clínico',
    'farmacia':        'Farmacia y PDV',
    'expediente':      'Expediente Clínico',
    'consultorio':     'Consultorio Médico',
    'citas':           'Agenda de Citas',
    'rrhh':            'Gestión de Personal',
    'nomina':          'Nómina',
    'bienestar':       'Bienestar y NOM-035',
    'contabilidad':    'Finanzas y Contabilidad',
    'war_room':        'War Room del Director',
    'ia':              'Inteligencia Artificial (PRIS)',
    'iot':             'IoT y Kiosko',
}


# ─── MIXIN PARA VISTAS ───────────────────────────────────────────────────────

class ModuloRequeridoMixin:
    """
    CBV Mixin para proteger vistas basadas en clases.

    Uso:
        class MiVistaDeLab(ModuloRequeridoMixin, TemplateView):
            modulo_requerido = 'laboratorio'

    Si el módulo está inactivo, devuelve 403.
    """
    modulo_requerido: str = None

    def dispatch(self, request, *args, **kwargs):
        if self.modulo_requerido:
            modulos_activos = getattr(request, 'modulos_activos', {})
            if not modulos_activos.get(self.modulo_requerido, True):
                if request.user.is_superuser:
                    pass  # Superusuario bypassa siempre
                else:
                    nombre = _MODULO_NOMBRES.get(self.modulo_requerido, self.modulo_requerido)
                    try:
                        return render(request, 'core/modulo_inactivo.html', {
                            'modulo': self.modulo_requerido,
                            'nombre_modulo': nombre,
                        }, status=403)
                    except Exception:
                        logging.getLogger(__name__).exception("Error inesperado en dispatch (feature_flags.py)")
                        from django.http import HttpResponseForbidden
                        return HttpResponseForbidden(f'Módulo {nombre} inactivo.')
        return super().dispatch(request, *args, **kwargs)


def modulo_requerido(modulo: str):
    """
    Decorador de vista funcional para proteger por módulo.

    Uso:
        @modulo_requerido('farmacia')
        def mi_vista_farmacia(request):
            ...
    """
    def decorator(view_func):
        from functools import wraps

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_superuser:
                modulos_activos = getattr(request, 'modulos_activos', {})
                if not modulos_activos.get(modulo, True):
                    nombre = _MODULO_NOMBRES.get(modulo, modulo)
                    try:
                        return render(request, 'core/modulo_inactivo.html', {
                            'modulo': modulo,
                            'nombre_modulo': nombre,
                        }, status=403)
                    except Exception:
                        logging.getLogger(__name__).exception("Error inesperado en wrapper (feature_flags.py)")
                        from django.http import HttpResponseForbidden
                        return HttpResponseForbidden(f'Módulo {nombre} inactivo.')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator