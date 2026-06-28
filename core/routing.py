"""
PRIS VOICE COMMANDER - WebSocket Routing
Define las rutas de WebSocket para comunicación en tiempo real
"""

from django.urls import re_path
from core import consumers

websocket_urlpatterns = [
    # Walkie-Talkie: Canal de comunicación directa entre usuarios
    re_path(r'ws/voice/walkie/(?P<room_name>\w+)/$', consumers.WalkieTalkieConsumer.as_asgi()),
    
    # Voice Commands: Canal para comandos de voz con respuestas en tiempo real
    re_path(r'ws/voice/commands/$', consumers.VoiceCommandConsumer.as_asgi()),
]
