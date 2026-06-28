"""
Marketing Tracking Integration — Utilidades para P2 Cascada
Genera URLs de tracking firmadas para emails y WhatsApp.
"""
from django.urls import reverse
from django.conf import settings
from marketing.tracking_signing import sign_track_token


def generar_pixel_tracking_url(paciente=None, prospecto=None, campana=None, evento="email_resultado_abierto"):
    """
    Genera URL de tracking pixel 1x1 para incluir en emails.
    
    Args:
        paciente: Instancia de Paciente (opcional)
        prospecto: Instancia de ProspectoCRM (opcional)
        campana: Instancia de CampanaMarketing (opcional)
        evento: Clave de evento canónica (default: email_resultado_abierto)
    
    Returns:
        str: URL absoluta del pixel de tracking
    """
    payload = {}
    
    if paciente and hasattr(paciente, 'pk'):
        payload['p'] = paciente.pk
        if hasattr(paciente, 'empresa_id'):
            payload['e'] = paciente.empresa_id
    
    if prospecto and hasattr(prospecto, 'pk'):
        payload['pr'] = prospecto.pk
        if hasattr(prospecto, 'empresa_id'):
            payload['e'] = prospecto.empresa_id
    
    token = sign_track_token(payload) if payload else ""
    
    base_url = reverse("marketing:marketing_track_pixel")
    
    params = f"?ev={evento}"
    if token:
        params += f"&tok={token}"
    if campana and hasattr(campana, 'pk'):
        params += f"&camp={campana.pk}"
    
    # Construir URL absoluta
    dominio = getattr(settings, 'PRISLAB_DOMINIO_PUBLICO', 'https://prislab.app')
    return f"{dominio}{base_url}{params}"


def generar_link_whatsapp_con_tracking(telefono, mensaje, paciente=None, campana=None, evento="wa_resultado_clic"):
    """
    Genera enlace wa.me con tracking integrado.
    El tracking se registra cuando el usuario hace clic en el enlace.
    
    Args:
        telefono: Número de teléfono destino
        mensaje: Mensaje pre-redactado
        paciente: Instancia de Paciente (opcional)
        campana: Instancia de CampanaMarketing (opcional)
        evento: Clave de evento canónica (default: wa_resultado_clic)
    
    Returns:
        str: URL de WhatsApp con parámetros de tracking
    """
    from urllib.parse import quote
    
    # Generar URL de tracking intermediaria (que luego redirige a wa.me)
    # o incrustar el pixel en una landing page previa
    tracking_url = generar_pixel_tracking_url(
        paciente=paciente,
        campana=campana,
        evento=evento
    )
    
    # Mensaje codificado
    mensaje_codificado = quote(mensaje, safe='')
    
    # Limpiar teléfono
    telefono_limpio = ''.join(filter(str.isdigit, str(telefono)))
    if len(telefono_limpio) == 10:
        telefono_limpio = '52' + telefono_limpio
    
    # URL de WhatsApp
    wa_url = f"https://wa.me/{telefono_limpio}?text={mensaje_codificado}"
    
    return {
        'wa_url': wa_url,
        'tracking_pixel': tracking_url,
        'mensaje_completo': f"{mensaje}\n\n[Track: {tracking_url}]"
    }


def generar_email_html_con_tracking(paciente, subject, body_html, campana=None):
    """
    Envuelve HTML de email con pixel de tracking invisible.
    
    Args:
        paciente: Instancia de Paciente
        subject: Asunto del email
        body_html: Cuerpo HTML del email
        campana: Instancia de CampanaMarketing (opcional)
    
    Returns:
        str: HTML completo con pixel de tracking 1x1 al final
    """
    pixel_url = generar_pixel_tracking_url(
        paciente=paciente,
        campana=campana,
        evento="email_resultado_abierto"
    )
    
    # Pixel invisible 1x1 al final del body
    pixel_img = f'<img src="{pixel_url}" width="1" height="1" alt="" style="display:block;visibility:hidden;" />'
    
    # Cerrar tags si es necesario y agregar pixel
    if '</body>' in body_html:
        return body_html.replace('</body>', f'{pixel_img}</body>')
    else:
        return f"{body_html}{pixel_img}"


def enviar_email_resultados_con_tracking(paciente, resultados_data, request=None):
    """
    Envía email de resultados con tracking pixel integrado.
    
    Args:
        paciente: Instancia de Paciente
        resultados_data: Dict con datos de resultados
        request: HttpRequest (opcional, para metadatos)
    """
    from django.core.mail import send_mail
    from django.template.loader import render_to_string

    from core.utils.lfpdppp_resultados import paciente_autorizado_canal_digital_resultados

    if not paciente_autorizado_canal_digital_resultados(paciente):
        return False
    
    if not paciente.email:
        return False
    
    # Renderizar plantilla con contexto
    contexto = {
        'paciente': paciente,
        'resultados': resultados_data,
        'empresa': paciente.empresa,
    }
    
    html_body = render_to_string('emails/resultados_listos.html', contexto)
    
    # Inyectar pixel de tracking
    html_con_tracking = generar_email_html_con_tracking(
        paciente=paciente,
        subject="Sus resultados de laboratorio están listos",
        body_html=html_body
    )
    
    # Enviar email
    try:
        send_mail(
            subject="Sus resultados de laboratorio están listos - " + paciente.empresa.nombre,
            message="",  # Versión texto plano
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@prislab.app'),
            recipient_list=[paciente.email],
            html_message=html_con_tracking,
            fail_silently=True
        )
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error enviando email con tracking: {e}")
        return False
