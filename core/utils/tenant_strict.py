"""
Resolución de tenant sin fugas cross-tenant.

REGLA: Nunca usar Empresa.objects.first() ni equivalentes implícitos.
La empresa debe venir del usuario autenticado, de sesión explícita (superusuario),
o de un argumento obligatorio en comandos management / scripts.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from django.http import HttpRequest

    from core.models import Empresa


def empresa_desde_request(request: "HttpRequest") -> Optional["Empresa"]:
    """
    Obtiene la empresa del request sin heurísticas peligrosas.

    Orden:
    1. request.user.empresa (usuario estándar con tenant asignado).
    2. Superusuario: solo si fijó `request.session['empresa_activa_id']` (elección explícita).

    No hay fallback a «la primera empresa de la BD».
    """
    from core.models import Empresa

    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return None
    emp = getattr(user, "empresa", None)
    if emp is not None:
        return emp
    if user.is_superuser:
        eid = request.session.get("empresa_activa_id")
        if eid:
            try:
                return Empresa.objects.get(pk=eid)
            except Empresa.DoesNotExist:
                return None
    return None


def empresa_desde_management(options: dict, *, require_arg: bool = True):
    """
    Resuelve empresa para comandos `manage.py`.

    Espera `options['empresa_id']` (int). Si falta y require_arg, lanza CommandError.
    """
    from django.core.management.base import CommandError

    from core.models import Empresa

    eid = options.get("empresa_id")
    if not eid:
        if require_arg:
            raise CommandError(
                "Multi-tenant: indique --empresa-id=<pk>. "
                "No se usa Empresa.objects.first() por seguridad."
            )
        return None
    empresa = Empresa.objects.filter(pk=eid).first()
    if not empresa:
        raise CommandError(f"No existe Empresa con id={eid}.")
    return empresa


def add_argument_empresa_id(parser, *, required: bool = True) -> None:
    """Añade --empresa-id al parser de BaseCommand.add_arguments."""
    parser.add_argument(
        "--empresa-id",
        type=int,
        required=required,
        help="ID de la empresa (tenant). Obligatorio salvo comandos que documenten otra fuente.",
    )
