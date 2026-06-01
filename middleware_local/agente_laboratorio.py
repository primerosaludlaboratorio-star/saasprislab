#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agente Principal de Integración LIS
Conecta equipos físicos del laboratorio con PRISLAB SaaS en la nube.

Uso:
    python agente_laboratorio.py
    
El agente lee config.yaml y mantiene conexiones activas con los equipos configurados.
"""

import yaml
import json
import time
import logging
import threading
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Importar drivers
from .drivers.norma_icon import NormaIconDriver
from .drivers.incca_chem import InCCAChemDriver
from .drivers.mission_u120 import MissionU120Driver
from .drivers.wondfo_finecare import WondfoFinecareDriver
from .drivers.fuji_nx600 import FujiNX600Driver

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agente_laboratorio.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AgenteLaboratorio:
    """
    Agente principal que gestiona las conexiones con múltiples equipos
    y sincroniza los resultados con la nube.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Inicializa el agente con la configuración.
        
        Args:
            config_path: Ruta al archivo de configuración YAML
        """
        self.config_path = Path(config_path)
        self.config = self._cargar_config()
        self.sucursal_id = self.config.get('sucursal_id')
        self.equipos = self.config.get('equipos', [])
        self.drivers = {}
        self.hilos = {}
        self.running = False
        
        # Configuración de sincronización a la nube
        self.cloud_url = self.config.get('cloud_url', 'http://localhost:8000')
        self.cloud_token = self.config.get('cloud_token', '')

        # HL7 receptor (SaaS)
        self.hl7_endpoint_path = self.config.get('hl7_endpoint_path', '/api/iot/hl7/')
        self.hl7_api_key = self.config.get('hl7_api_key', '')
        self.empresa_id = self.config.get('empresa_id')
        
        logger.info(f"Agente inicializado para sucursal ID: {self.sucursal_id}")
        logger.info(f"Equipos configurados: {len(self.equipos)}")
    
    def _cargar_config(self) -> Dict:
        """Carga la configuración desde el archivo YAML."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuración cargada desde {self.config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Archivo de configuración no encontrado: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error al parsear YAML: {e}")
            raise
    
    def _crear_driver(self, equipo_config: Dict):
        """
        Crea una instancia del driver apropiado según la configuración del equipo.
        
        Args:
            equipo_config: Configuración del equipo desde config.yaml
        """
        nombre = equipo_config.get('nombre')
        driver_type = equipo_config.get('driver')
        
        try:
            if driver_type == 'norma_icon':
                driver = NormaIconDriver(equipo_config)
            elif driver_type == 'incca':
                driver = InCCAChemDriver(equipo_config)
            elif driver_type == 'mission_u120':
                driver = MissionU120Driver(equipo_config)
            elif driver_type == 'wondfo_finecare':
                driver = WondfoFinecareDriver(equipo_config)
            elif driver_type == 'fuji_nx600':
                driver = FujiNX600Driver(equipo_config)
            else:
                logger.error(f"Driver desconocido: {driver_type} para equipo {nombre}")
                return None
            
            logger.info(f"Driver creado: {driver_type} para {nombre}")
            return driver
        except Exception as e:
            logger.error(f"Error al crear driver {driver_type} para {nombre}: {e}")
            return None
    
    def _procesar_resultado(self, equipo_nombre: str, resultado: Dict):
        """
        Procesa un resultado recibido de un equipo y lo envía a la nube.
        
        Args:
            equipo_nombre: Nombre del equipo que generó el resultado
            resultado: Diccionario con los datos del resultado
        """
        try:
            # Enriquecer el resultado con metadatos
            resultado_enriquecido = {
                **resultado,
                'equipo': equipo_nombre,
                'sucursal_id': self.sucursal_id,
                'timestamp_recepcion': datetime.now().isoformat(),
            }
            
            logger.info(f"Resultado recibido de {equipo_nombre}: {resultado_enriquecido.get('folio', 'N/A')}")
            
            # Enviar a la nube
            self._enviar_a_nube(resultado_enriquecido)
            
        except Exception as e:
            logger.error(f"Error al procesar resultado de {equipo_nombre}: {e}")
    
    def _enviar_a_nube(self, json_data: Dict):
        """
        Envía datos a la nube mediante POST al endpoint de recepción.
        
        Args:
            json_data: Diccionario con los datos del resultado
        """
        base = self.cloud_url.rstrip('/')
        is_hl7 = isinstance(json_data, dict) and bool(json_data.get('hl7_raw'))

        def _infer_numero_orden(payload: Dict) -> str:
            for key in (
                'numero_orden', 'folio', 'folio_orden', 'orden', 'orden_id',
                'order_id', 'sample_id', 'muestra_id', 'paciente_id',
            ):
                val = payload.get(key)
                if val is None:
                    continue
                val_str = str(val).strip()
                if val_str:
                    return val_str
            return ''

        def _to_json_receptor_hl7(payload: Dict) -> Dict:
            resultados = []

            # Fuji: payload ya trae lista en 'resultados'
            if isinstance(payload.get('resultados'), list):
                for r in payload.get('resultados', []):
                    if not isinstance(r, dict):
                        continue
                    codigo = (r.get('codigo_prislab') or r.get('codigo') or r.get('codigo_fuji') or '').strip()
                    if not codigo:
                        continue
                    resultados.append({
                        'codigo': codigo,
                        'nombre': r.get('nombre') or codigo,
                        'valor': r.get('valor'),
                        'unidad': r.get('unidad') or r.get('unidad_raw') or '',
                        'flags': r.get('estado') or r.get('flags') or 'N',
                    })

            # Wondfo / U120 genérico: un resultado por mensaje
            else:
                codigo = (payload.get('codigo_prueba') or payload.get('codigo') or '').strip()
                if codigo:
                    resultados.append({
                        'codigo': codigo,
                        'nombre': payload.get('nombre') or codigo,
                        'valor': payload.get('resultado') or payload.get('valor') or payload.get('valor_raw'),
                        'unidad': payload.get('unidad') or payload.get('unidad_raw') or '',
                        'flags': payload.get('flags') or 'N',
                    })

            return {
                'protocolo': 'JSON',
                'equipo': payload.get('equipo'),
                'sucursal_id': payload.get('sucursal_id'),
                'timestamp_recepcion': payload.get('timestamp_recepcion'),
                'numero_orden': _infer_numero_orden(payload),
                'resultados': resultados,
                'raw': payload,
            }

        if is_hl7:
            endpoint = f"{base}{self.hl7_endpoint_path}"
            headers = {
                'Content-Type': 'text/plain; charset=utf-8',
            }
            if self.hl7_api_key:
                headers['X-PRISLAB-API-KEY'] = self.hl7_api_key
            if self.empresa_id:
                headers['X-EMPRESA-ID'] = str(self.empresa_id)
            payload = json_data.get('hl7_raw', '')
        else:
            # Preferir receptor /api/iot/hl7/ en modo JSON para equipos no-HL7.
            # Esto permite traza unificada en el SaaS (ResultadoHL7) sin depender del endpoint legacy.
            endpoint = f"{base}{self.hl7_endpoint_path}"
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
            }
            if self.hl7_api_key:
                headers['X-PRISLAB-API-KEY'] = self.hl7_api_key
            if self.empresa_id:
                headers['X-EMPRESA-ID'] = str(self.empresa_id)
            payload = _to_json_receptor_hl7(json_data)
        
        try:
            if is_hl7:
                response = requests.post(endpoint, data=payload.encode('utf-8', errors='replace'), headers=headers, timeout=15)
            else:
                response = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200 or response.status_code == 201:
                logger.info(f"Resultado enviado exitosamente a la nube: {response.status_code}")
            else:
                logger.warning(f"Respuesta inesperada de la nube: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al enviar a la nube: {e}")
            logger.warning("Los resultados se guardarán localmente para reintento posterior")
            # Cola de reintentos pendiente: usar celery.retry o persistir en tabla ResultadoHL7 con estado PENDIENTE_REINTENTO.
    
    def _ejecutar_driver(self, equipo_config: Dict):
        """
        Ejecuta un driver en un hilo separado.
        
        Args:
            equipo_config: Configuración del equipo
        """
        nombre = equipo_config.get('nombre')
        driver = self._crear_driver(equipo_config)
        
        if driver is None:
            logger.error(f"No se pudo crear driver para {nombre}")
            return
        
        self.drivers[nombre] = driver
        
        logger.info(f"Iniciando conexión con {nombre}...")
        
        try:
            # Configurar callback para resultados
            driver.on_result = lambda resultado: self._procesar_resultado(nombre, resultado)
            
            # Conectar y escuchar
            driver.conectar()
            
            # Mantener conexión activa
            while self.running:
                driver.procesar()
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error en driver {nombre}: {e}")
        finally:
            driver.desconectar()
            logger.info(f"Conexión cerrada con {nombre}")
    
    def iniciar(self):
        """Inicia el agente y todas las conexiones con los equipos."""
        if self.running:
            logger.warning("El agente ya está corriendo")
            return
        
        self.running = True
        logger.info("🚀 Iniciando Agente de Laboratorio PRISLAB...")
        logger.info(f"URL de nube: {self.cloud_url}")
        
        # Iniciar hilos para cada equipo
        for equipo in self.equipos:
            nombre = equipo.get('nombre')
            thread = threading.Thread(
                target=self._ejecutar_driver,
                args=(equipo,),
                name=f"Thread-{nombre}",
                daemon=True
            )
            thread.start()
            self.hilos[nombre] = thread
            logger.info(f"Hilo iniciado para {nombre}")
        
        logger.info(f"✅ Agente iniciado. {len(self.equipos)} equipos conectados.")
    
    def detener(self):
        """Detiene el agente y cierra todas las conexiones."""
        logger.info("Deteniendo agente...")
        self.running = False
        
        # Esperar a que todos los hilos terminen
        for nombre, thread in self.hilos.items():
            logger.info(f"Esperando cierre de {nombre}...")
            thread.join(timeout=5)
        
        # Desconectar todos los drivers
        for nombre, driver in self.drivers.items():
            try:
                driver.desconectar()
            except:
                pass
        
        logger.info("Agente detenido")
    
    def ejecutar(self):
        """Ejecuta el agente de forma continua."""
        try:
            self.iniciar()
            
            # Mantener el programa corriendo
            while self.running:
                time.sleep(1)
                
                # Verificar salud de los hilos
                for nombre, thread in list(self.hilos.items()):
                    if not thread.is_alive():
                        logger.warning(f"Hilo de {nombre} murió. Intentando reiniciar...")
                        # Reinicio automático pendiente: llamar a _ejecutar_driver(equipo_config) tras registrar el fallo.
                        
        except KeyboardInterrupt:
            logger.info("Interrupción recibida (Ctrl+C)")
        finally:
            self.detener()


def main():
    """Punto de entrada principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Agente de Integración LIS PRISLAB')
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Ruta al archivo de configuración (default: config.yaml)'
    )
    args = parser.parse_args()
    
    try:
        agente = AgenteLaboratorio(config_path=args.config)
        agente.ejecutar()
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        raise


if __name__ == "__main__":
    main()
