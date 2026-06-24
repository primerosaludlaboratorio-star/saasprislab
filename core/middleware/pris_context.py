"""
PRIS-JARVIS — Middleware de Contexto
=====================================
Inyecta en request.pris_context la información que PRIS necesita:
- Quién habla (user)
- Permisos y sucursal (groups, empresa)
- Pantalla actual (path, módulo)
"""
import logging

logger = logging.getLogger('core')


class PrisContextMiddleware:
    """
    Middleware que añade request.pris_context para el agente PRIS.
    Debe ejecutarse después de AuthenticationMiddleware.
    Import lazy de get_pris_context para evitar que un fallo de import
    en pris_agent rompa cada request del sistema.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        try:
            from core.agent.pris_agent import get_pris_context
            self._get_pris_context = get_pris_context
        except Exception:
            logger.exception("PrisContextMiddleware: no se pudo importar get_pris_context — contexto PRIS desactivado")
            self._get_pris_context = None

    def __call__(self, request):
        if self._get_pris_context is not None:
            try:
                request.pris_context = self._get_pris_context(request)
            except Exception:
                logger.exception("PrisContextMiddleware: error al construir pris_context")
                request.pris_context = {}
        else:
            request.pris_context = {}
        return self.get_response(request)
