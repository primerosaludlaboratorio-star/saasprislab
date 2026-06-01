"""
Vistas del Módulo de Inteligencia Artificial.
Integración con Google Cloud AI: Vision API, Speech-to-Text, Gemini.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Avg, Sum
from decimal import Decimal
import json
import base64
import os
import logging
from datetime import datetime, timedelta

from .models import CotizacionOCR, TranscripcionVoz

logger = logging.getLogger('ia')
from .forms import ProcesarRecetaForm, TranscribirAudioForm, ConsultaAsistenteForm
from laboratorio.models import Estudio
from core.models import OrdenDeServicio, DetalleOrden
from consultorio.models import ConsultaMedica
from core.models import Paciente


# ========================================
# VISTA 1: DASHBOARD IA
# ========================================

@login_required
def dashboard_ia(request):
    """
    Dashboard principal del módulo IA.
    Muestra estadísticas de uso y accesos rápidos.
    """
    # Estadísticas de OCR
    total_ocr = CotizacionOCR.objects.filter(
        usuario_creador=request.user
    ).count()
    
    ocr_recientes = CotizacionOCR.objects.filter(
        usuario_creador=request.user
    ).order_by('-fecha_creacion')[:5]
    
    # Estadísticas de Transcripción
    total_transcripciones = TranscripcionVoz.objects.filter(
        usuario_creador=request.user
    ).count()
    
    transcripciones_recientes = TranscripcionVoz.objects.filter(
        usuario_creador=request.user
    ).order_by('-fecha_creacion')[:5]
    
    # Promedio de confianza
    promedio_confianza_ocr = CotizacionOCR.objects.filter(
        usuario_creador=request.user
    ).aggregate(Avg('confianza_promedio'))['confianza_promedio__avg'] or 0
    
    promedio_confianza_voz = TranscripcionVoz.objects.filter(
        usuario_creador=request.user
    ).aggregate(Avg('confianza_transcripcion'))['confianza_transcripcion__avg'] or 0
    
    # Estadísticas de la semana
    hace_7_dias = timezone.now() - timedelta(days=7)
    ocr_semana = CotizacionOCR.objects.filter(
        usuario_creador=request.user,
        fecha_creacion__gte=hace_7_dias
    ).count()
    
    transcripciones_semana = TranscripcionVoz.objects.filter(
        usuario_creador=request.user,
        fecha_creacion__gte=hace_7_dias
    ).count()
    
    context = {
        'total_ocr': total_ocr,
        'total_transcripciones': total_transcripciones,
        'ocr_recientes': ocr_recientes,
        'transcripciones_recientes': transcripciones_recientes,
        'promedio_confianza_ocr': round(promedio_confianza_ocr * 100, 1),
        'promedio_confianza_voz': round(promedio_confianza_voz * 100, 1),
        'ocr_semana': ocr_semana,
        'transcripciones_semana': transcripciones_semana,
        'api_configurada': bool(settings.GOOGLE_API_KEY),
    }
    
    return render(request, 'ia/dashboard.html', context)


# ========================================
# VISTA 2: OCR DE RECETAS MÉDICAS
# ========================================

@login_required
def procesar_receta_ocr(request):
    """
    Procesa una imagen de receta médica usando Google Cloud Vision API.
    Extrae texto y sugiere estudios de laboratorio automáticamente.
    """
    if request.method == 'POST':
        form = ProcesarRecetaForm(request.POST, request.FILES)
        if form.is_valid():
            # Crear objeto CotizacionOCR
            cotizacion = form.save(commit=False)
            cotizacion.usuario_creador = request.user
            
            # Procesar imagen con OCR
            imagen = request.FILES['imagen_receta']
            texto_extraido = _extraer_texto_con_vision_api(imagen)
            
            cotizacion.texto_extraido = texto_extraido
            cotizacion.save()
            
            # Procesar con fuzzy matching para detectar estudios
            estudios_detectados = cotizacion.procesar_imagen()
            
            # Redirigir a resultados
            return redirect('ia:resultados_ocr', pk=cotizacion.pk)
    else:
        form = ProcesarRecetaForm()
    
    context = {
        'form': form,
        'api_configurada': bool(settings.GOOGLE_API_KEY),
    }
    
    return render(request, 'ia/ocr/procesar.html', context)


@login_required
def resultados_ocr(request, pk):
    """
    Muestra los resultados del procesamiento OCR.
    """
    cotizacion = get_object_or_404(CotizacionOCR, pk=pk, usuario_creador=request.user)
    
    context = {
        'cotizacion': cotizacion,
        'estudios': cotizacion.estudios_detectados,
        'puede_crear_orden': not cotizacion.orden_asociada,
    }
    
    return render(request, 'ia/ocr/resultados.html', context)


@login_required
@require_http_methods(["POST"])
def crear_orden_desde_ocr(request, pk):
    """
    Crea una orden de laboratorio a partir de los resultados del OCR.
    """
    cotizacion = get_object_or_404(CotizacionOCR, pk=pk, usuario_creador=request.user)
    
    if cotizacion.orden_asociada:
        return JsonResponse({
            'success': False,
            'error': 'Ya existe una orden asociada a esta cotización.'
        }, status=400)
    
    # Obtener datos del formulario
    data = json.loads(request.body)
    paciente_id = data.get('paciente_id')
    estudios_seleccionados = data.get('estudios', [])
    
    if not paciente_id or not estudios_seleccionados:
        return JsonResponse({
            'success': False,
            'error': 'Debe seleccionar un paciente y al menos un estudio.'
        }, status=400)
    
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'success': False, 'error': 'Usuario sin empresa.'}, status=403)

    paciente = get_object_or_404(
        Paciente,
        pk=paciente_id,
        empresa=empresa,
        activo=True,
    )

    from decimal import Decimal as _Dec

    sucursal = getattr(request.user, 'sucursal', None)

    total_orden = _Dec('0')
    with transaction.atomic():
        orden = OrdenDeServicio.objects.create(
            empresa=empresa,
            sucursal=sucursal,
            paciente=paciente,
            responsable_ingreso=request.user,
            total=_Dec('0'),
            anticipo=_Dec('0'),
            estado='PAGADO',
            estado_pago='PAGADO',
            estado_clinico='PENDIENTE_TOMA',
            notas_internas=f'OCR automático. Confianza: {cotizacion.confianza_promedio}%'[:500],
        )
        for estudio_data in estudios_seleccionados:
            estudio = Estudio.objects.get(pk=estudio_data['estudio_id'])
            precio = estudio.precio_base or _Dec('0')
            DetalleOrden.objects.create(
                orden=orden,
                descripcion_linea=(estudio.nombre or '')[:300],
                precio_momento=precio,
            )
            total_orden += precio
        orden.total = total_orden
        orden.save(update_fields=['total'])
        cotizacion.orden_asociada = orden
        cotizacion.save(update_fields=['orden_asociada'])

    return JsonResponse({
        'success': True,
        'orden_id': orden.id,
        'folio': orden.folio_orden or str(orden.id),
    })


# ========================================
# VISTA 3: TRANSCRIPCIÓN DE AUDIO
# ========================================

@login_required
def transcribir_audio(request):
    """
    Transcribe audio médico usando Google Speech-to-Text.
    Extrae entidades clave (síntomas, medicamentos, alergias).
    """
    if request.method == 'POST':
        form = TranscribirAudioForm(request.POST, request.FILES)
        if form.is_valid():
            # Crear objeto TranscripcionVoz
            transcripcion = form.save(commit=False)
            transcripcion.usuario_creador = request.user
            
            # Procesar audio con Speech-to-Text
            audio = request.FILES['audio']
            resultado = _transcribir_audio_con_speech_api(audio)
            
            transcripcion.texto_transcrito = resultado['texto']
            transcripcion.confianza_transcripcion = Decimal(str(resultado['confianza']))
            transcripcion.duracion_audio = resultado['duracion']
            
            # Extraer entidades con Gemini
            entidades = _extraer_entidades_con_gemini(resultado['texto'])
            transcripcion.entidades_extraidas = entidades
            
            transcripcion.save()
            
            # Redirigir a resultados
            return redirect('ia:resultados_transcripcion', pk=transcripcion.pk)
    else:
        form = TranscribirAudioForm()
    
    context = {
        'form': form,
        'api_configurada': bool(settings.GOOGLE_API_KEY),
    }
    
    return render(request, 'ia/voz/transcripcion.html', context)


@login_required
def resultados_transcripcion(request, pk):
    """
    Muestra los resultados de la transcripción de audio.
    """
    transcripcion = get_object_or_404(TranscripcionVoz, pk=pk, usuario_creador=request.user)
    
    context = {
        'transcripcion': transcripcion,
        'entidades': transcripcion.entidades_extraidas,
    }
    
    return render(request, 'ia/voz/resultados.html', context)


# ========================================
# VISTA 4: ASISTENTE MÉDICO CON GEMINI
# ========================================

@login_required
def asistente_medico(request):
    """
    Chat con asistente médico usando Gemini.
    Responde preguntas sobre diagnósticos, tratamientos, etc.
    """
    if request.method == 'POST':
        form = ConsultaAsistenteForm(request.POST)
        if form.is_valid():
            pregunta = form.cleaned_data['pregunta']
            contexto = form.cleaned_data.get('contexto', '')
            
            # Consultar a Gemini
            respuesta = _consultar_gemini_asistente(pregunta, contexto)
            
            context = {
                'form': form,
                'pregunta': pregunta,
                'respuesta': respuesta,
                'api_configurada': bool(settings.GOOGLE_API_KEY),
            }
            
            return render(request, 'ia/asistente/chat.html', context)
    else:
        form = ConsultaAsistenteForm()
    
    context = {
        'form': form,
        'api_configurada': bool(settings.GOOGLE_API_KEY),
    }
    
    return render(request, 'ia/asistente/chat.html', context)


@login_required
@require_http_methods(["POST"])
def api_consultar_asistente(request):
    """
    API endpoint para consultas al asistente (usado por Pris).
    """
    try:
        data = json.loads(request.body)
        pregunta = data.get('pregunta', '')
        contexto = data.get('contexto', '')
        
        if not pregunta:
            return JsonResponse({
                'success': False,
                'error': 'Debe proporcionar una pregunta.'
            }, status=400)
        
        # Consultar a Gemini
        respuesta = _consultar_gemini_asistente(pregunta, contexto)
        
        return JsonResponse({
            'success': True,
            'respuesta': respuesta
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ========================================
# VISTA 5: ANÁLISIS INTELIGENTE CON GEMINI
# ========================================

@login_required
@require_http_methods(["POST"])
def analizar_sintomas(request):
    """
    Analiza síntomas del paciente y sugiere diagnósticos.
    """
    try:
        data = json.loads(request.body)
        sintomas = data.get('sintomas', '')
        historial = data.get('historial', '')
        
        if not sintomas:
            return JsonResponse({
                'success': False,
                'error': 'Debe proporcionar síntomas.'
            }, status=400)
        
        # Analizar con Gemini
        analisis = _analizar_sintomas_con_gemini(sintomas, historial)
        
        return JsonResponse({
            'success': True,
            'analisis': analisis
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def verificar_interacciones(request):
    """
    Verifica interacciones medicamentosas usando Gemini.
    """
    try:
        data = json.loads(request.body)
        medicamentos = data.get('medicamentos', [])
        
        if not medicamentos:
            return JsonResponse({
                'success': False,
                'error': 'Debe proporcionar al menos un medicamento.'
            }, status=400)
        
        # Verificar con Gemini
        interacciones = _verificar_interacciones_con_gemini(medicamentos)
        
        return JsonResponse({
            'success': True,
            'interacciones': interacciones
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ========================================
# FUNCIONES AUXILIARES (Google Cloud APIs)
# ========================================

def _extraer_texto_con_vision_api(imagen):
    """
    Extrae texto de una imagen usando Google Cloud Vision API.
    PLACEHOLDER: Se activará cuando se configuren las APIs.
    """
    if not settings.GOOGLE_API_KEY:
        return _extraer_texto_fallback(imagen)
    
    try:
        # Implementar cuando el usuario configure GOOGLE_CLOUD_VISION en GCP.
        # from google.cloud import vision
        # client = vision.ImageAnnotatorClient()
        # image = vision.Image(content=imagen.read())
        # response = client.text_detection(image=image)
        # return response.text_annotations[0].description if response.text_annotations else ''
        
        # Por ahora, usar fallback
        return _extraer_texto_fallback(imagen)
    except Exception as e:
        logger.warning("Error en Vision API: %s", e)
        return _extraer_texto_fallback(imagen)


def _extraer_texto_fallback(imagen):
    """
    Fallback cuando no hay API configurada.
    Simula extracción de texto.
    """
    return """
    RECETA MÉDICA
    
    Paciente: [Nombre del paciente]
    Fecha: {fecha}
    
    INDICACIONES:
    - Biometría Hemática Completa
    - Química Sanguínea (6 elementos)
    - Examen General de Orina
    - Perfil Lipídico
    
    OBSERVACIONES:
    Ayuno de 8-12 horas previo a la toma de muestra.
    """.format(fecha=datetime.now().strftime('%Y-%m-%d'))


def _transcribir_audio_con_speech_api(audio):
    """
    Transcribe audio usando Google Speech-to-Text API.
    PLACEHOLDER: Se activará cuando se configuren las APIs.
    """
    if not settings.GOOGLE_API_KEY:
        return _transcribir_audio_fallback(audio)
    
    try:
        # Implementar cuando el usuario configure GOOGLE_CLOUD_VISION en GCP.
        # from google.cloud import speech_v1
        # client = speech_v1.SpeechClient()
        # audio_content = audio.read()
        # audio_obj = speech_v1.RecognitionAudio(content=audio_content)
        # config = speech_v1.RecognitionConfig(...)
        # response = client.recognize(config=config, audio=audio_obj)
        # return {
        #     'texto': response.results[0].alternatives[0].transcript,
        #     'confianza': response.results[0].alternatives[0].confidence,
        #     'duracion': len(audio_content) // 16000  # Estimación
        # }
        
        # Por ahora, usar fallback
        return _transcribir_audio_fallback(audio)
    except Exception as e:
        logger.warning("Error en Speech-to-Text API: %s", e)
        return _transcribir_audio_fallback(audio)


def _transcribir_audio_fallback(audio):
    """
    Fallback cuando no hay API configurada.
    """
    return {
        'texto': 'El paciente presenta dolor abdominal desde hace 3 días. Refiere náuseas ocasionales. Niega fiebre. Antecedentes de gastritis. Solicita biometría hemática y química sanguínea.',
        'confianza': 0.85,
        'duracion': 45
    }


def _extraer_entidades_con_gemini(texto):
    """
    Extrae entidades médicas del texto usando Gemini.
    """
    # Obtener API key
    api_key = (
        getattr(settings, 'GOOGLE_API_KEY', None) or
        getattr(settings, 'GEMINI_API_KEY', None) or
        os.environ.get('GOOGLE_API_KEY') or
        os.environ.get('GEMINI_API_KEY')
    )
    
    if not api_key:
        logger.warning("API key de Gemini no configurada para extracción de entidades")
        return _extraer_entidades_fallback(texto)
    
    try:
        from core.utils.gemini_client import get_gemini_client
        client = get_gemini_client()

        prompt = f"""Extrae entidades médicas del siguiente texto y devuelve un JSON:
{{
    "sintomas": ["lista"],
    "duracion": "texto",
    "antecedentes": ["lista"],
    "alergias": ["lista"],
    "medicamentos_actuales": ["lista"],
    "estudios_solicitados": ["lista"]
}}

Texto: {texto}

Responde SOLO el JSON."""

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={'temperature': 0.3, 'max_output_tokens': 1000}
        )
        resultado = json.loads(response.text)
        logger.info("Extracción de entidades exitosa")
        return resultado
        
    except Exception as e:
        logger.error(f"Error en Gemini API: {e}", exc_info=True)
        return _extraer_entidades_fallback(texto)


def _extraer_entidades_fallback(texto):
    """
    Fallback para extracción de entidades.
    """
    return {
        'sintomas': ['dolor abdominal', 'náuseas'],
        'duracion': '3 días',
        'antecedentes': ['gastritis'],
        'alergias': [],
        'medicamentos_actuales': [],
        'estudios_solicitados': ['biometría hemática', 'química sanguínea']
    }


def _consultar_gemini_asistente(pregunta, contexto=''):
    """
    Consulta al asistente médico usando Gemini.
    """
    # Obtener API key de múltiples fuentes posibles
    api_key = (
        getattr(settings, 'GOOGLE_API_KEY', None) or
        getattr(settings, 'GEMINI_API_KEY', None) or
        os.environ.get('GOOGLE_API_KEY') or
        os.environ.get('GEMINI_API_KEY')
    )
    
    if not api_key:
        logger.warning("API key de Gemini no configurada, usando fallback")
        return _consultar_asistente_fallback(pregunta)
    
    try:
        from core.utils.gemini_client import get_gemini_client
        client = get_gemini_client()

        prompt = f"""Eres un asistente médico experto en PRISLAB.
{contexto}

Pregunta del usuario: {pregunta}

Responde de manera clara, concisa y profesional."""

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={'temperature': 0.5, 'max_output_tokens': 1500}
        )
        logger.info(f"Consulta a Gemini exitosa para: {pregunta[:50]}...")
        return response.text
        
    except Exception as e:
        logger.error(f"Error en Gemini API: {e}", exc_info=True)
        return _consultar_asistente_fallback(pregunta)


def _consultar_asistente_fallback(pregunta):
    """
    Fallback para consultas al asistente.
    """
    respuestas_comunes = {
        'diabetes': 'La diabetes tipo 2 se diagnostica mediante:\n- Glucosa en ayuno ≥126 mg/dL\n- HbA1c ≥6.5%\n- Glucosa al azar ≥200 mg/dL con síntomas\n\nSe recomienda confirmar con pruebas repetidas.',
        'hipertension': 'La hipertensión arterial se define como:\n- Sistólica ≥140 mmHg o\n- Diastólica ≥90 mmHg\n\nTratamiento inicial: modificación del estilo de vida + IECA o ARA-II.',
    }
    
    pregunta_lower = pregunta.lower()
    for key, respuesta in respuestas_comunes.items():
        if key in pregunta_lower:
            return respuesta
    
    return f"Asistente IA (modo demo): Para responder a '{pregunta}', configure las APIs de Google Cloud."


def _analizar_sintomas_con_gemini(sintomas, historial):
    """
    Analiza síntomas y sugiere diagnósticos con Gemini.
    PLACEHOLDER: Se activará cuando se configuren las APIs.
    """
    if not settings.GOOGLE_API_KEY:
        return {
            'diagnósticos_probables': [
                'Gastroenteritis aguda',
                'Síndrome de intestino irritable',
                'Dispepsia funcional'
            ],
            'estudios_recomendados': [
                'Biometría hemática completa',
                'Coprocultivo',
                'Parásitos en heces'
            ],
            'nivel_urgencia': 'MODERADO',
            'recomendaciones': [
                'Hidratación oral abundante',
                'Dieta blanda',
                'Reposo relativo',
                'Valorar antibioticoterapia según resultados'
            ]
        }
    
    # Stub activo. Implementar con Gemini cuando se activen las APIs de IA clinica.
    return {}


def _verificar_interacciones_con_gemini(medicamentos):
    """
    Verifica interacciones medicamentosas con Gemini.
    PLACEHOLDER: Se activará cuando se configuren las APIs.
    """
    if not settings.GOOGLE_API_KEY:
        return {
            'interacciones_encontradas': 0,
            'interacciones': [],
            'advertencias': [],
            'nivel_riesgo': 'BAJO'
        }
    
    # Stub activo. Implementar con Gemini cuando se activen las APIs de IA clinica.
    return {}
