"""
core/views/feature_flags_admin.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Panel de administración de Feature Flags (Interruptores).
Accesible solo para ADMIN / DIRECTOR / Superusuario.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('core.feature_flags_admin')

_ROLES_PERMITIDOS = {'ADMIN', 'DIRECTOR'}


def _tiene_permiso(user) -> bool:
    if user.is_superuser:
        return True
    return getattr(user, 'rol', '') in _ROLES_PERMITIDOS


@login_required
def panel_feature_flags(request):
    """Renderiza el panel de interruptores del Director."""
    if not _tiene_permiso(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Acceso restringido al Director y Administradores.')

    empresa = getattr(request.user, 'empresa', None)
    from core.services.feature_flags import obtener_todos
    flags = obtener_todos(empresa)

    # Agrupar por categoría
    por_categoria = {}
    for codigo, info in flags.items():
        cat = info['categoria']
        if cat not in por_categoria:
            por_categoria[cat] = []
        por_categoria[cat].append({'codigo': codigo, **info})

    return render(request, 'core/feature_flags/panel.html', {
        'por_categoria': por_categoria,
        'titulo': 'Configuración del Sistema — Interruptores',
    })


@login_required
@require_http_methods(['POST'])
def api_toggle_flag(request, codigo: str):
    """Activa o desactiva un flag via AJAX."""
    if not _tiene_permiso(request.user):
        return JsonResponse({'error': 'Sin permiso'}, status=403)

    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'error': 'Sin empresa asignada'}, status=400)

    import json as _json
    try:
        body = _json.loads(request.body)
        valor = bool(body.get('activo', False))
    except Exception:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    from core.services.feature_flags import activar, desactivar, FLAG_CATALOG
    if codigo not in FLAG_CATALOG:
        return JsonResponse({'error': f'Flag desconocido: {codigo}'}, status=400)

    ok = activar(codigo, empresa, request.user) if valor else desactivar(codigo, empresa, request.user)
    if ok:
        logger.info(f'[Flags] {codigo}={valor} cambiado por {request.user.username}')
        return JsonResponse({
            'ok': True,
            'codigo': codigo,
            'activo': valor,
            'mensaje': f'{"Activado" if valor else "Desactivado"}: {FLAG_CATALOG[codigo]["nombre"]}',
        })
    return JsonResponse({'error': 'No se pudo guardar el cambio'}, status=500)


@login_required
def api_flags_estado(request):
    """API para el widget PRIS — devuelve el estado actual de los flags."""
    empresa = getattr(request.user, 'empresa', None)
    from core.services.feature_flags import obtener_todos
    return JsonResponse({'flags': obtener_todos(empresa)})
