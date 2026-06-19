#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Driver para InCCA Química
Implementa comunicación serial con protocolo ASTM 1394.

Características:
- Conexión serial (RS-232)
- Protocolo ASTM 1394 (STX, ETX, Checksum)
- Decodificación de tramas estándar
"""

import threading
import logging
from typing import Optional, Callable, Dict, Any
import time

from .serial_compat import serial

logger = logging.getLogger(__name__)


class InCCAChemDriver:
    """
    Driver para equipos InCCA que comunican por puerto serial con ASTM 1394.
    """
    
    # Constantes ASTM 1394
    STX = b'\x02'  # Start of Text
    ETX = b'\x03'  # End of Text
    ENQ = b'\x05'  # Enquiry
    ACK = b'\x06'  # Acknowledge
    NAK = b'\x15'  # Negative Acknowledge
    EOT = b'\x04'  # End of Transmission
    LF = b'\x0A'   # Line Feed
    CR = b'\x0D'   # Carriage Return
    CRLF = CR + LF
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el driver con la configuración del equipo.
        
        Args:
            config: Configuración del equipo desde config.yaml
        """
        self.config = config
        self.nombre = config.get('nombre', 'InCCA Química')
        self.puerto = config.get('puerto', 'COM1')
        self.baudrate = config.get('baudrate', 9600)
        self.bytesize = config.get('bytesize', 8)
        self.parity = config.get('parity', 'N')
        self.stopbits = config.get('stopbits', 1)
        self.timeout = config.get('timeout', 1.0)
        
        self.serial_port: Optional[serial.Serial] = None
        self.running = False
        self.thread = None
        self.on_result: Optional[Callable] = None
        self.buffer = b''
        
        logger.info(f"Driver InCCA inicializado: {self.nombre} - {self.puerto}@{self.baudrate}")
    
    def conectar(self):
        """Establece la conexión serial."""
        try:
            # Configurar puerto serial
            self.serial_port = serial.Serial(
                port=self.puerto,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout
            )
            
            logger.info(f"✅ Conectado a {self.puerto} para {self.nombre}")
            
            # Iniciar hilo de lectura
            self.running = True
            self.thread = threading.Thread(target=self._leer_datos, daemon=True)
            self.thread.start()
            
            # Enviar ENQ (Enquiry) para iniciar comunicación
            self._enviar_enq()
            
        except serial.SerialException as e:
            logger.error(f"Error al conectar {self.nombre} en {self.puerto}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al conectar {self.nombre}: {e}")
            raise
    
    def desconectar(self):
        """Cierra la conexión serial."""
        self.running = False
        
        if self.serial_port and self.serial_port.is_open:
            try:
                # Enviar EOT antes de desconectar
                self._enviar_eot()
                time.sleep(0.1)
                self.serial_port.close()
            except:
                pass
            self.serial_port = None
        
        logger.info(f"Desconectado: {self.nombre}")
    
    def _enviar_enq(self):
        """Envía ENQ (Enquiry) al equipo."""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(self.ENQ)
                logger.debug(f"ENQ enviado a {self.nombre}")
        except Exception as e:
            logger.error(f"Error al enviar ENQ a {self.nombre}: {e}")
    
    def _enviar_ack(self):
        """Envía ACK (Acknowledge) al equipo."""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(self.ACK)
                logger.debug(f"ACK enviado a {self.nombre}")
        except Exception as e:
            logger.error(f"Error al enviar ACK a {self.nombre}: {e}")
    
    def _enviar_nak(self):
        """Envía NAK (Negative Acknowledge) al equipo."""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(self.NAK)
                logger.debug(f"NAK enviado a {self.nombre}")
        except Exception as e:
            logger.error(f"Error al enviar NAK a {self.nombre}: {e}")
    
    def _enviar_eot(self):
        """Envía EOT (End of Transmission) al equipo."""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(self.EOT)
                logger.debug(f"EOT enviado a {self.nombre}")
        except Exception as e:
            logger.error(f"Error al enviar EOT a {self.nombre}: {e}")
    
    def _leer_datos(self):
        """Lee datos del puerto serial en un hilo separado."""
        while self.running:
            try:
                if not self.serial_port or not self.serial_port.is_open:
                    break
                
                # Leer datos disponibles
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    self.buffer += data
                    
                    # Procesar tramas completas
                    self._procesar_buffer()
                else:
                    time.sleep(0.1)
                    
            except serial.SerialException as e:
                logger.error(f"Error de lectura serial en {self.nombre}: {e}")
                break
            except Exception as e:
                if self.running:
                    logger.error(f"Error inesperado en lectura de {self.nombre}: {e}")
                break
    
    def _procesar_buffer(self):
        """Procesa el buffer de datos buscando tramas ASTM 1394 completas."""
        while True:
            # Buscar STX (Start of Text)
            stx_pos = self.buffer.find(self.STX)
            if stx_pos == -1:
                # No hay inicio de trama, limpiar buffer
                if len(self.buffer) > 1000:  # Limitar tamaño del buffer
                    self.buffer = self.buffer[-500:]
                break
            
            # Remover datos antes del STX
            self.buffer = self.buffer[stx_pos:]
            
            # Buscar ETX (End of Text)
            etx_pos = self.buffer.find(self.ETX, 1)
            if etx_pos == -1:
                # Trama incompleta, esperar más datos
                break
            
            # Extraer trama completa (STX + datos + ETX + checksum)
            trama_completa = self.buffer[:etx_pos + 3]  # STX + datos + ETX + 2 bytes checksum
            self.buffer = self.buffer[etx_pos + 3:]
            
            # Validar checksum
            if self._validar_checksum(trama_completa):
                # Procesar trama
                self._procesar_trama_astm(trama_completa)
                # Enviar ACK
                self._enviar_ack()
            else:
                logger.warning(f"Checksum inválido en trama de {self.nombre}")
                # Enviar NAK
                self._enviar_nak()
    
    def _validar_checksum(self, trama: bytes) -> bool:
        """
        Valida el checksum de una trama ASTM 1394.
        
        Args:
            trama: Trama completa incluyendo STX, ETX y checksum
            
        Returns:
            True si el checksum es válido
        """
        try:
            if len(trama) < 4:
                return False
            
            # STX no cuenta en el checksum
            # Checksum son los últimos 2 bytes (ASCII hexadecimal)
            checksum_recibido = trama[-2:].decode('ascii')
            
            # ASTM suma desde el primer byte tras STX hasta ETX incluido.
            datos = trama[1:-2]
            suma = sum(datos) & 0xFF
            checksum_calculado = f"{suma:02X}"
            
            return checksum_recibido == checksum_calculado
            
        except Exception as e:
            logger.error(f"Error al validar checksum: {e}")
            return False
    
    def _procesar_trama_astm(self, trama: bytes):
        """
        Procesa una trama ASTM 1394 válida.
        
        Args:
            trama: Trama completa con STX, datos, ETX y checksum
        """
        try:
            # Extraer datos (entre STX y ETX)
            datos = trama[1:-3].decode('ascii', errors='ignore')
            
            # Parsear según formato ASTM
            resultado = self._parsear_astm(datos)
            
            if resultado:
                logger.info(f"📋 Resultado ASTM recibido de {self.nombre}")
                
                if self.on_result:
                    self.on_result(resultado)
                    
        except Exception as e:
            logger.error(f"Error al procesar trama ASTM de {self.nombre}: {e}")
    
    def _parsear_astm(self, datos: str) -> Optional[Dict[str, Any]]:
        """
        Parsea los datos según formato ASTM 1394.
        
        Args:
            datos: Cadena de datos entre STX y ETX
            
        Returns:
            Diccionario con el resultado parseado
        """
        try:
            # ASTM 1394 usa campos separados por | y registros separados por \r
            registros = datos.split('\r')
            
            resultado = {
                'equipo': self.nombre,
                'tipo_mensaje': 'ASTM 1394',
                'registros': [],
            }
            
            for registro in registros:
                if not registro.strip():
                    continue
                
                campos = registro.split('|')
                tipo_registro = campos[0] if campos else ''
                
                if tipo_registro == 'H':
                    # Header Record
                    resultado['header'] = {
                        'id_equipo': campos[2] if len(campos) > 2 else None,
                    }
                elif tipo_registro == 'P':
                    # Patient Record
                    resultado['paciente'] = {
                        'id': campos[2] if len(campos) > 2 else None,
                        'nombre': campos[5] if len(campos) > 5 else None,
                    }
                elif tipo_registro == 'O':
                    # Order Record
                    resultado['orden'] = {
                        'id': campos[2] if len(campos) > 2 else None,
                    }
                elif tipo_registro == 'R':
                    # Result Record
                    resultado['registros'].append({
                        'codigo_prueba': campos[2] if len(campos) > 2 else None,
                        'valor': campos[3] if len(campos) > 3 else None,
                        'unidad': campos[4] if len(campos) > 4 else None,
                        'rango': campos[5] if len(campos) > 5 else None,
                    })
                elif tipo_registro == 'L':
                    # Terminator Record
                    break
            
            return resultado if resultado.get('registros') or resultado.get('paciente') else None
            
        except Exception as e:
            logger.error(f"Error al parsear ASTM: {e}")
            return None
    
    def procesar(self):
        """Procesa datos pendientes (método llamado en loop principal)."""
        if self.thread and self.thread.is_alive():
            return {
                'modo': 'hilo_serial',
                'conectado': bool(self.serial_port and self.serial_port.is_open),
                'buffer_pendiente': len(self.buffer),
            }

        bytes_leidos = 0
        try:
            if self.serial_port and self.serial_port.is_open:
                disponibles = int(getattr(self.serial_port, 'in_waiting', 0) or 0)
                if disponibles > 0:
                    data = self.serial_port.read(disponibles)
                    if data:
                        self.buffer += data
                        bytes_leidos = len(data)

            if self.buffer:
                self._procesar_buffer()

            return {
                'modo': 'loop_serial',
                'conectado': bool(self.serial_port and self.serial_port.is_open),
                'bytes_leidos': bytes_leidos,
                'buffer_pendiente': len(self.buffer),
            }
        except serial.SerialException as e:
            logger.error(f"Error de lectura serial en {self.nombre}: {e}")
            raise
