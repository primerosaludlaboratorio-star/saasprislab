from django.urls import path
from . import views

app_name = 'iot'

urlpatterns = [
    path('', views.dashboard_kioscos, name='dashboard_kioscos'),
    path('api/crear-kiosco/', views.api_crear_kiosco, name='api_crear_kiosco'),
    path('api/toggle/<int:kiosco_id>/', views.api_toggle_kiosco, name='api_toggle_kiosco'),
    path('api/heartbeat/<int:kiosco_id>/', views.api_kiosco_heartbeat, name='api_heartbeat'),
    path('api/confirmar/<int:verificacion_id>/', views.api_kiosco_confirmar, name='api_confirmar'),
    path('api/rechazar/<int:verificacion_id>/', views.api_kiosco_rechazar, name='api_rechazar'),
    path('api/enviar/', views.api_enviar_a_kiosco, name='api_enviar'),
]
