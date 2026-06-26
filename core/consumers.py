"""
PRIS VOICE COMMANDER - WebSocket Consumers
Maneja conexiones en tiempo real para comandos de voz y walkie-talkie
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async

logger = logging.getLogger('websockets')


class VoiceCommandConsumer(AsyncWebsocketConsumer):
    """
    Consumer para comandos de voz con procesamiento en tiempo real.
    Recibe transcripciones y contexto, procesa con IA, retorna respuestas.
    """
    
    async def connect(self):
        """Acepta la conexión WebSocket."""
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            logger.warning("Usuario anónimo intentó conectar al canal de voz")
            await self.close()
            return
        
        # Unirse al canal personal del usuario
        self.group_name = f"voice_commands_{self.user.id}"
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Usuario {self.user.username} conectado al canal de comandos de voz")
        
        # Enviar mensaje de bienvenida
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Bienvenido, {self.user.get_full_name()}. PRIS Voice Commander activo.',
            'user_role': 'DIRECTOR' if self.user.is_superuser else 'STAFF'
        }))
    
    async def disconnect(self, close_code):
        """Desconecta del canal."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            logger.info(f"Usuario {self.user.username} desconectado del canal de voz")
    
    async def receive(self, text_data):
        """
        Recibe comandos de voz desde el cliente.
        
        Formato esperado:
        {
            "type": "voice_command",
            "transcription": "buscar paciente juan",
            "url": "/farmacia/ventas/",
            "context": "Receta #554 en pantalla"
        }
        """
        try:
            data = json.loads(text_data)
            command_type = data.get('type')
            
            if command_type == 'voice_command':
                await self.handle_voice_command(data)
            elif command_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Tipo de comando no reconocido: {command_type}'
                }))
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'JSON inválido'
            }))
        except (KeyError, TypeError, AttributeError) as e:
            logger.warning(f"Datos malformados en VoiceCommandConsumer: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Datos inválidos: {type(e).__name__}'
            }))
        except Exception as e:
            # Safety net del consumer async — evita que un error no anticipado
            # rompa la conexión WebSocket completa.
            logger.error(f"Error en receive de VoiceCommandConsumer: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error del servidor: {type(e).__name__}'
            }))
    
    async def handle_voice_command(self, data):
        """Procesa un comando de voz con IA."""
        transcription = data.get('transcription', '')
        url = data.get('url', '/')
        context = data.get('context', '')
        
        if not transcription:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Transcripción vacía'
            }))
            return
        
        # Enviar "pensando..." al cliente
        await self.send(text_data=json.dumps({
            'type': 'processing',
            'message': 'Pensando...'
        }))
        
        # Procesar con IA (sync_to_async para operaciones de DB)
        resultado = await sync_to_async(self.process_voice_command)(
            transcription, url, context
        )
        
        # Enviar respuesta al cliente
        await self.send(text_data=json.dumps({
            'type': 'command_result',
            'intention': resultado['intencion'],
            'parameters': resultado['parametros'],
            'response': resultado['respuesta'],
            'action': resultado['accion'],
            'blocked': resultado['bloqueado'],
            'requires_auth': resultado['requiere_auth'],
            'processing_time_ms': resultado['tiempo_procesamiento_ms']
        }))
    
    def process_voice_command(self, transcription, url, context):
        """Procesamiento síncro del comando (para llamar funciones de DB)."""
        from core.services.voice_service import procesar_comando_voz, registrar_comando_voz
        
        # Procesar con IA
        resultado = procesar_comando_voz(
            transcripcion=transcription,
            usuario=self.user,
            url_actual=url,
            datos_pantalla=context
        )
        
        # Registrar en log de auditoría
        registrar_comando_voz(
            usuario=self.user,
            transcripcion=transcription,
            resultado=resultado,
            url_actual=url,
            datos_pantalla=context
        )
        
        return resultado


class WalkieTalkieConsumer(AsyncWebsocketConsumer):
    """
    Consumer para comunicación tipo walkie-talkie entre usuarios.
    Permite transmitir audio efímero en tiempo real.
    """
    
    async def connect(self):
        """Acepta la conexión y une al room."""
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            logger.warning("Usuario anónimo intentó conectar al walkie-talkie")
            await self.close()
            return
        
        # Room name desde la URL (ej: "farmacia", "consultorio", "general")
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'walkie_{self.room_name}'
        
        # Unirse al room
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Usuario {self.user.username} conectado al walkie-talkie room '{self.room_name}'")
        
        # Notificar a otros usuarios que alguien se unió
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'username': self.user.username,
                'full_name': self.user.get_full_name(),
                'user_id': self.user.id
            }
        )
    
    async def disconnect(self, close_code):
        """Desconecta del room."""
        if hasattr(self, 'room_group_name'):
            # Notificar a otros que el usuario se fue
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'username': self.user.username,
                    'full_name': self.user.get_full_name()
                }
            )
            
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"Usuario {self.user.username} desconectado del walkie-talkie")
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Recibe mensajes de audio (bytes) o texto.
        
        Formato de texto:
        {
            "type": "audio_message",
            "audio_data": "base64_encoded_audio",
            "duration": 3.5,
            "recipient_id": 123  // opcional, para mensaje directo
        }
        """
        if bytes_data:
            # Audio raw en bytes (para optimización futura)
            await self.broadcast_audio(bytes_data, is_bytes=True)
        
        elif text_data:
            try:
                data = json.loads(text_data)
                message_type = data.get('type')
                
                if message_type == 'audio_message':
                    await self.broadcast_audio(data)
                elif message_type == 'ping':
                    await self.send(text_data=json.dumps({'type': 'pong'}))
                else:
                    logger.warning(f"Tipo de mensaje walkie-talkie no reconocido: {message_type}")
            
            except json.JSONDecodeError:
                logger.error("JSON inválido recibido en walkie-talkie")
    
    async def broadcast_audio(self, data, is_bytes=False):
        """
        Transmite el audio a todos en el room (o a un destinatario específico).
        """
        if is_bytes:
            # Para transmisión de bytes raw (implementación futura)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'audio_broadcast',
                    'audio_data': data,
                    'sender_id': self.user.id,
                    'sender_name': self.user.get_full_name(),
                    'is_bytes': True
                }
            )
        else:
            # Audio en base64 (implementación actual)
            recipient_id = data.get('recipient_id')
            
            if recipient_id:
                # Mensaje directo a un usuario específico
                # Canal privado pendiente: usar channel_layer.send(channel_name, msg) con el channel_name del destinatario especifico.
                pass
            else:
                # Broadcast a todos en el room
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'audio_broadcast',
                        'audio_data': data.get('audio_data'),
                        'duration': data.get('duration', 0),
                        'sender_id': self.user.id,
                        'sender_name': self.user.get_full_name()
                    }
                )
    
    async def audio_broadcast(self, event):
        """Handler para recibir audio del channel layer y enviarlo al cliente."""
        # No enviar el audio de vuelta al emisor
        if event['sender_id'] == self.user.id:
            return
        
        # Enviar al cliente
        await self.send(text_data=json.dumps({
            'type': 'audio_message',
            'audio_data': event.get('audio_data'),
            'duration': event.get('duration', 0),
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp': None  # El cliente puede agregar timestamp
        }))
    
    async def user_joined(self, event):
        """Handler para notificar cuando un usuario se une."""
        # No notificar al usuario que se unió
        if event['user_id'] == self.user.id:
            return
        
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'username': event['username'],
            'full_name': event['full_name']
        }))
    
    async def user_left(self, event):
        """Handler para notificar cuando un usuario se va."""
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'username': event['username'],
            'full_name': event['full_name']
        }))
