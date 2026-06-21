import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods

from core.utils.empresa_request import get_empresa_usuario

logger = logging.getLogger('core')


def _empresa_configuracion_o_error(request):
    empresa = get_empresa_usuario(request.user)
    if not empresa:
        return None, JsonResponse({'error': 'Sin empresa'}, status=403)
    return empresa, None


def _puede_administrar_configuracion(user) -> bool:
    if not get_empresa_usuario(user):
        return False
    return user.rol in ('ADMIN', 'DIRECTOR') or user.is_superuser


@login_required
def configuracion_dashboard(request):
    """
    Dashboard maestro de configuración. Incluye widget de consumo de IA.
    """
    empresa = get_empresa_usuario(request.user)
    contexto = {}

    if empresa:
        try:
            from core.utils.ia_resources import consumo_mensual
            from core.utils.ia_cache import estadisticas_cache
            contexto['ia_consumo']  = consumo_mensual(empresa)
            contexto['ia_cache']    = estadisticas_cache(empresa)
            contexto['empresa']     = empresa
            contexto['tiene_byok']  = empresa.tiene_byok_gemini()
            contexto['tiene_drive'] = empresa.tiene_drive_propio()
            cfg = getattr(empresa, 'configuracion_modulos', None)
            contexto['modo_ia']     = cfg.modo_ia if cfg else 'PRODUCCION'
            contexto['modo_ia_choices'] = [
                ('APRENDIZAJE', '🧠 Aprendizaje'),
                ('PRODUCCION',  '🚀 Producción'),
                ('AHORRO_EXTREMO', '💡 Ahorro Extremo'),
            ]
        except Exception as exc:
            logger.warning("configuracion_dashboard: error cargando datos IA — %s", exc)

    return render(request, "core/configuracion_dashboard.html", contexto)


@login_required
@require_http_methods(["GET"])
def api_ia_consumo(request):
    """API JSON: datos de consumo IA del mes actual para el widget del Director."""
    empresa = get_empresa_usuario(request.user)
    if not empresa:
        return JsonResponse({'error': 'Sin empresa asignada'}, status=400)
    try:
        from core.utils.ia_resources import consumo_mensual
        from core.utils.ia_cache import estadisticas_cache
        data = consumo_mensual(empresa)
        data['cache'] = estadisticas_cache(empresa)
        return JsonResponse(data)
    except Exception as exc:
        logger.error("api_ia_consumo: %s", exc)
        return JsonResponse({'error': str(exc)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_cambiar_modo_ia(request):
    """Cambia el modo de consumo IA de la empresa (APRENDIZAJE/PRODUCCION/AHORRO_EXTREMO)."""
    if not _puede_administrar_configuracion(request.user):
        return JsonResponse({'error': 'Sin permiso'}, status=403)
    empresa, error = _empresa_configuracion_o_error(request)
    if error:
        return error
    try:
        datos = json.loads(request.body)
        modo = datos.get('modo', '')
        from core.models import ConfiguracionModulos
        opciones_validas = ['APRENDIZAJE', 'PRODUCCION', 'AHORRO_EXTREMO']
        if modo not in opciones_validas:
            return JsonResponse({'error': f'Modo inválido. Opciones: {opciones_validas}'}, status=400)
        cfg, _ = ConfiguracionModulos.objects.get_or_create(empresa=empresa)
        cfg.modo_ia = modo
        cfg.save(update_fields=['modo_ia'])
        return JsonResponse({'ok': True, 'modo_ia': modo})
    except Exception as exc:
        logger.error("api_cambiar_modo_ia: %s", exc)
        return JsonResponse({'error': str(exc)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_guardar_byok(request):
    """Guarda la API Key BYOK de Gemini del laboratorio (cifrada con Fernet)."""
    if not _puede_administrar_configuracion(request.user):
        return JsonResponse({'error': 'Sin permiso'}, status=403)
    empresa, error = _empresa_configuracion_o_error(request)
    if error:
        return error
    try:
        datos = json.loads(request.body)
        api_key = datos.get('api_key', '').strip()
        drive_folder = datos.get('drive_folder_id', '').strip()
        if api_key:
            empresa.set_byok_gemini_key(api_key)
        if drive_folder:
            empresa.drive_folder_id = drive_folder
        empresa.save(update_fields=['byok_gemini_api_key_enc', 'drive_folder_id'])
        return JsonResponse({
            'ok': True,
            'tiene_byok': empresa.tiene_byok_gemini(),
            'drive_folder_id': empresa.drive_folder_id or '',
        })
    except Exception as exc:
        logger.error("api_guardar_byok: %s", exc)
        return JsonResponse({'error': str(exc)}, status=500)
