"""
core/views/audio_legal.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoints para sellado y verificación legal de audio/transcripciones.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('core.audio_legal')


@login_required
@require_http_methods(['POST'])
def api_sellar_audio(request):
    """
    Recibe una transcripción de voz desde el cliente,
    genera el hash SHA-256 + timestamp servidor y la guarda en VoiceAuditLog.
    """
    try:
        data = json.loads(request.body)
        transcripcion = (data.get('transcripcion') or '').strip()
        modulo = (data.get('modulo') or 'PRIS').upper()
        duracion = data.get('duracion_segundos')
        url_actual = data.get('url_actual', request.META.get('HTTP_REFERER', ''))

        if not transcripcion:
            return JsonResponse({'error': 'Transcripción vacía'}, status=400)

        empresa = getattr(request.user, 'empresa', None)

        from core.utils.pris_audio_vision import sellar_transcripcion
        resultado = sellar_transcripcion(
            transcripcion=transcripcion,
            usuario=request.user,
            empresa=empresa,
            modulo=modulo,
            duracion_segundos=duracion,
            url_actual=url_actual,
        )
        return JsonResponse({'ok': True, **resultado})
    except Exception as exc:
        logger.error(f'[AudioLegal] Error sellando: {exc}')
        return JsonResponse({'error': str(exc)}, status=500)


@login_required
def api_verificar_integridad_audio(request, registro_id: int):
    """
    Dado un ID de VoiceAuditLog, verifica que el hash
    almacenado coincida con la transcripción guardada.
    Útil para peritaje legal o auditoría.
    """
    try:
        from core.utils.pris_audio_vision import verificar_integridad
        resultado = verificar_integridad(registro_id)
        return JsonResponse(resultado)
    except Exception as exc:
        logging.getLogger(__name__).exception("Error inesperado en api_verificar_integridad_audio (audio_legal.py)")
        return JsonResponse({'error': str(exc)}, status=500)