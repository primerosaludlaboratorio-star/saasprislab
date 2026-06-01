#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Driver para Fuji DRI-CHEM NX600
Implementa comunicación serial con protocolo Fuji DRI-CHEM.

Características:
- Conexión serial (RS-232)
- Protocolo: Tramas con STX (0x02) y ETX (0x03)
- Formato: Posicional o delimitado por comas/tabuladores
- Mapeo de códigos Fuji a códigos internos PRISLAB
"""

import serial
import serial.tools.list_ports
import threading
import logging
import re
from typing import Optional, Callable, Dict, Any, List
import time
from datetime import datetime

logger = logging.getLogger(__name__)


# Mapeo de códigos Fuji a códigos internos PRISLAB
MAPEO_CODIGOS_FUJI = {
    # Química Clínica - Glucosa
    'GLU-P': 'GLU',  # Glucosa (Plasma)
    'GLU': 'GLU',    # Glucosa (Sangre)
    'BS': 'GLU',     # Blood Sugar
    
    # Función Renal
    'BUN': 'URE',    # Blood Urea Nitrogen -> Urea
    'URE': 'URE',    # Urea
    'CRE': 'CRE',    # Creatinina
    'CREA': 'CRE',   # Creatinina (alternativo)
    'BUN/CRE': 'BUN_CRE',  # Ratio BUN/Creatinina
    
    # Enzimas
    'ALT': 'ALT',    # Alanina Aminotransferasa
    'GPT': 'ALT',    # GPT -> ALT
    'AST': 'AST',    # Aspartato Aminotransferasa
    'GOT': 'AST',    # GOT -> AST
    'LDH': 'LDH',    # Lactato Deshidrogenasa
    'ALP': 'ALP',    # Fosfatasa Alcalina
    'ALP-P': 'ALP',  # Fosfatasa Alcalina (Plasma)
    'GGT': 'GGT',    # Gamma Glutamil Transferasa
    'γ-GT': 'GGT',   # Gamma Glutamil Transferasa (griega)
    
    # Lípidos
    'TG': 'TGL',     # Triglicéridos
    'TG-P': 'TGL',   # Triglicéridos (Plasma)
    'CHOL': 'COL',   # Colesterol Total
    'TC': 'COL',     # Total Cholesterol
    'HDL-C': 'HDL',  # HDL Colesterol
    'LDL-C': 'LDL',  # LDL Colesterol
    
    # Función Hepática
    'TP': 'PROT',    # Proteínas Totales
    'TBIL': 'BILT',  # Bilirrubina Total
    'DBIL': 'BILD',  # Bilirrubina Directa
    'IBIL': 'BILI',  # Bilirrubina Indirecta
    'ALB': 'ALB',    # Albúmina
    
    # Electrolitos
    'Na': 'NA',      # Sodio
    'K': 'K',        # Potasio
    'Cl': 'CL',      # Cloro
    'CO2': 'CO2',    # Dióxido de Carbono
    'HCO3': 'HCO3',  # Bicarbonato
    
    # Otros
    'CK': 'CK',      # Creatina Quinasa
    'CK-MB': 'CK_MB', # Creatina Quinasa MB
    'AMY': 'AMY',    # Amilasa
    'LIP': 'LIP',    # Lipasa
    'UA': 'ACU',     # Ácido Úrico
}


class FujiNX600Driver:
    """
    Driver para equipos Fuji DRI-CHEM NX600 que comunican por puerto serial.
    """
    
    # Constantes del protocolo
    STX = b'\x02'  # Start of Text
    ETX = b'\x03'  # End of Text
    CR = b'\r'     # Carriage Return
    LF = b'\n'     # Line Feed
    CRLF = CR + LF
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el driver con la configuración del equipo.
        
        Args:
            config: Configuración del equipo desde config.yaml
        """
        self.config = config
        self.nombre = config.get('nombre', 'Fuji NX600')
        self.puerto = config.get('puerto', 'COM3')
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
        
        logger.info(f"Driver Fuji NX600 inicializado: {self.nombre} - {self.puerto}@{self.baudrate}")
    
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
        """Procesa el buffer de datos buscando tramas Fuji completas."""
        while True:
            # Buscar STX (Start of Text)
            stx_pos = self.buffer.find(self.STX)
            if stx_pos == -1:
                # No hay inicio de trama, limpiar buffer si es muy grande
                if len(self.buffer) > 1000:
                    self.buffer = self.buffer[-500:]
                break
            
            # Remover datos antes del STX
            self.buffer = self.buffer[stx_pos:]
            
            # Buscar ETX (End of Text)
            etx_pos = self.buffer.find(self.ETX, 1)
            if etx_pos == -1:
                # Trama incompleta, esperar más datos
                break
            
            # Extraer trama completa (STX + datos + ETX)
            trama_completa = self.buffer[:etx_pos + 1]
            self.buffer = self.buffer[etx_pos + 1:]
            
            # Procesar trama
            self._procesar_trama_fuji(trama_completa)
    
    def _procesar_trama_fuji(self, trama: bytes):
        """
        Procesa una trama Fuji DRI-CHEM válida.
        
        Args:
            trama: Trama completa con STX, datos y ETX
        """
        try:
            # Extraer datos (entre STX y ETX)
            datos = trama[1:-1].decode('ascii', errors='ignore')
            
            # Parsear según formato Fuji
            resultado = self._parsear_fuji(datos)
            
            if resultado:
                logger.info(f"📋 Resultado Fuji recibido de {self.nombre}")
                
                if self.on_result:
                    self.on_result(resultado)
                    
        except Exception as e:
            logger.error(f"Error al procesar trama Fuji de {self.nombre}: {e}")
    
    def _parsear_fuji(self, datos: str) -> Optional[Dict[str, Any]]:
        """
        Parsea los datos según formato Fuji DRI-CHEM.
        
        Los datos pueden venir en formato:
        - Delimitado por comas: "GLU-P,95.5,mg/dL,NORMAL"
        - Delimitado por tabuladores: "GLU-P\t95.5\tmg/dL\tNORMAL"
        - Posicional: Formato fijo de columnas
        
        Args:
            datos: Cadena de datos entre STX y ETX
            
        Returns:
            Diccionario con el resultado parseado
        """
        try:
            # Intentar diferentes formatos
            resultado = {
                'equipo': self.nombre,
                'tipo_mensaje': 'Fuji DRI-CHEM',
                'resultados': [],
                'timestamp': datetime.now().isoformat(),
            }
            
            # Dividir por líneas (CR, LF o CRLF)
            lineas = re.split(r'\r\n|\r|\n', datos)
            
            for linea in lineas:
                linea = linea.strip()
                if not linea:
                    continue
                
                # Intentar formato delimitado por comas
                if ',' in linea:
                    campos = [c.strip() for c in linea.split(',')]
                    resultado_parseado = self._parsear_campos_delimitados(campos)
                    if resultado_parseado:
                        resultado['resultados'].append(resultado_parseado)
                
                # Intentar formato delimitado por tabuladores
                elif '\t' in linea:
                    campos = [c.strip() for c in linea.split('\t')]
                    resultado_parseado = self._parsear_campos_delimitados(campos)
                    if resultado_parseado:
                        resultado['resultados'].append(resultado_parseado)
                
                # Intentar formato posicional
                else:
                    resultado_parseado = self._parsear_formato_posicional(linea)
                    if resultado_parseado:
                        resultado['resultados'].append(resultado_parseado)
            
            # Si no hay resultados, intentar parsear la línea completa
            if not resultado['resultados'] and datos:
                campos = [c.strip() for c in re.split(r'[,;\t\s]+', datos) if c.strip()]
                if len(campos) >= 2:
                    resultado_parseado = self._parsear_campos_delimitados(campos)
                    if resultado_parseado:
                        resultado['resultados'].append(resultado_parseado)
            
            return resultado if resultado.get('resultados') else None
            
        except Exception as e:
            logger.error(f"Error al parsear datos Fuji: {e}")
            return None
    
    def _parsear_campos_delimitados(self, campos: List[str]) -> Optional[Dict[str, Any]]:
        """
        Parsea campos delimitados típicos de Fuji DRI-CHEM.
        
        Formato esperado:
        - Campo 0: Código de prueba (ej: GLU-P, CRE, BUN)
        - Campo 1: Valor numérico
        - Campo 2: Unidad (opcional, ej: mg/dL, U/L)
        - Campo 3: Estado/Comentario (opcional, ej: NORMAL, HIGH, LOW)
        
        Args:
            campos: Lista de campos parseados
            
        Returns:
            Diccionario con el resultado de una prueba
        """
        try:
            if len(campos) < 2:
                return None
            
            codigo_fuji = campos[0].strip().upper()
            valor_str = campos[1].strip()
            
            # Mapear código Fuji a código PRISLAB
            codigo_prislab = MAPEO_CODIGOS_FUJI.get(codigo_fuji, codigo_fuji)
            
            # Intentar convertir valor a número
            try:
                # Eliminar caracteres no numéricos excepto punto y signo negativo
                valor_limpio = re.sub(r'[^\d\.\-\+]', '', valor_str)
                valor = float(valor_limpio) if valor_limpio else None
            except (ValueError, TypeError):
                valor = None
            
            # Obtener unidad si existe
            unidad = campos[2].strip() if len(campos) > 2 else None
            
            # Obtener estado/comentario si existe
            estado = campos[3].strip() if len(campos) > 3 else None
            
            if valor is None:
                logger.warning(f"Valor inválido en resultado Fuji: {valor_str}")
                return None
            
            return {
                'codigo_fuji': codigo_fuji,
                'codigo_prislab': codigo_prislab,
                'valor': valor,
                'unidad': unidad or 'N/A',
                'estado': estado or 'NORMAL',
                'equipo': self.nombre,
            }
            
        except Exception as e:
            logger.error(f"Error al parsear campos delimitados: {e}")
            return None
    
    def _parsear_formato_posicional(self, linea: str) -> Optional[Dict[str, Any]]:
        """
        Parsea formato posicional (columnas fijas).
        
        Este método intenta extraer datos de un formato posicional,
        aunque el formato exacto puede variar según la configuración del equipo.
        
        Args:
            linea: Línea de datos en formato posicional
            
        Returns:
            Diccionario con el resultado de una prueba
        """
        try:
            # Los formatos posicionales de Fuji suelen tener:
            # - Código de prueba en posiciones 0-10
            # - Valor en posiciones 11-20
            # - Unidad en posiciones 21-30
            # - Estado en posiciones 31-40
            
            if len(linea) < 20:
                return None
            
            codigo_fuji = linea[0:10].strip().upper()
            valor_str = linea[11:20].strip()
            unidad = linea[21:30].strip() if len(linea) > 30 else None
            estado = linea[31:40].strip() if len(linea) > 40 else None
            
            # Mapear código Fuji a código PRISLAB
            codigo_prislab = MAPEO_CODIGOS_FUJI.get(codigo_fuji, codigo_fuji)
            
            # Intentar convertir valor a número
            try:
                valor_limpio = re.sub(r'[^\d\.\-\+]', '', valor_str)
                valor = float(valor_limpio) if valor_limpio else None
            except (ValueError, TypeError):
                valor = None
            
            if valor is None:
                return None
            
            return {
                'codigo_fuji': codigo_fuji,
                'codigo_prislab': codigo_prislab,
                'valor': valor,
                'unidad': unidad or 'N/A',
                'estado': estado or 'NORMAL',
                'equipo': self.nombre,
            }
            
        except Exception as e:
            logger.error(f"Error al parsear formato posicional: {e}")
            return None
    
    def procesar(self):
        """Procesa datos pendientes (método llamado en loop principal)."""
        # El procesamiento se hace en el hilo de lectura
        pass
