from django.urls import path
from . import views

app_name = 'pris_ai_core'

urlpatterns = [
    path('api/voice/', views.voice_command_api, name='voice_command_api'),
    path('api/ocr/', views.ocr_api, name='ocr_api'),
]
