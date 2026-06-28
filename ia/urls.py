"""
URLs del Módulo de Inteligencia Artificial.
"""

from django.urls import path
from . import views

app_name = 'ia'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_ia, name='dashboard'),
    
    # OCR de Recetas
    path('ocr/procesar/', views.procesar_receta_ocr, name='procesar_receta'),
    path('ocr/resultados/<int:pk>/', views.resultados_ocr, name='resultados_ocr'),
    path('ocr/crear-orden/<int:pk>/', views.crear_orden_desde_ocr, name='crear_orden_desde_ocr'),
    
    # Transcripción de Audio
    path('voz/transcribir/', views.transcribir_audio, name='transcribir_audio'),
    path('voz/resultados/<int:pk>/', views.resultados_transcripcion, name='resultados_transcripcion'),
    
    # Asistente Médico
    path('asistente/', views.asistente_medico, name='asistente_medico'),
    
    # APIs para AJAX (usado por Pris y otros módulos)
    path('api/consultar/', views.api_consultar_asistente, name='api_consultar_asistente'),
    path('api/analizar-sintomas/', views.analizar_sintomas, name='api_analizar_sintomas'),
    path('api/verificar-interacciones/', views.verificar_interacciones, name='api_verificar_interacciones'),
]
