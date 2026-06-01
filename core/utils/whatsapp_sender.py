"""
Conector de WhatsApp — Envío real + Generador de enlaces de fallback
═══════════════════════════════════════════════════════════════════

Flujo de envío:
  1. Si TWILIO_ACCOUNT_SID está configurado → envío automático vía Twilio WA Business API.
  2. Si WHATSAPP_API_TOKEN (360dialog / Meta) está configurado → envío via Meta Cloud API.
  3. Si ninguno está → genera enlace wa.me de fallback para click manual del staff.

Variables de entorno requeridas para envío real:
  - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM
    (Ej: TWILIO_WHATSAPP_FROM = 'whatsapp:+14155238886')
  O bien:
  - WHATSAPP_API_TOKEN, WHATSAPP_PHONE_NUMBER_ID
    (Meta / 360dialog Cloud API)

Uso:
    from core.utils.whatsapp_sender import enviar_whatsapp, generar_enlace_whatsapp
    resultado = enviar_whatsapp(telefono='5551234567', mensaje='Tus resultados listos.')
    # resultado = {'enviado': True, 'canal': 'twilio', 'sid': '...'}
    # o bien: {'enviado': False, 'canal': 'link', 'link': 'https://wa.me/...'}
"""
import logging
import os
import urllib.parse

logger = logging.getLogger('core.whatsapp')

_TWILIO_SID   = os.environ.get('TWILIO_ACCOUNT_SID', '')
_TWILIO_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
_TWILIO_FROM  = os.environ.get('TWILIO_WHATSAPP_FROM', '')  # 'whatsapp:+14155238886'

_META_TOKEN   = os.environ.get('WHATSAPP_API_TOKEN', '')
_META_PHONE_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')


def enviar_whatsapp(telefono: str, mensaje: str) -> dict:
    """
    Intenta enviar un WhatsApp real. Si no hay credenciales, devuelve el enlace wa.me.

    Returns:
        dict con claves: enviado (bool), canal ('twilio'|'meta'|'link'), y detalles.
    """
    telefono_e164 = _normalizar_telefono(telefono)
    if not telefono_e164:
        return {'enviado': False, 'canal': 'error', 'error': 'Teléfono inválido'}

    # Opción 1: Twilio
    if _TWILIO_SID and _TWILIO_TOKEN and _TWILIO_FROM:
        return _enviar_twilio(telefono_e164, mensaje)

    # Opción 2: Meta Cloud API / 360dialog
    if _META_TOKEN and _META_PHONE_ID:
        return _enviar_meta(telefono_e164, mensaje)

    # Fallback: link manual
    link = generar_enlace_whatsapp(telefono, mensaje)
    logger.info(
        'enviar_whatsapp: sin credenciales API, generando link fallback para %s', telefono_e164
    )
    return {'enviado': False, 'canal': 'link', 'link': link}


def _normalizar_telefono(telefono: str) -> str:
    """Normaliza a formato E.164 (+521XXXXXXXXXX). Retorna '' si inválido."""
    digits = ''.join(filter(str.isdigit, str(telefono or '')))
    if len(digits) == 10:
        digits = '52' + digits
    if len(digits) >= 11:
        return '+' + digits
    return ''


def _enviar_twilio(telefono_e164: str, mensaje: str) -> dict:
    """Envía via Twilio WhatsApp Sandbox / Business API."""
    try:
        from twilio.rest import Client  # type: ignore
        client = Client(_TWILIO_SID, _TWILIO_TOKEN)
        msg = client.messages.create(
            from_=_TWILIO_FROM,
            to=f'whatsapp:{telefono_e164}',
            body=mensaje,
        )
        logger.info('whatsapp_twilio: enviado a %s SID=%s', telefono_e164, msg.sid)
        return {'enviado': True, 'canal': 'twilio', 'sid': msg.sid}
    except ImportError:
        logger.warning('whatsapp_twilio: twilio no instalado. pip install twilio')
        return {'enviado': False, 'canal': 'error', 'error': 'Librería twilio no instalada'}
    except Exception as e:
        logger.error('whatsapp_twilio error: %s', e)
        return {'enviado': False, 'canal': 'error', 'error': str(e)}


def _enviar_meta(telefono_e164: str, mensaje: str) -> dict:
    """Envía via Meta Cloud API (WhatsApp Business API v17+)."""
    import json
    try:
        import urllib.request
        digits_only = telefono_e164.lstrip('+')
        payload = {
            'messaging_product': 'whatsapp',
            'to': digits_only,
            'type': 'text',
            'text': {'body': mensaje},
        }
        data = json.dumps(payload).encode('utf-8')
        url = f'https://graph.facebook.com/v17.0/{_META_PHONE_ID}/messages'
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'Authorization': f'Bearer {_META_TOKEN}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        msg_id = result.get('messages', [{}])[0].get('id', '')
        logger.info('whatsapp_meta: enviado a %s msg_id=%s', digits_only, msg_id)
        return {'enviado': True, 'canal': 'meta', 'message_id': msg_id}
    except Exception as e:
        logger.error('whatsapp_meta error: %s', e)
        return {'enviado': False, 'canal': 'error', 'error': str(e)}


def generar_enlace_whatsapp(telefono, mensaje):
    """
    Genera enlace universal de WhatsApp Web.
    
    Args:
        telefono (str): Número de teléfono con código de país (ej: '525551234567')
        mensaje (str): Mensaje pre-redactado
    
    Returns:
        str: URL completa para WhatsApp Web
    
    Ejemplo:
        enlace = generar_enlace_whatsapp('525551234567', 'Hola, aquí está tu cotización')
        # Retorna: 'https://wa.me/525551234567?text=Hola%2C%20aqu%C3%AD%20est%C3%A1%20tu%20cotizaci%C3%B3n'
    """
    # Limpiar teléfono (remover espacios, guiones, paréntesis)
    telefono_limpio = ''.join(filter(str.isdigit, str(telefono)))
    
    # Si no tiene código de país, asumir México (+52)
    if len(telefono_limpio) == 10:
        telefono_limpio = '52' + telefono_limpio
    
    # Codificar mensaje para URL
    mensaje_codificado = urllib.parse.quote(mensaje, safe='')
    
    # Generar enlace
    enlace = f'https://wa.me/{telefono_limpio}?text={mensaje_codificado}'
    
    return enlace


def generar_mensaje_cotizacion(paciente_nombre, estudios, total, link_descarga=None):
    """
    Genera mensaje pre-formateado para cotización por WhatsApp.
    
    Args:
        paciente_nombre (str): Nombre del paciente
        estudios (list): Lista de estudios con nombre y precio
        total (Decimal): Total de la cotización
        link_descarga (str, optional): Link para descargar PDF
    
    Returns:
        str: Mensaje formateado
    """
    mensaje = f"🏥 *PRISLAB - Cotización de Laboratorio*\n\n"
    mensaje += f"Hola *{paciente_nombre}*,\n\n"
    mensaje += f"Aquí está tu cotización de estudios:\n\n"
    
    for estudio in estudios:
        nombre = estudio.get('nombre', 'Estudio')
        precio = estudio.get('precio', 0)
        mensaje += f"• {nombre}: ${precio:,.2f}\n"
    
    mensaje += f"\n*Total: ${total:,.2f}*\n\n"
    
    if link_descarga:
        mensaje += f"📄 Descarga tu cotización completa aquí:\n{link_descarga}\n\n"
    
    mensaje += "¿Te gustaría agendar tu cita?\n\n"
    mensaje += "Saludos,\n*Equipo Prislab* 🔬"
    
    return mensaje


def generar_mensaje_resultados(paciente_nombre, orden_folio, link_descarga):
    """
    Genera mensaje pre-formateado para envío de resultados por WhatsApp.
    Incluye posdata de fidelización con descuento en consulta.
    
    Args:
        paciente_nombre (str): Nombre del paciente
        orden_folio (str): Folio de la orden
        link_descarga (str): Link seguro para descargar resultados PDF
    
    Returns:
        str: Mensaje formateado con posdata de marketing
    """
    mensaje = f"🔬 *PRISLAB - Resultados de Laboratorio*\n\n"
    mensaje += f"Hola *{paciente_nombre}*,\n\n"
    mensaje += f"Tus resultados de laboratorio están listos.\n\n"
    mensaje += f"📋 *Orden:* {orden_folio}\n\n"
    mensaje += f"📄 *Descarga Segura:*\n{link_descarga}\n\n"
    mensaje += "⚠️ *Importante:* Este enlace es personalizado y seguro. "
    mensaje += "No lo compartas con terceros.\n\n"
    mensaje += "Si tienes alguna duda, no dudes en contactarnos.\n\n"
    mensaje += "Saludos,\n*Equipo Prislab* 🏥\n\n"
    mensaje += "─────────────────────\n"
    mensaje += "💊 *Tu salud es lo más importante.* Por ser paciente de "
    mensaje += "Primero Salud, tu próxima consulta con la *Dra. Brizia* "
    mensaje += "tiene un *10% de descuento*. Válido por 30 días. "
    mensaje += "¡Agenda tu cita hoy! 📅"
    
    return mensaje
