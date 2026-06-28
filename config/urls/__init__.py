from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

# ── Handlers de error (deben estar en el módulo ROOT_URLCONF) ────────────────
from core.views.general import error_404, error_500, error_403

handler404 = error_404
handler500 = error_500
handler403 = error_403

# ── Submódulos en orden de precedencia ──────────────────────────────────────
from .core_views import urlpatterns as _core
from .laboratorio import urlpatterns as _lab
from .farmacia import urlpatterns as _farm
from .director import urlpatterns as _dir
from .finanzas import urlpatterns as _fin
from .pris_ia import urlpatterns as _pris
from .modulos import urlpatterns as _mod
from .api import urlpatterns as _api

# Catch-all core.urls (SIEMPRE al final)
_core_catchall = [path('', include('core.urls', namespace='core'))]

urlpatterns = (
    _core
    + _lab
    + _farm
    + _dir
    + _fin
    + _pris
    + _mod
    + _api
    + _core_catchall
)

# Archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
