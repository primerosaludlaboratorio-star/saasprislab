from django.urls import path
from . import views

app_name = 'bienestar'

urlpatterns = [
    path('', views.dashboard_bienestar, name='dashboard_bienestar'),
    
    # Chat con PRIS
    path('chat/', views.chat_bienestar, name='chat_bienestar'),
    path('api/chat/', views.api_chat_bienestar, name='api_chat_bienestar'),
    
    # Diario Emocional
    path('diario/', views.diario_emocional, name='diario_emocional'),
    path('diario/lista/', views.diario_emocional, name='diario_lista'),
    path('diario/nueva/', views.nueva_entrada_diario, name='nueva_entrada_diario'),
    path('diario/nueva/entrada/', views.nueva_entrada_diario, name='nueva_entrada'),
    path('diario/estadisticas/', views.estadisticas_diario, name='estadisticas_diario'),
    
    # Recursos
    path('recursos/', views.recursos_bienestar, name='recursos_bienestar'),
    path('recursos/lista/', views.recursos_bienestar, name='recursos_lista'),
    path('recursos/<int:recurso_id>/', views.detalle_recurso, name='detalle_recurso'),
    
    # Consultorio
    path('consultorio/agendar/', views.agendar_consultorio_bienestar, name='agendar_consultorio'),
]
