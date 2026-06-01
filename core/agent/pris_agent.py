"""
PRIS-JARVIS Agent — Motor de ejecución con RBAC
================================================
Registro de herramientas (Function Calling), escudo de permisos y contexto.
Cada herramienta está mapeada a permisos Django; si el usuario no tiene permiso,
Pris responde con mensaje de autorización.
"""
import logging
from typing import Any, Callable, Dict, Optional, Tuple

from django.contrib.auth import get_user_model
from django.utils import timezone

logger = logging.getLogger('core')

User = get_user_model()


# ─── Registro de herramientas: nombre -> {permiso, descripcion, ejecutor} ─────────
# permiso: str o None (None = sin restricción, solo login)
# ejecutor: callable(args, empresa, user) -> dict
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_tool(
    name: str,
    permission: Optional[str] = None,
    required_groups: Optional[list] = None,
    description: str = "",
):
    """Decorador para registrar una herramienta con su permiso RBAC."""
    def decorator(func: Callable):
        TOOL_REGISTRY[name] = {
            "permission": permission,
            "required_groups": required_groups or [],
            "description": description,
            "executor": func,
        }
        return func
    return decorator


# ─── Validador RBAC (Escudo de Permisos) ────────────────────────────────────────

def can_execute_tool(user, tool_name: str) -> Tuple[bool, str]:
    """
    Verifica si el usuario puede ejecutar la herramienta.
    Retorna (puede_ejecutar, mensaje_error).
    """
    if not user or not user.is_authenticated:
        return False, "Debe iniciar sesión para usar esta función."

    if user.is_superuser:
        return True, ""

    if tool_name not in TOOL_REGISTRY:
        return False, f"Herramienta '{tool_name}' no disponible."

    reg = TOOL_REGISTRY[tool_name]
    perm = reg.get("permission")
    groups = reg.get("required_groups", [])

    if perm and not user.has_perm(perm):
        return False, (
            "Disculpe, pero su rol no tiene autorización para esta acción. "
            f"Se requiere el permiso: {perm}."
        )

    if groups and not user.groups.filter(name__in=groups).exists():
        return False, (
            "Disculpe, pero su rol no tiene autorización para esta acción. "
            f"Se requiere uno de los grupos: {', '.join(groups)}."
        )

    return True, ""


# ─── Contexto PRIS (quién, permisos, sucursal, pantalla) ────────────────────────

def get_pris_context(request) -> dict:
    """
    Construye el contexto para PRIS: usuario, empresa, grupos, URL actual.
    Usado por el middleware y por el endpoint de chat.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {
            "usuario": None,
            "empresa": None,
            "grupos": [],
            "modulo": "Sistema general",
            "url": getattr(request, 'path', '') or '',
            "es_superuser": False,
        }

    empresa = getattr(user, 'empresa', None)
    grupos = list(user.groups.values_list('name', flat=True))
    path = getattr(request, 'path', '') or ''

    modulo = "Sistema general"
    if '/laboratorio' in path or '/captura' in path:
        modulo = "Laboratorio - Captura de resultados"
    elif '/recepcion' in path:
        modulo = "Recepción"
    elif '/farmacia' in path:
        modulo = "Farmacia"
    elif '/consultorio' in path or '/medico' in path:
        modulo = "Consultorio médico"
    elif '/dashboard' in path or '/home' in path:
        modulo = "Dashboard"
    elif '/cotizacion' in path:
        modulo = "Cotizador"
    elif '/director' in path:
        modulo = "Panel Director"

    return {
        "usuario": user.username,
        "nombre_usuario": user.get_full_name() or user.username,
        "empresa": getattr(empresa, 'nombre', 'PRISLAB') if empresa else 'PRISLAB',
        "empresa_id": getattr(empresa, 'id', None),
        "grupos": grupos,
        "modulo": modulo,
        "url": path,
        "es_superuser": user.is_superuser,
        "fecha_hora": timezone.localtime(timezone.now()).strftime("%A %d de %B de %Y, %H:%M"),
    }


# ─── Clase PrisAgent (orquestador) ──────────────────────────────────────────────

class PrisAgent:
    """
    Agente PRIS-JARVIS: ejecuta herramientas con validación RBAC.
    Uso:
        agent = PrisAgent(request)
        ok, result = agent.execute("consultar_inventario", {"producto": "paracetamol"})
    """

    def __init__(self, request):
        self.request = request
        self.user = getattr(request, 'user', None)
        self.context = get_pris_context(request)

    def execute(self, tool_name: str, args: dict) -> tuple[bool, dict]:
        """
        Ejecuta una herramienta si el usuario tiene permiso.
        Retorna (exito, resultado_dict).
        Si no tiene permiso, resultado_dict tiene {"error": mensaje}.
        """
        puede, msg = can_execute_tool(self.user, tool_name)
        if not puede:
            return False, {"error": msg, "denegado_rbac": True}

        if tool_name not in TOOL_REGISTRY:
            return False, {"error": f"Herramienta '{tool_name}' no registrada."}

        reg = TOOL_REGISTRY[tool_name]
        executor = reg.get("executor")
        if not executor:
            return False, {"error": f"Herramienta '{tool_name}' sin ejecutor."}

        try:
            empresa = getattr(self.user, 'empresa', None)
            resultado = executor(args, empresa, self.user)
            return True, resultado if isinstance(resultado, dict) else {"resultado": resultado}
        except Exception as e:
            logger.exception(f"PRIS-JARVIS tool '{tool_name}' error")
            return False, {"error": str(e)}


# ─── Herramientas de auditoría (ejemplos para Fase 2) ────────────────────────────
# Estas se registrarán cuando se implementen los ejecutores reales.
# Por ahora, el registro se hace en pris_ia.py al importar las tools existentes.
