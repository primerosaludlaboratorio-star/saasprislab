"""Comprobación única del usuario Escudo Clínico LIMS (PRISLAB_ESCUDO_USUARIO_ID)."""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model


def verificar_escudo_clinico() -> tuple[bool, str]:
    """
    Retorna (True, mensaje_ok) o (False, mensaje_error).
    """
    User = get_user_model()
    raw = getattr(settings, 'PRISLAB_ESCUDO_USUARIO_ID', None)
    if raw is None:
        return False, 'PRISLAB_ESCUDO_USUARIO_ID no está definido.'
    try:
        uid = int(raw)
    except (TypeError, ValueError):
        return False, f'PRISLAB_ESCUDO_USUARIO_ID inválido: {raw!r}'
    u = User.objects.filter(pk=uid, is_active=True).first()
    if not u:
        return False, f'Usuario escudo pk={uid} no existe o está inactivo.'
    return True, f'Escudo OK: pk={uid} username={u.username!r}'
