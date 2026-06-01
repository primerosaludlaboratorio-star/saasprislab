"""
Módulo de Bienestar Mejorado con Privacidad Total y Protocolo de Alerta Roja.
Inspirado en 'Yana' - Privacidad absoluta con protección de riesgo.
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q

from core.models import (
    Empresa, Usuario,
    ConversacionBienestar, AlertaBienestar,
)


@login_required
def chat_bienestar(request):
    """Chat confidencial con PRIS en el módulo de bienestar."""
    empresa = getattr(request.user, 'empresa', None)

    # Solo los propios mensajes del usuario (privacidad total)
    conversaciones = ConversacionBienestar.objects.filter(
        usuario=request.user
    ).order_by('fecha_creacion')[:100]

    return render(request, 'bienestar/chat.html', {
        'empresa': empresa,
        'conversaciones': conversaciones,
    })


@login_required
@require_http_methods(["POST"])
def enviar_mensaje_bienestar(request):
    """
    Envía un mensaje al chat de bienestar.
    Detecta patrones de riesgo y genera AlertaBienestar silenciosa si procede.
    """
    empresa = getattr(request.user, 'empresa', None)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, AttributeError):
        data = {}
    mensaje = data.get('mensaje', request.POST.get('mensaje', '')).strip()

    if not mensaje:
        return JsonResponse({'status': 'error', 'mensaje': 'Mensaje vacío'}, status=400)

    # Guardar mensaje del usuario
    ConversacionBienestar.objects.create(
        usuario=request.user,
        empresa=empresa,
        rol=ConversacionBienestar.ROL_USUARIO,
        mensaje=mensaje,
        estado_salud=ConversacionBienestar.ESTADO_NORMAL,
    )

    # Detección de riesgo por palabras clave
    palabras_critico = [
        'suicidio', 'matar', 'morir', 'acabar con todo', 'desaparecer',
        'no puedo más', 'no aguanto', 'sin esperanza', 'sin salida',
        'abuso', 'violencia', 'amenaza', 'miedo extremo',
    ]
    palabras_alto = [
        'depresión', 'ansiedad extrema', 'pánico', 'desesperación',
        'no puedo dormir', 'no como', 'no tengo ganas', 'todo está mal',
    ]

    msg_lower = mensaje.lower()
    nivel_riesgo = AlertaBienestar.NIVEL_BAJO
    estado_conv  = ConversacionBienestar.ESTADO_NORMAL

    for p in palabras_critico:
        if p in msg_lower:
            nivel_riesgo = AlertaBienestar.NIVEL_CRITICO
            estado_conv  = ConversacionBienestar.ESTADO_ALERTA
            break

    if nivel_riesgo != AlertaBienestar.NIVEL_CRITICO:
        for p in palabras_alto:
            if p in msg_lower:
                nivel_riesgo = AlertaBienestar.NIVEL_ALTO
                estado_conv  = ConversacionBienestar.ESTADO_ATENCION
                break

    # Actualizar estado_salud SOLO en el mensaje recién guardado (no en toda la historia)
    ConversacionBienestar.objects.filter(
        usuario=request.user, empresa=empresa
    ).order_by('-fecha_creacion')[:1].update(estado_salud=estado_conv)

    # Crear alerta si el nivel lo requiere
    if nivel_riesgo in (AlertaBienestar.NIVEL_ALTO, AlertaBienestar.NIVEL_CRITICO):
        AlertaBienestar.objects.create(
            usuario=request.user,
            empresa=empresa,
            nivel=nivel_riesgo,
            descripcion=f"Se detectó mensaje de riesgo {nivel_riesgo} en el chat de bienestar.",
        )

    # Generar respuesta de PRIS
    if nivel_riesgo == AlertaBienestar.NIVEL_CRITICO:
        respuesta = (
            "Entiendo que estás pasando por un momento muy difícil. Tu bienestar es importante. "
            "Quiero que sepas que no estás solo/a. Te recomiendo contactar a un profesional de la salud mental "
            "o a una línea de crisis. Si estás en México, puedes llamar al 800 911 2000 (Línea de la Vida). "
            "Estoy aquí para escucharte y apoyarte."
        )
    elif nivel_riesgo == AlertaBienestar.NIVEL_ALTO:
        respuesta = (
            "Veo que estás pasando por un momento difícil. Es normal sentirse así a veces. "
            "Estoy aquí para escucharte. Recuerda que buscar ayuda es un signo de fortaleza."
        )
    else:
        respuesta = (
            "Gracias por compartir conmigo. Estoy aquí para escucharte y apoyarte. "
            "Tu bienestar es importante para nosotros."
        )

    # Guardar respuesta de PRIS
    ConversacionBienestar.objects.create(
        usuario=request.user,
        empresa=empresa,
        rol=ConversacionBienestar.ROL_PRIS,
        mensaje=respuesta,
        estado_salud=estado_conv,
    )

    return JsonResponse({
        'status': 'success',
        'respuesta': respuesta,
        'nivel_riesgo': nivel_riesgo,
        'privacidad': 'Esta conversación es completamente confidencial. Solo tú puedes verla.',
    })


@login_required
def alertas_bienestar_director(request):
    """Vista para que el Director vea alertas silenciosas (sin datos de identidad)."""
    if not request.user.is_superuser:
        messages.error(request, 'Acceso restringido. Solo disponible para directores.')
        return redirect('home')

    empresa = getattr(request.user, 'empresa', None)

    alertas = AlertaBienestar.objects.filter(
        empresa=empresa,
    ).select_related('usuario').order_by('-fecha_alerta')

    return render(request, 'bienestar/alertas_director.html', {
        'empresa': empresa,
        'alertas': alertas,
    })


@login_required
@require_http_methods(["POST"])
def marcar_alerta_vista(request, alerta_id):
    """Marca una alerta de bienestar como vista por el director."""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'mensaje': 'Acceso restringido'}, status=403)

    empresa = getattr(request.user, 'empresa', None)
    alerta = get_object_or_404(AlertaBienestar, id=alerta_id, empresa=empresa)
    alerta.estado   = AlertaBienestar.ESTADO_VISTA
    alerta.fecha_vista = timezone.now()
    alerta.visto_por   = request.user
    alerta.save(update_fields=['estado', 'fecha_vista', 'visto_por'])

    return JsonResponse({'status': 'success', 'mensaje': 'Alerta marcada como vista'})
