#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Driver para Wondfo Finecare y otros equipos LIS unidireccionales
Implementa lectura genérica de puerto serial o TCP/IP.

Características:
- Conexión serial o TCP/IP
- Protocolo genérico unidireccional
- Parsing flexible de resultados
"""

import serial
import socket
import threading
import logging
from typing import Optional, Callable, Dict, Any
import time

logger = logging.getLogger(__name__)


class WondfoFinecareDriver:
    """
    Driver genérico para equipos LIS unidireccionales como Wondfo Finecare.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el driver con la configuración del equipo.
        
        Args:
            config: Configuración del equipo desde config.yaml
        """
        self.config = config
        self.nombre = config.get('nombre', 'Wondfo Finecare')
        self.tipo = config.get('tipo', 'serial')  # 'serial' o 'tcp'
        
        # Configuración serial
        self.puerto = config.get('puerto', 'COM1')
        self.baudrate = config.get('baudrate', 9600)
        
        # Configuración TCP/IP
        self.ip = config.get('ip', '127.0.0.1')
        self.puerto_tcp = config.get('puerto', 5000)
        
        # Configuración general
        self.delimiter = config.get('delimiter', '\r\n')
        self.encoding = config.get('encoding', 'utf-8')
        
        self.serial_port: Optional[serial.Serial] = None
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.thread = None
        self.on_result: Optional[Callable] = None
        self.buffer = ""
        
        logger.info(f"Driver Wondfo Finecare inicializado: {self.nombre} - Tipo: {self.tipo}")
    
    def conectar(self):
        """Establece la conexión según el tipo configurado."""
        if self.tipo == 'serial':
            self._conectar_serial()
        elif self.tipo == 'tcp':
            self._conectar_tcp()
        else:
            raise ValueError(f"Tipo de conexión no soportado: {self.tipo}")
    
    def _conectar_serial(self):
        """Establece la conexión serial."""
        try:
            self.serial_port = serial.Serial(
                port=self.puerto,
                baudrate=self.baudrate,
                timeout=1.0
            )
            
            logger.info(f"✅ Conectado serial a {self.puerto} para {self.nombre}")
            
            self.running = True
            self.thread = threading.Thread(target=self._leer_serial, daemon=True)
            self.thread.start()
            
        except serial.SerialException as e:
            logger.error(f"Error al conectar serial {self.nombre}: {e}")
            raise
    
    def _conectar_tcp(self):
        """Establece la conexión TCP/IP."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.ip, self.puerto_tcp))
            self.socket.settimeout(1.0)
            
            logger.info(f"✅ Conectado TCP/IP a {self.ip}:{self.puerto_tcp} para {self.nombre}")
            
            self.running = True
            self.thread = threading.Thread(target=self._leer_tcp, daemon=True)
            self.thread.start()
            
        except socket.error as e:
            logger.error(f"Error al conectar TCP/IP {self.nombre}: {e}")
            raise
    
    def desconectar(self):
        """Cierra la conexión."""
        self.running = False
        
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except:
                pass
            self.serial_port = None
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        logger.info(f"Desconectado: {self.nombre}")
    
    def _leer_serial(self):
        """Lee datos del puerto serial en un hilo separado."""
        while self.running:
            try:
                if not self.serial_port or not self.serial_port.is_open:
                    break
                
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting).decode(
                        self.encoding, errors='ignore'
                    )
                    self.buffer += data
                    self._procesar_buffer()
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                if self.running:
                    logger.error(f"Error en lectura serial de {self.nombre}: {e}")
                break
    
    def _leer_tcp(self):
        """Lee datos del socket TCP/IP en un hilo separado."""
        while self.running:
            try:
                if not self.socket:
                    break
                
                data = self.socket.recv(4096).decode(self.encoding, errors='ignore')
                if not data:
                    break
                
                self.buffer += data
                self._procesar_buffer()
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error en lectura TCP/IP de {self.nombre}: {e}")
                break
    
    def _procesar_buffer(self):
        """Procesa el buffer de datos buscando mensajes completos."""
        while self.delimiter in self.buffer:
            mensaje, self.buffer = self.buffer.split(self.delimiter, 1)
            mensaje = mensaje.strip()
            
            if mensaje:
                self._procesar_mensaje(mensaje)
    
    def _procesar_mensaje(self, mensaje: str):
        """
        Procesa un mensaje recibido del equipo.
        
        Args:
            mensaje: Mensaje de texto recibido
        """
        try:
            # Parsear según formato genérico
            resultado = self._parsear_mensaje_generico(mensaje)
            
            if resultado:
                logger.info(f"📋 Resultado recibido de {self.nombre}")
                
                if self.on_result:
                    self.on_result(resultado)
                    
        except Exception as e:
            logger.error(f"Error al procesar mensaje de {self.nombre}: {e}")
    
    def _parsear_mensaje_generico(self, mensaje: str) -> Optional[Dict[str, Any]]:
        """
        Parsea un mensaje de forma genérica.
        
        Intenta varios formatos comunes y devuelve la mejor interpretación.
        
        Args:
            mensaje: Mensaje de texto a parsear
            
        Returns:
            Diccionario con el resultado parseado
        """
        try:
            resultado = {
                'equipo': self.nombre,
                'tipo_mensaje': 'generico',
                'datos_crudos': mensaje,
            }
            
            # Intentar extraer información con diferentes separadores
            separadores = [',', '\t', '|', ';', ' ']
            
            for sep in separadores:
                if sep in mensaje and mensaje.count(sep) >= 2:
                    partes = [p.strip() for p in mensaje.split(sep)]
                    
                    # Si hay suficientes partes, intentar interpretarlas
                    if len(partes) >= 3:
                        resultado['tipo_mensaje'] = f'separado_{sep}'
                        resultado['campos'] = partes
                        
                        # Intentar identificar campos comunes
                        # Asumir: [0]=ID, [1]=Código, [2]=Valor, [3]=Unidad, etc.
                        if len(partes) > 0:
                            resultado['paciente_id'] = partes[0]
                        if len(partes) > 1:
                            resultado['codigo_prueba'] = partes[1]
                        if len(partes) > 2:
                            resultado['resultado'] = partes[2]
                        if len(partes) > 3:
                            resultado['unidad'] = partes[3]
                        if len(partes) > 4:
                            resultado['fecha'] = partes[4]
                        
                        return resultado
            
            # Si no se pudo parsear, devolver mensaje crudo
            return resultado
            
        except Exception as e:
            logger.error(f"Error al parsear mensaje genérico: {e}")
            return None
    
    def procesar(self):
        """Procesa datos pendientes (método llamado en loop principal)."""
        # El procesamiento se hace en el hilo de lectura
        pass
