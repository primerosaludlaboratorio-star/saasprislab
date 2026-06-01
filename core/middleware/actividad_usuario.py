"""
Middleware para rastrear actividad del usuario y detectar sesiones intensas (4+ horas).
El Guardián Jarvis: Sugiere descansos cuando se detecta actividad prolongada.
"""
from django.utils import timezone
from datetime import timedelta
from core.models import Usuario


class ActividadUsuarioMiddleware:
    """
    Middleware que rastrea la actividad del usuario y detecta sesiones intensas.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(request, 'user', None) and getattr(request.user, 'is_authenticated', False):
            usuario = request.user
            try:
                # Inicializar tiempo de actividad si no existe
                if not getattr(usuario, 'tiempo_actividad_inicio', None):
                    usuario.tiempo_actividad_inicio = timezone.now()
                    usuario.save(update_fields=['tiempo_actividad_inicio'])
                # Calcular tiempo de actividad
                tiempo_activo = timezone.now() - usuario.tiempo_actividad_inicio
                if tiempo_activo > timedelta(hours=4):
                    request.session['sugerir_descanso'] = True
                    request.session['tiempo_activo_horas'] = tiempo_activo.total_seconds() / 3600
                else:
                    request.session['sugerir_descanso'] = False
            except (AttributeError, TypeError, ValueError):
                pass  # No romper el request si el modelo cambió o save falla

        response = self.get_response(request)
        return response
