#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Driver para Norma Icon (Icon-3 / Icon-5)

Recibe resultados por TCP/IP en HL7 v2.x.

Soporta:
- HL7 v2.x “plano” (segmentos separados por \r)
- HL7 v2.x con MLLP (0x0b ... 0x1c 0x0d)

El equipo espera un ACK (MSH/MSA) antes de cerrar la conexión.
Este driver genera un ACK mínimo (AA) con el Message Control ID del MSH.
"""

import socket
import threading
import logging
from typing import Optional, Callable, Dict, Any
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class NormaIconDriver:
    """
    Driver para equipos Norma Icon que comunican por TCP/IP con HL7 v2.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el driver con la configuración del equipo.
        
        Args:
            config: Configuración del equipo desde config.yaml
        """
        self.config = config
        self.nombre = config.get('nombre', 'Norma Icon')
        self.ip = config.get('ip', '127.0.0.1')
        self.puerto = config.get('puerto', 5000)
        self.tipo = config.get('tipo', 'tcp')

        # HL7 v2 config
        self.use_mllp = bool(config.get('mllp', True))
        self.encoding = config.get('encoding', 'utf-8')
        self.ack_timeout_sec = float(config.get('ack_timeout_sec', 9.0))
        
        self.socket = None
        self.cliente_socket = None
        self.running = False
        self.thread = None
        self.on_result: Optional[Callable] = None
        self._buffer_loop = b""
        
        logger.info(f"Driver Norma Icon inicializado: {self.nombre} - {self.ip}:{self.puerto}")
    
    def conectar(self):
        """Establece la conexión TCP/IP como servidor (listener)."""
        try:
            # Crear socket TCP/IP
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.ip, self.puerto))
            self.socket.listen(1)
            self.socket.settimeout(1.0)  # Timeout para poder verificar running
            
            logger.info(f"✅ Escuchando en {self.ip}:{self.puerto} para {self.nombre}")
            
            # Iniciar hilo de escucha
            self.running = True
            self.thread = threading.Thread(target=self._escuchar_conexiones, daemon=True)
            self.thread.start()
            
        except Exception as e:
            logger.error(f"Error al conectar {self.nombre}: {e}")
            raise
    
    def desconectar(self):
        """Cierra la conexión TCP/IP."""
        self.running = False
        
        if self.cliente_socket:
            try:
                self.cliente_socket.close()
            except:
                pass
            self.cliente_socket = None
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        logger.info(f"Desconectado: {self.nombre}")
    
    def _escuchar_conexiones(self):
        """Escucha conexiones entrantes del equipo."""
        while self.running:
            try:
                # Aceptar conexión
                self.cliente_socket, address = self.socket.accept()
                logger.info(f"📡 Conexión establecida desde {address} para {self.nombre}")
                
                # Procesar mensajes del cliente
                self._procesar_mensajes()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error en conexión {self.nombre}: {e}")
                break
    
    def _procesar_mensajes(self):
        """Procesa mensajes recibidos del equipo."""
        buffer = b""
        
        while self.running:
            try:
                # Recibir datos
                data = self.cliente_socket.recv(4096)
                
                if not data:
                    logger.warning(f"Conexión cerrada por {self.nombre}")
                    break
                
                buffer += data
                
                # Intentar parsear mensajes completos
                while True:
                    if self.use_mllp:
                        msg, buffer = self._try_extract_mllp(buffer)
                        if msg is None:
                            break
                        self._handle_hl7_v2_message(msg)
                        continue

                    # HL7 plano: intentar por MSH.. (segmentos \r). Procesamos por “bloques”
                    msg, buffer = self._try_extract_plain_hl7(buffer)
                    if msg is None:
                        break
                    self._handle_hl7_v2_message(msg)

            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error al procesar mensajes de {self.nombre}: {e}")
                break
        
        if self.cliente_socket:
            try:
                self.cliente_socket.close()
            except:
                pass
            self.cliente_socket = None
    
    def _try_extract_mllp(self, buffer: bytes) -> tuple[Optional[str], bytes]:
        """Extrae un mensaje MLLP si está completo. Retorna (msg, new_buffer)."""
        SB = b'\x0b'
        EB = b'\x1c'
        CR = b'\x0d'

        start = buffer.find(SB)
        if start == -1:
            return None, buffer
        end = buffer.find(EB + CR, start + 1)
        if end == -1:
            return None, buffer

        payload = buffer[start + 1:end]
        rest = buffer[end + 2:]
        msg = payload.decode(self.encoding, errors='replace')
        return msg, rest

    def _try_extract_plain_hl7(self, buffer: bytes) -> tuple[Optional[str], bytes]:
        """Heurística simple: si hay un MSH y al menos un OBX/OBR, procesar hasta el final actual."""
        txt = buffer.decode(self.encoding, errors='replace')
        if 'MSH|' not in txt:
            return None, buffer

        # En HL7 v2 los segmentos se separan por \r, pero a veces llegan como \n.
        # Si aún no hay OBR/OBX, esperamos más.
        if ('\rOBR|' not in txt) and ('\nOBR|' not in txt) and ('\rOBX|' not in txt) and ('\nOBX|' not in txt):
            return None, buffer

        # Consumir todo lo que hay (el equipo suele cerrar conexión tras enviar + recibir ACK)
        return txt, b''

    def _handle_hl7_v2_message(self, hl7_text: str):
        """Genera ACK y dispara callback con hl7_raw."""
        try:
            ack = self._build_ack(hl7_text)
            self._send_ack(ack)

            payload = {
                'equipo': self.nombre,
                'tipo_mensaje': 'HL7v2',
                'hl7_raw': hl7_text,
            }
            if self.on_result:
                self.on_result(payload)

        except Exception as e:
            logger.error(f"Error manejando HL7v2 de {self.nombre}: {e}")
    
    def _build_ack(self, hl7_text: str) -> str:
        """Construye un ACK AA mínimo para el Message Control ID del MSH."""
        # Normalizar separadores
        msg = hl7_text.replace('\n', '\r')
        msh_line = None
        for seg in msg.split('\r'):
            if seg.startswith('MSH|'):
                msh_line = seg
                break

        if not msh_line:
            # ACK genérico
            ctrl_id = str(int(time.time() * 1000))
            return (
                f"MSH|^~\\&|||{self.nombre}|PRISLAB|{datetime.utcnow().strftime('%Y%m%d%H%M%S')}||ACK|{ctrl_id}|P|2.5\r"
                f"MSA|AA|{ctrl_id}\r"
            )

        parts = msh_line.split('|')
        # HL7 v2: MSH-10 es Message Control ID
        ctrl_id = parts[9] if len(parts) > 9 else str(int(time.time() * 1000))

        sending_app = parts[2] if len(parts) > 2 else ''
        sending_fac = parts[3] if len(parts) > 3 else ''
        receiving_app = parts[4] if len(parts) > 4 else ''
        receiving_fac = parts[5] if len(parts) > 5 else ''

        # Invertimos sender/receiver para el ACK
        dtm = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return (
            f"MSH|^~\\&|{receiving_app}|{receiving_fac}|{sending_app}|{sending_fac}|{dtm}||ACK|{ctrl_id}|P|2.5\r"
            f"MSA|AA|{ctrl_id}\r"
        )

    def _send_ack(self, ack_text: str):
        if not self.cliente_socket:
            return
        payload = ack_text.replace('\n', '\r').encode(self.encoding, errors='replace')
        if self.use_mllp:
            payload = b'\x0b' + payload + b'\x1c\x0d'
        try:
            self.cliente_socket.sendall(payload)
        except Exception as e:
            logger.warning(f"No se pudo enviar ACK a {self.nombre}: {e}")
    
    def procesar(self):
        """Procesa datos pendientes (método llamado en loop principal)."""
        if self.thread and self.thread.is_alive():
            return {
                'modo': 'hilo_tcp',
                'escuchando': bool(self.socket),
                'cliente_conectado': bool(self.cliente_socket),
                'buffer_pendiente': len(self._buffer_loop),
            }

        bytes_leidos = 0
        if self.cliente_socket:
            try:
                data = self.cliente_socket.recv(4096)
            except socket.timeout:
                data = b''

            if data:
                self._buffer_loop += data
                bytes_leidos = len(data)
                self._procesar_buffer_loop()

        return {
            'modo': 'loop_tcp',
            'escuchando': bool(self.socket),
            'cliente_conectado': bool(self.cliente_socket),
            'bytes_leidos': bytes_leidos,
            'buffer_pendiente': len(self._buffer_loop),
        }

    def _procesar_buffer_loop(self):
        """Drena mensajes HL7 completos acumulados por procesar()."""
        while True:
            if self.use_mllp:
                msg, self._buffer_loop = self._try_extract_mllp(self._buffer_loop)
            else:
                msg, self._buffer_loop = self._try_extract_plain_hl7(self._buffer_loop)

            if msg is None:
                break
            self._handle_hl7_v2_message(msg)
