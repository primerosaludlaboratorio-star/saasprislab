#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Driver para Mission U120
Implementa lectura de puerto serial con formato de texto simple.

Características:
- Conexión serial (RS-232)
- Formato de texto simple con separadores
- Parsing de resultados de laboratorio
"""

import serial
import threading
import logging
from typing import Optional, Callable, Dict, Any
import time
import re

logger = logging.getLogger(__name__)


class MissionU120Driver:
    """
    Driver para equipos Mission U120 que comunican por puerto serial con texto simple.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el driver con la configuración del equipo.
        
        Args:
            config: Configuración del equipo desde config.yaml
        """
        self.config = config
        self.nombre = config.get('nombre', 'Mission U120')
        self.puerto = config.get('puerto', 'COM1')
        self.baudrate = config.get('baudrate', 9600)
        self.bytesize = config.get('bytesize', 8)
        self.parity = config.get('parity', 'N')
        self.stopbits = config.get('stopbits', 1)
        self.timeout = config.get('timeout', 1.0)
        self.delimiter = config.get('delimiter', '\r\n')
        
        self.serial_port: Optional[serial.Serial] = None
        self.running = False
        self.thread = None
        self.on_result: Optional[Callable] = None
        self.buffer = ""
        
        logger.info(f"Driver Mission U120 inicializado: {self.nombre} - {self.puerto}@{self.baudrate}")
    
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
                self.serial_port.close()
            except:
                pass
            self.serial_port = None
        
        logger.info(f"Desconectado: {self.nombre}")
    
    def _leer_datos(self):
        """Lee datos del puerto serial en un hilo separado."""
        while self.running:
            try:
                if not self.serial_port or not self.serial_port.is_open:
                    break
                
                # Leer datos disponibles
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                    self.buffer += data
                    
                    # Procesar líneas completas
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
        """Procesa el buffer de datos buscando líneas completas."""
        while self.delimiter in self.buffer:
            # Extraer línea completa
            linea, self.buffer = self.buffer.split(self.delimiter, 1)
            linea = linea.strip()
            
            if linea:
                # Procesar línea
                self._procesar_linea(linea)
    
    def _procesar_linea(self, linea: str):
        """
        Procesa una línea de datos recibida del equipo.
        
        Args:
            linea: Línea de texto recibida del equipo
        """
        try:
            # Parsear según formato Mission U120
            resultado = self._parsear_mission(linea)
            
            if resultado:
                logger.info(f"📋 Resultado recibido de {self.nombre}")
                
                if self.on_result:
                    self.on_result(resultado)
                    
        except Exception as e:
            logger.error(f"Error al procesar línea de {self.nombre}: {e}")
    
    def _parsear_mission(self, linea: str) -> Optional[Dict[str, Any]]:
        """
        Parsea una línea de datos según formato Mission U120.
        
        Formato típico puede ser:
        - Separado por comas: "Paciente_ID,Código_Prueba,Resultado,Unidad,Fecha"
        - Separado por tabs: "Paciente_ID\tCódigo_Prueba\tResultado\tUnidad\tFecha"
        - Formato fijo con posiciones específicas
        
        Args:
            linea: Línea de texto a parsear
            
        Returns:
            Diccionario con el resultado parseado
        """
        try:
            # Intentar diferentes formatos comunes
            
            # Formato separado por comas
            if ',' in linea:
                campos = [c.strip() for c in linea.split(',')]
                if len(campos) >= 3:
                    return {
                        'equipo': self.nombre,
                        'tipo_mensaje': 'texto_separado',
                        'paciente_id': campos[0] if len(campos) > 0 else None,
                        'codigo_prueba': campos[1] if len(campos) > 1 else None,
                        'resultado': campos[2] if len(campos) > 2 else None,
                        'unidad': campos[3] if len(campos) > 3 else None,
                        'fecha': campos[4] if len(campos) > 4 else None,
                    }
            
            # Formato separado por tabs
            elif '\t' in linea:
                campos = [c.strip() for c in linea.split('\t')]
                if len(campos) >= 3:
                    return {
                        'equipo': self.nombre,
                        'tipo_mensaje': 'texto_separado',
                        'paciente_id': campos[0] if len(campos) > 0 else None,
                        'codigo_prueba': campos[1] if len(campos) > 1 else None,
                        'resultado': campos[2] if len(campos) > 2 else None,
                        'unidad': campos[3] if len(campos) > 3 else None,
                        'fecha': campos[4] if len(campos) > 4 else None,
                    }
            
            # Formato separado por pipes
            elif '|' in linea:
                campos = [c.strip() for c in linea.split('|')]
                if len(campos) >= 3:
                    return {
                        'equipo': self.nombre,
                        'tipo_mensaje': 'texto_separado',
                        'paciente_id': campos[0] if len(campos) > 0 else None,
                        'codigo_prueba': campos[1] if len(campos) > 1 else None,
                        'resultado': campos[2] if len(campos) > 2 else None,
                        'unidad': campos[3] if len(campos) > 3 else None,
                        'fecha': campos[4] if len(campos) > 4 else None,
                    }
            
            # Intentar parsear con regex (para formatos más complejos)
            # Ejemplo: "ID:12345 TEST:GLU RESULT:95.5 mg/dL"
            regex_pattern = r'ID[:\s]+(\w+).*?TEST[:\s]+(\w+).*?RESULT[:\s]+([\d.]+)\s*(\w+)?'
            match = re.search(regex_pattern, linea, re.IGNORECASE)
            if match:
                return {
                    'equipo': self.nombre,
                    'tipo_mensaje': 'texto_regex',
                    'paciente_id': match.group(1),
                    'codigo_prueba': match.group(2),
                    'resultado': match.group(3),
                    'unidad': match.group(4) if match.lastindex >= 4 else None,
                }
            
            # Si no coincide con ningún formato conocido, devolver línea completa
            logger.warning(f"Formato no reconocido de {self.nombre}: {linea[:100]}")
            return {
                'equipo': self.nombre,
                'tipo_mensaje': 'texto_crudo',
                'datos_crudos': linea,
            }
            
        except Exception as e:
            logger.error(f"Error al parsear línea Mission: {e}")
            return None
    
    def procesar(self):
        """Procesa datos pendientes (método llamado en loop principal)."""
        # El procesamiento se hace en el hilo de lectura
        pass
