"""
Módulo de Bienestar - Espacio Seguro (Inspirado en YANA).
Sistema completo de apoyo emocional con IA.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Avg
from datetime import timedelta, date
import json
import logging
import random

from core.models import Empresa
from .models import DiarioEmocional, RecursoCrecimiento


# ==================== DASHBOARD ====================

@login_required
def dashboard_bienestar(request):
    """Dashboard principal del módulo de bienestar estilo YANA."""
    empresa = getattr(request.user, 'empresa', None)
    usuario = request.user
    
    # Obtener última entrada del diario
    ultima_entrada = DiarioEmocional.objects.filter(usuario=usuario).first()
    
    # Afirmación del día
    afirmaciones_diarias = [
        "Eres más fuerte de lo que crees. 💪",
        "Hoy es un buen día para comenzar. 🌅",
        "Tus emociones son válidas. 🤗",
        "Mereces amor y cuidado. 💜",
        "Cada día es una nueva oportunidad. 🌟",
        "Tu bienestar es importante. ❤️",
        "Está bien no estar bien. 🌸",
        "Eres capaz de superar esto. 🦋",
        "Tu salud mental es prioridad. 🧠",
        "Respira, todo va a estar bien. 🌊",
        "Eres suficiente tal como eres. ✨",
        "Hoy eliges cuidarte. 🌺",
        "Tu progreso es válido. 📈",
        "Mereces descansar. 😴",
        "Eres valioso/a. 💎"
    ]
    
    # Seleccionar afirmación basada en el día
    dia_del_ano = timezone.now().timetuple().tm_yday
    afirmacion_hoy = afirmaciones_diarias[dia_del_ano % len(afirmaciones_diarias)]
    
    # Estadísticas rápidas
    total_entradas = DiarioEmocional.objects.filter(usuario=usuario).count()
    racha_dias = calcular_racha(usuario)
    
    context = {
        'empresa': empresa,
        'afirmacion_hoy': afirmacion_hoy,
        'ultima_entrada': ultima_entrada,
        'total_entradas': total_entradas,
        'racha_dias': racha_dias,
    }
    
    return render(request, 'bienestar/dashboard.html', context)


def calcular_racha(usuario):
    """Calcula la racha de días consecutivos con entradas."""
    hoy = timezone.now().date()
    racha = 0
    
    for i in range(365):  # Máximo 365 días
        fecha = hoy - timedelta(days=i)
        if DiarioEmocional.objects.filter(usuario=usuario, fecha=fecha).exists():
            racha += 1
        else:
            break
    
    return racha


# ==================== CHAT CON PRIS ====================

@login_required
def chat_bienestar(request):
    """Chat confidencial con PRIS para apoyo emocional."""
    empresa = getattr(request.user, 'empresa', None)
    
    return render(request, 'bienestar/chat.html', {
        'empresa': empresa,
    })


@login_required
@require_http_methods(["POST"])
def api_chat_bienestar(request):
    """API para chat de bienestar con PRIS (IA Gemini)."""
    try:
        data = json.loads(request.body)
        mensaje_usuario = data.get('mensaje', '').strip()
        
        if not mensaje_usuario:
            return JsonResponse({
                'ok': False,
                'mensaje': 'Por favor escribe un mensaje'
            }, status=400)
        
        # Obtener respuesta usando el proveedor central de IA.
        try:
            from core.utils.gemini_client import generate_content
            
            # Contexto especializado para bienestar emocional
            contexto_bienestar = """Eres PRIS, una asistente de inteligencia artificial especializada en apoyo emocional y bienestar.

Tu rol es similar a YANA:
- Ofrecer apoyo emocional sin juzgar
- Escuchar activamente y validar sentimientos
- Sugerir técnicas de manejo emocional cuando sea apropiado
- Ser cálida, empática y comprensiva
- Usar lenguaje inclusivo y positivo
- Respuestas CORTAS y directas (máximo 3-4 líneas)

IMPORTANTE:
- Si detectas riesgo de suicidio/autolesión: recomienda URGENTEMENTE buscar ayuda profesional
- Si detectas violencia/abuso: recomienda recursos de apoyo inmediatos
- NO diagnostiques, solo apoyas
- NO des respuestas muy largas
- Sé humana y cercana

Pregunta del usuario: {pregunta}

Responde de forma breve, cálida y empática:"""
            
            prompt_completo = contexto_bienestar.replace('{pregunta}', mensaje_usuario)
            
            # Generar respuesta con el proveedor central configurado para Prisci.
            respuesta_ia = generate_content(
                prompt_completo,
                temperature=0.8,
                max_tokens=300,
            ) or "Lo siento, no pude generar una respuesta. ¿Podrías reformular tu mensaje?"
            
        except Exception as e:
            logger = logging.getLogger('bienestar')
            logger.error(f"Error en chat bienestar: {str(e)}")
            
            # Respuesta de fallback
            respuesta_ia = "Lo siento, estoy teniendo problemas técnicos en este momento. Por favor intenta de nuevo en unos momentos. Si necesitas ayuda urgente, llama al 800 911 2000 (Línea de la Vida)."
        
        # Detectar nivel de riesgo en el mensaje del usuario
        nivel_riesgo = detectar_riesgo_emocional(mensaje_usuario)
        
        return JsonResponse({
            'ok': True,
            'mensaje': respuesta_ia,
            'nivel_riesgo': nivel_riesgo,
        })
        
    except Exception as e:
        logger = logging.getLogger('bienestar')
        logger.error(f"Error crítico en api_chat_bienestar: {str(e)}")
        
        return JsonResponse({
            'ok': False,
            'mensaje': 'Error de conexión. Por favor intenta de nuevo.'
        }, status=500)


def detectar_riesgo_emocional(texto):
    """Detecta nivel de riesgo en el texto del usuario."""
    texto_lower = texto.lower()
    
    # Palabras clave de alto riesgo
    palabras_suicidio = ['suicidio', 'suicidarme', 'matarme', 'acabar con mi vida', 'no quiero vivir']
    palabras_violencia = ['golpea', 'golpear', 'violencia', 'abuso', 'maltrato']
    palabras_acoso = ['acoso', 'acosan', 'hostigamiento', 'hostigan']
    
    # Detectar riesgo
    if any(palabra in texto_lower for palabra in palabras_suicidio):
        return 'ROJO_VIDA'
    elif any(palabra in texto_lower for palabra in palabras_violencia):
        return 'ROJO_VIOLENCIA'
    elif any(palabra in texto_lower for palabra in palabras_acoso):
        return 'ROJO_ACOSO'
    elif any(palabra in ['triste', 'ansiedad', 'angustia', 'estres', 'preocupado'] for palabra in texto_lower.split()):
        return 'AMARILLO'
    else:
        return 'VERDE'


# ==================== DIARIO EMOCIONAL ====================

@login_required
def diario_emocional(request):
    """Vista del diario emocional - Lista de entradas."""
    usuario = request.user
    empresa = getattr(request.user, 'empresa', None)
    
    # Obtener entradas del usuario
    entradas = DiarioEmocional.objects.filter(usuario=usuario).order_by('-fecha')[:30]
    
    # Datos para gráfica de tendencias (últimos 30 días)
    hoy = timezone.now().date()
    tendencias = []
    
    for i in range(30):
        fecha = hoy - timedelta(days=29-i)
        entrada = DiarioEmocional.objects.filter(usuario=usuario, fecha=fecha).first()
        
        # Mapear sentimiento a valor numérico
        valor = 3  # Neutro por defecto
        if entrada and entrada.sentimiento_ia:
            if 'feliz' in entrada.sentimiento_ia.lower() or 'bien' in entrada.sentimiento_ia.lower():
                valor = 5
            elif 'triste' in entrada.sentimiento_ia.lower() or 'mal' in entrada.sentimiento_ia.lower():
                valor = 2
            elif 'ansioso' in entrada.sentimiento_ia.lower():
                valor = 3
        
        tendencias.append({
            'fecha': fecha.strftime('%d/%m'),
            'valor': valor,
            'tiene_entrada': entrada is not None
        })
    
    context = {
        'empresa': empresa,
        'entradas': entradas,
        'tendencias': tendencias,
    }
    
    return render(request, 'bienestar/diario/lista.html', context)


@login_required
def nueva_entrada_diario(request):
    """Crear nueva entrada en el diario emocional."""
    if request.method == 'POST':
        contenido = request.POST.get('contenido', '').strip()
        
        if not contenido:
            messages.error(request, 'Por favor escribe algo en tu diario.')
            return redirect('bienestar:nueva_entrada_diario')
        
        try:
            # Analizar sentimiento con IA
            try:
                from core.utils.gemini_client import generate_content
                
                prompt_analisis = f"""Analiza el siguiente texto emocional y responde SOLO con una palabra que describa el sentimiento principal.

Texto: {contenido}

Responde solo con UNA de estas palabras: feliz, triste, ansioso, enojado, neutral, esperanzado, confundido, frustrado"""

                sentimiento_ia = (
                    generate_content(prompt_analisis, temperature=0.3, max_tokens=10) or 'neutral'
                ).strip().lower()
                
            except Exception:
                # Si falla la IA, usar detección simple
                sentimiento_ia = 'neutral'
                if any(palabra in contenido.lower() for palabra in ['feliz', 'alegre', 'contento', 'bien']):
                    sentimiento_ia = 'feliz'
                elif any(palabra in contenido.lower() for palabra in ['triste', 'deprimido', 'mal']):
                    sentimiento_ia = 'triste'
                elif any(palabra in contenido.lower() for palabra in ['ansioso', 'ansiedad', 'nervioso', 'preocupado']):
                    sentimiento_ia = 'ansioso'
            
            # Detectar nivel de riesgo
            nivel_riesgo = detectar_riesgo_emocional(contenido)
            
            # Crear entrada
            fecha_hoy = timezone.now().date()
            entrada, created = DiarioEmocional.objects.update_or_create(
                usuario=request.user,
                fecha=fecha_hoy,
                defaults={
                    'contenido_privado': contenido,
                    'sentimiento_ia': sentimiento_ia,
                    'nivel_riesgo': nivel_riesgo,
                }
            )
            
            # Si es nivel crítico, enviar alerta
            if entrada.es_critico() and not entrada.alerta_enviada:
                # Enviar alerta a dirección/RH
                try:
                    from django.core.mail import send_mail
                    from django.contrib.auth import get_user_model
                    _UserModel = get_user_model()

                    # Obtener usuarios administradores/RH de la misma empresa
                    empresa_req = getattr(request.user, 'empresa', None)
                    _qs_admins = _UserModel.objects.filter(is_staff=True, email__isnull=False).exclude(email='')
                    if empresa_req:
                        _qs_admins = _qs_admins.filter(empresa=empresa_req)
                    admins = _qs_admins
                    admin_emails = [admin.email for admin in admins]
                    
                    if admin_emails:
                        send_mail(
                            subject=f'🚨 ALERTA: Entrada crítica de diario emocional - {request.user.get_full_name() or request.user.username}',
                            message=f'''
Se ha detectado una entrada de diario emocional con nivel de riesgo CRÍTICO.

Usuario: {request.user.get_full_name() or request.user.username}
Fecha: {entrada.fecha.strftime("%d/%m/%Y")}
Nivel de Riesgo: {entrada.nivel_riesgo}
Sentimiento: {entrada.sentimiento_ia}

Se recomienda contactar al usuario para brindar apoyo inmediato.

---
Sistema PRISLAB - Módulo de Bienestar
                            '''.strip(),
                            from_email='noreply@prislab.com',
                            recipient_list=admin_emails,
                            fail_silently=True,
                        )
                        entrada.alerta_enviada = True
                        entrada.save()
                except Exception as e:
                    logger = logging.getLogger('bienestar')
                    logger.warning(f'No se pudo enviar alerta por email: {str(e)}')

            
            if created:
                messages.success(request, f'✅ Entrada guardada. Tu sentimiento principal: {sentimiento_ia}')
            else:
                messages.info(request, '📝 Entrada actualizada para hoy.')
            
            return redirect('bienestar:diario_emocional')
            
        except Exception as e:
            logger = logging.getLogger('bienestar')
            logger.error(f'Error al guardar entrada del diario: {str(e)}')
            messages.error(request, 'Error al guardar entrada. Por favor intenta de nuevo.')
            return redirect('bienestar:nueva_entrada_diario')
    
    # GET: Mostrar formulario
    empresa = getattr(request.user, 'empresa', None)
        
    emociones_sugeridas = [
        {'emoji': '😊', 'nombre': 'Feliz', 'color': '#4CAF50'},
        {'emoji': '😢', 'nombre': 'Triste', 'color': '#2196F3'},
        {'emoji': '😰', 'nombre': 'Ansioso', 'color': '#FF9800'},
        {'emoji': '😠', 'nombre': 'Enojado', 'color': '#F44336'},
        {'emoji': '😌', 'nombre': 'Tranquilo', 'color': '#00BCD4'},
        {'emoji': '🤔', 'nombre': 'Confundido', 'color': '#9C27B0'},
    ]
    
    return render(request, 'bienestar/diario/nueva_entrada.html', {
        'empresa': empresa,
        'emociones': emociones_sugeridas,
    })


@login_required
def estadisticas_diario(request):
    """Estadísticas y patrones emocionales."""
    usuario = request.user
    empresa = getattr(request.user, 'empresa', None)
    
    # Obtener entradas de los últimos 30 días
    hace_30_dias = timezone.now().date() - timedelta(days=30)
    entradas = DiarioEmocional.objects.filter(
        usuario=usuario,
        fecha__gte=hace_30_dias
    ).order_by('fecha')
    
    # Análisis de patrones
    patrones = []
    
    # Patrón 1: Días de la semana con mejor/peor ánimo
    entradas_por_dia_semana = {}
    for entrada in entradas:
        dia = entrada.fecha.strftime('%A')
        if dia not in entradas_por_dia_semana:
            entradas_por_dia_semana[dia] = []
        entradas_por_dia_semana[dia].append(entrada)
    
    # Patrón 2: Racha actual
    racha = calcular_racha(usuario)
    if racha > 0:
        patrones.append({
            'tipo': 'Positivo',
            'icono': '🔥',
            'descripcion': f'Llevas {racha} días consecutivos escribiendo en tu diario. ¡Excelente!'
        })
    
    # Patrón 3: Tendencia emocional (convertir a lista para soporte de negative indexing)
    entradas_lista = list(entradas)
    sentimientos_recientes = [e.sentimiento_ia for e in entradas_lista[-7:] if e.sentimiento_ia]
    if sentimientos_recientes:
        if sentimientos_recientes.count('feliz') > len(sentimientos_recientes) / 2:
            patrones.append({
                'tipo': 'Positivo',
                'icono': '😊',
                'descripcion': 'Tu ánimo ha mejorado en la última semana'
            })
        elif sentimientos_recientes.count('triste') > len(sentimientos_recientes) / 2:
            patrones.append({
                'tipo': 'Atención',
                'icono': '💙',
                'descripcion': 'Has tenido varios días difíciles. Considera hablar con alguien de confianza.'
            })
    
    context = {
        'empresa': empresa,
        'total_entradas': entradas.count(),
        'racha_dias': racha,
        'patrones': patrones,
        'entradas': entradas,
    }
    
    return render(request, 'bienestar/diario/estadisticas.html', context)


# ==================== RECURSOS ====================

@login_required
def recursos_bienestar(request):
    """Biblioteca de recursos de bienestar."""
    empresa = getattr(request.user, 'empresa', None)
        
    categoria = request.GET.get('categoria', 'TODOS')
    
    # Obtener recursos de la base de datos
    recursos = RecursoCrecimiento.objects.filter(activo=True)
    
    if categoria != 'TODOS':
        recursos = recursos.filter(categoria=categoria)
    
    recursos = recursos.order_by('-fecha_creacion')
    
    categorias = RecursoCrecimiento.CATEGORIA_CHOICES
    
    return render(request, 'bienestar/recursos/lista.html', {
        'empresa': empresa,
        'recursos': recursos,
        'categorias': categorias,
        'categoria_actual': categoria,
    })


@login_required
def detalle_recurso(request, recurso_id):
    """Detalle de un recurso de bienestar."""
    empresa = getattr(request.user, 'empresa', None)
        
    recurso = get_object_or_404(RecursoCrecimiento, id=recurso_id, activo=True)
    
    # Recursos relacionados
    relacionados = RecursoCrecimiento.objects.filter(
        categoria=recurso.categoria,
        activo=True
    ).exclude(id=recurso.id)[:3]
    
    return render(request, 'bienestar/recursos/detalle.html', {
        'empresa': empresa,
        'recurso': recurso,
        'relacionados': relacionados,
    })


# ==================== CONSULTORIO BIENESTAR ====================

@login_required
def agendar_consultorio_bienestar(request):
    """Agendar consulta de bienestar (nutricional, psicológica)."""
    empresa = getattr(request.user, 'empresa', None)
        
    if request.method == 'POST':
        servicio = request.POST.get('servicio')
        fecha = request.POST.get('fecha')
        hora = request.POST.get('hora')
        notas = request.POST.get('notas')
        
        # Citas de Bienestar se almacenan en el modelo SesionCoachingStaff (aislado de CitaMedica por NOM-035).
        # Integración pendiente cuando se complete la Fase de Bienestar/RRHH.
        messages.success(request, f'Cita de {servicio} agendada exitosamente para {fecha} a las {hora}.')
        return redirect('bienestar:dashboard_bienestar')
    
    servicios = [
        {'id': 'nutricion', 'nombre': 'Consulta Nutricional', 'duracion': '45 min', 'icono': 'apple-alt'},
        {'id': 'psicologia', 'nombre': 'Sesión de Psicología', 'duracion': '50 min', 'icono': 'brain'},
        {'id': 'coaching', 'nombre': 'Coaching de Vida', 'duracion': '60 min', 'icono': 'user-friends'},
    ]
    
    horarios_disponibles = [
        '09:00', '10:00', '11:00', '12:00', '14:00', '15:00', '16:00', '17:00'
    ]
    
    return render(request, 'bienestar/consultorio/agendar.html', {
        'empresa': empresa,
        'servicios': servicios,
        'horarios': horarios_disponibles,
    })
