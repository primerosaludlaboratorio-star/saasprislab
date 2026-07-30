"""
Contexto de PRIS para las solicitudes web.

La ejecucion de herramientas vive en ``core.agent.tools`` y su dispatcher
activo. Este modulo conserva unicamente el contexto que consume el middleware.
"""

from django.utils import timezone


def get_pris_context(request) -> dict:
    """Construye el contexto de usuario, empresa, modulo y permisos visibles."""
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
        "fecha_hora": timezone.localtime(timezone.now()).strftime(
            "%A %d de %B de %Y, %H:%M"
        ),
    }
