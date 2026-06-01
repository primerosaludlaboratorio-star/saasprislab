"""
Middleware para asegurar que todas las respuestas API devuelvan JSON.
Evita que errores 404/500 devuelvan HTML cuando se espera JSON.
"""
import json
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class JSONResponseMiddleware(MiddlewareMixin):
    """
    Middleware que intercepta respuestas de error y las convierte a JSON
    si la petición es AJAX (X-Requested-With: XMLHttpRequest).
    """
    
    def process_response(self, request, response):
        # Solo procesar si es una petición AJAX
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return response

        # Fragmentos HTML (PDV, HTMX): nunca convertir a JSON aunque venga como XHR
        accept = (request.headers.get('Accept') or '')
        if 'text/html' in accept:
            return response
        path = getattr(request, 'path', '') or ''
        if (
            'buscar-fragmento' in path
            or path.endswith('/fragmento/')
            or '/farmacia/pdv/buscar-fragmento' in path
        ):
            return response

        # Solo procesar si la respuesta no es ya JSON
        content_type = response.get('Content-Type', '')
        if 'application/json' in content_type:
            return response
        
        # Redirect a login para AJAX = sesión expirada -> devolver JSON 401
        if response.status_code in (301, 302) and '/login' in response.get('Location', ''):
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Sesión expirada. Recargue la página.',
                'codigo': 401,
                'redirect': response.get('Location', '/login/')
            }, status=401)

        # Si es un error (4xx, 5xx) y la respuesta es HTML, convertir a JSON
        if response.status_code >= 400:
            try:
                # Intentar leer el contenido HTML
                content = response.content.decode('utf-8')
                
                # Si contiene HTML (DOCTYPE), convertir a JSON
                if '<!DOCTYPE' in content or '<html' in content:
                    error_message = 'Error del servidor'
                    
                    # Extraer mensaje de error si es posible
                    if response.status_code == 404:
                        error_message = 'Recurso no encontrado'
                    elif response.status_code == 403:
                        error_message = 'Acceso denegado'
                    elif response.status_code == 500:
                        error_message = 'Error interno del servidor'
                    
                    return JsonResponse({
                        'status': 'error',
                        'mensaje': error_message,
                        'codigo': response.status_code
                    }, status=response.status_code)
            except Exception:
                # Si falla la conversión, devolver JSON genérico
                return JsonResponse({
                    'status': 'error',
                    'mensaje': f'Error del servidor (código {response.status_code})',
                    'codigo': response.status_code
                }, status=response.status_code)
        
        return response
