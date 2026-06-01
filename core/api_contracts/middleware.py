"""
Asigna request_id de correlación (Cadenero).
Prioridad: cabecera X-Request-ID si es UUID válido; si no, genera uno nuevo.
"""
import uuid

from django.utils.deprecation import MiddlewareMixin


class ApiRequestIdMiddleware(MiddlewareMixin):
    """Expone request.api_request_id y refleja X-Request-ID en la respuesta."""

    def process_request(self, request):
        raw = (request.META.get("HTTP_X_REQUEST_ID") or "").strip()
        rid = raw
        if raw:
            try:
                uuid.UUID(raw)
            except (ValueError, TypeError):
                rid = str(uuid.uuid4())
        else:
            rid = str(uuid.uuid4())
        request.api_request_id = rid

    def process_response(self, request, response):
        rid = getattr(request, "api_request_id", None)
        if rid:
            response["X-Request-ID"] = rid
        return response
