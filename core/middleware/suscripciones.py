from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.conf import settings

class SuscripcionMiddleware:
    """
    Verifica que la empresa (tenant) del usuario logueado tenga una suscripción activa.
    Bloquea el acceso si la suscripción está vencida o cancelada, excepto a URLs críticas 
    como logout o portal de pago.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Excepciones: Rutas estáticas, admin, login, etc.
        path = request.path_info
        if path.startswith('/admin/') or path.startswith('/static/') or path.startswith('/media/') or path.startswith('/login/') or path.startswith('/logout/') or path.startswith('/api/public/'):
            return self.get_response(request)

        user = getattr(request, 'user', None)
        if user and user.is_authenticated and not user.is_superuser:
            empresa = getattr(user, 'empresa', None)
            if empresa:
                # Comprobar si tiene suscripción
                if hasattr(empresa, 'suscripcion'):
                    suscripcion = empresa.suscripcion
                    if not suscripcion.esta_activa:
                        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                            return JsonResponse({
                                'error': 'Suscripción inactiva',
                                'detalle': f'La suscripción de {empresa.nombre} se encuentra {suscripcion.estado}.'
                            }, status=402)
                        return HttpResponseForbidden(f"<h1>Acceso Denegado (Error 402 - Payment Required)</h1><p>La suscripción para {empresa.nombre} se encuentra en estado <b>{suscripcion.estado}</b>. Contacte a soporte o renueve su plan.</p>")
                else:
                    # No tiene registro de suscripción, opcional: crear trial por defecto o bloquear.
                    pass

        response = self.get_response(request)
        return response
