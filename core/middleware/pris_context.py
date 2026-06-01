"""
PRIS-JARVIS — Middleware de Contexto
=====================================
Inyecta en request.pris_context la información que PRIS necesita:
- Quién habla (user)
- Permisos y sucursal (groups, empresa)
- Pantalla actual (path, módulo)
"""
import logging

from core.agent.pris_agent import get_pris_context

logger = logging.getLogger('core')


class PrisContextMiddleware:
    """
    Middleware que añade request.pris_context para el agente PRIS.
    Debe ejecutarse después de AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.pris_context = get_pris_context(request)
        return self.get_response(request)
