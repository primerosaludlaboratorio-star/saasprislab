from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView
from core import views
from core.views.general import (
    CustomLoginView,
    service_worker_view,
    health_view,
    readiness_view,
    liveness_view,
)
from core.views import autenticacion_2fa as views_2fa

urlpatterns = [
    # Favicon — data URI para evitar 404 del browser
    path('favicon.ico', RedirectView.as_view(url='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>❤️</text></svg>', permanent=True)),

    # Legacy logo path — redirige al data URI
    path('media/logos/LOGO_PRISLAB.png', RedirectView.as_view(url='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>❤️</text></svg>', permanent=False)),

    # Panel Administrativo de Django
    path('admin/', admin.site.urls),

    # PWA — Service Worker con scope completo del dominio (única instancia)
    path('sw.js', service_worker_view, name='service_worker'),
    path('health/', health_view, name='health'),
    path('ready/', readiness_view, name='ready'),
    path('live/', liveness_view, name='live'),

    # RUTA PRINCIPAL - Login personalizado
    path('', CustomLoginView.as_view(), name='login_root'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),

    # FASE 4: Autenticación de dos factores (2FA/TOTP)
    path('auth/2fa/verificar/', views_2fa.verificar_2fa, name='verificar_2fa'),
    path('auth/2fa/configurar/', views_2fa.setup_2fa, name='setup_2fa'),
    path('auth/2fa/desactivar/', views_2fa.desactivar_2fa, name='desactivar_2fa'),

    # Home y Dashboard principal
    path('home/', views.home_view, name='home'),
    path('dashboard/', views.dashboard_director, name='dashboard'),
]
