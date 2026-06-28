"""
Utilidades para generar saludos personalizados según el usuario.
"""
from django.contrib.auth import get_user_model
import logging

Usuario = get_user_model()


def obtener_saludo_personalizado(usuario):
    """
    Genera un saludo personalizado según el rol, título profesional y nombre del usuario.
    Prioriza el título profesional configurado sobre el mapeo automático.
    """
    if not usuario:
        return {
            'saludo': '¡Hola!',
            'mensaje': 'Bienvenido a PRISLAB',
            'mensaje_bienestar': '',
            'nombre_completo': ''
        }
    
    try:
        nombre = getattr(usuario, 'first_name', None) or getattr(usuario, 'username', 'Usuario')
        apellido = getattr(usuario, 'last_name', '') or ''
        nombre_completo = f"{nombre} {apellido}".strip()
        
        # Usar título profesional si está configurado, sino usar mapeo automático
        titulo_profesional = getattr(usuario, 'titulo_profesional', None)
        if titulo_profesional:
            titulo = titulo_profesional
        else:
            # Mapeo de roles a títulos/grados (fallback)
            rol = getattr(usuario, 'rol', '')
            titulos = {
                'QUIMICO': 'Q.C.',
                'MEDICO': 'Dra.' if hasattr(usuario, 'gender') and getattr(usuario, 'gender', None) == 'F' else 'Dr.',
                'ADMIN': 'Director',
                'GERENTE': 'Gerente',
            }
            titulo = titulos.get(rol, '')
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en obtener_saludo_personalizado (saludos.py)")
        # Si hay cualquier error, usar valores por defecto
        nombre = getattr(usuario, 'username', 'Usuario')
        nombre_completo = nombre
        titulo = ''
    
    # Saludo base con título
    if titulo:
        saludo = f"¡Hola {titulo} {nombre}!"
    else:
        saludo = f"¡Hola {nombre}!"
    
    # Mensaje según rol y enfoque profesional
    try:
        enfoque_profesional = getattr(usuario, 'enfoque_profesional', None)
        rol = getattr(usuario, 'rol', '')
        
        if enfoque_profesional:
            mensaje = f"Te deseamos un día de éxito. PRIS está aquí para facilitar tu labor y que alcances tu máximo potencial profesional. Tu enfoque: {enfoque_profesional}."
        elif rol in ['QUIMICO', 'RECEPCION', 'MEDICO']:
            mensaje = "Te deseamos un día de éxito. PRIS está aquí para facilitar tu labor y que alcances tu máximo potencial profesional."
        elif rol == 'CAJERO' or 'Deya' in nombre_completo or 'deya' in nombre.lower():
            saludo = "¡Hola Deya!" if 'Deya' in nombre_completo or 'deya' in nombre.lower() else saludo
            mensaje = "Gracias por ser un pilar de este equipo. Te deseamos un excelente día enfocado en tu crecimiento profesional. No olvides que si necesitas un espacio de paz o alguien con quien hablar, cuentas con tu Módulo de Bienestar. Estamos aquí para apoyarte en cada paso."
            mensaje_bienestar = "No olvides que si necesitas un espacio de paz o alguien con quien hablar, cuentas con tu Módulo de Bienestar. Estamos aquí para apoyarte en cada paso."
            return {
                'saludo': saludo,
                'mensaje': mensaje,
                'mensaje_bienestar': mensaje_bienestar,
                'nombre_completo': nombre_completo
            }
        else:
            mensaje = "Te deseamos un día de éxito. PRIS está aquí para facilitar tu trabajo."
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en obtener_saludo_personalizado (saludos.py)")
        mensaje = "Te deseamos un día de éxito. PRIS está aquí para facilitar tu trabajo."
    
    mensaje_bienestar = "Recuerda: si en algún momento el día se vuelve pesado y requieres un momento de paz, tu Módulo de Bienestar está siempre disponible para ti."
    
    try:
        return {
            'saludo': saludo,
            'mensaje': mensaje,
            'mensaje_bienestar': mensaje_bienestar,
            'nombre_completo': nombre_completo
        }
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en obtener_saludo_personalizado (saludos.py)")
        # Fallback en caso de cualquier error
        return {
            'saludo': f'¡Hola {nombre}!',
            'mensaje': 'Te deseamos un día de éxito. PRIS está aquí para facilitar tu trabajo.',
            'mensaje_bienestar': mensaje_bienestar,
            'nombre_completo': nombre_completo
        }