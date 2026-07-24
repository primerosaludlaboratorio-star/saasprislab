"""
core/views/pris_ia/_rbac.py

Verificación de control de acceso basado en roles para herramientas de Prisci.
"""

from ._constants import _TOOL_RBAC, _SUPERUSER_ONLY_TOOLS


def _rol_aliases_usuario(user) -> set[str]:
    rol = (getattr(user, 'rol', '') or '').upper()
    aliases = {rol} if rol else set()
    mapa = {
        'GERENTE': {'GERENCIA', 'GERENCIA_OPERATIVA'},
        'QUIMICO': {'LABORATORIO'},
        'MEDICO': {'MEDICOS'},
        'ADMIN': {'Administrador'},
        'DIRECTOR': {'GERENCIA', 'Administrador'},
    }
    aliases.update(mapa.get(rol, set()))
    return {a for a in aliases if a}


def _verificar_rbac(tool_name: str, user, pris_mode: bool = False, **legacy_kwargs) -> tuple:
    """
    Retorna (permitido, mensaje_denegacion).
    El RBAC se aplica SIEMPRE, incluso en modo operativo completo.
    La confirmación humana es una capa ADICIONAL, no el único mecanismo de seguridad.
    """
    # Acepta el nombre histórico solo para no romper integraciones existentes.
    pris_mode = legacy_kwargs.get('jarvis_mode', pris_mode)
    if not user or not getattr(user, 'is_authenticated', False):
        return False, "No tienes autorizacion para hacer eso. Inicia sesion primero."
    if user.is_superuser:
        return True, ""

    if tool_name in _SUPERUSER_ONLY_TOOLS:
        return False, "Disculpe, esta acción requiere nivel de Superusuario (Director)."
    if tool_name not in _TOOL_RBAC:
        return False, "Esta herramienta no está registrada en el catálogo seguro de PRIS."
    grupos_req = _TOOL_RBAC[tool_name]
    if grupos_req is None:
        return True, ""
    if not grupos_req:
        return False, "Disculpe, esta acción está reservada para el Director del sistema."
    grupos_usuario = set(user.groups.values_list('name', flat=True))
    roles_usuario = _rol_aliases_usuario(user)
    permitidos = set(grupos_req)
    if grupos_usuario.intersection(permitidos) or roles_usuario.intersection(permitidos):
        return True, ""
    return False, (
        "Disculpe, pero su rol no tiene autorización para esta acción. "
        f"Grupos permitidos: {', '.join(grupos_req)}."
    )
