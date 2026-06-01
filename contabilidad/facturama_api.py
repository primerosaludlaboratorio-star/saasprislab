"""
Cliente API para Facturama (PAC)
Timbrado de CFDI 4.0 para México
Modo supervivencia: timeouts y manejo de errores para no bloquear ante APIs lentas/caídas.
"""

import hashlib
import logging
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import Timeout, ConnectionError as RequestsConnectionError
from django.conf import settings
from lxml import etree
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


class FacturamaAPI:
    """
    Cliente simplificado para timbrado con Facturama
    """
    
    def __init__(self):
        self.user = settings.FACTURAMA_USER
        self.password = settings.FACTURAMA_PASSWORD
        self.sandbox = settings.FACTURAMA_SANDBOX
        
        if self.sandbox:
            self.base_url = "https://apisandbox.facturama.mx"
        else:
            self.base_url = "https://api.facturama.mx"
        
        self.auth = HTTPBasicAuth(self.user, self.password)
    
    def timbrar_cfdi(self, factura):
        """
        Timbra una factura y retorna el XML timbrado.
        
        Blindaje H-002: Implementa idempotency key para evitar duplicados
        ante timeouts de red. La clave se genera a partir del folio único
        de la factura, garantizando que reintentos por latencia extrema
        no generen múltiples CFDIs ante el SAT.
        """
        cfdi_json = self._construir_cfdi_json(factura)

        url = f"{self.base_url}/3/cfdis"

        eid = factura.cfdi_empresa_scope_id()
        if not eid:
            logger.critical(
                'Facturama: factura %s sin empresa alcance (cliente/usuario); abortando timbrado',
                factura.id,
            )
            return {
                'success': False,
                'error': 'Configuración incompleta: la factura no tiene empresa asociada para timbrado.',
            }

        # Idempotency-Key determinista (sin timestamp): mismo CFDI lógico = misma clave ante reintentos/PAC.
        semilla = f'cfdi-empresa{eid}-fac{factura.id}'
        idempotency_key = hashlib.sha256(semilla.encode()).hexdigest()
        
        headers = {
            'Content-Type': 'application/json',
            'Idempotency-Key': idempotency_key,  # Blindaje contra timeouts y reintentos
        }
        
        logger.info("Facturama: timbrando factura %s con idempotency key %s...", 
                    factura.folio_interno, idempotency_key[:16] + "...")
        
        try:
            response = requests.post(
                url,
                auth=self.auth,
                headers=headers,
                json=cfdi_json,
                timeout=(5, 30)  # 5s connect, 30s read — modo supervivencia
            )
            
            if response.status_code == 201:
                data = response.json()
                uuid = data.get('Complement', {}).get('TaxStamp', {}).get('Uuid')
                logger.info("Facturama: timbrado exitoso UUID=%s", uuid)
                return {
                    'success': True,
                    'uuid': uuid,
                    'xml': data.get('Result'),
                    'fecha_timbrado': data.get('Date'),
                }
            else:
                logger.warning("Facturama: error HTTP %s - %s", 
                              response.status_code, response.text[:200])
                return {
                    'success': False,
                    'error': response.text,
                    'status_code': response.status_code
                }
        except Timeout:
            logger.warning("Facturama: timeout (servicio lento o no responde)")
            return {
                'success': False,
                'timeout': True,
                'error': 'El servicio de facturación no respondió a tiempo. Intente de nuevo en unos minutos.',
            }
        except RequestsConnectionError as e:
            logger.warning("Facturama: error de conexión — %s", e)
            return {
                'success': False,
                'error': 'No se pudo conectar con el servicio de facturación. Verifique su conexión o intente más tarde.'
            }
        except Exception as e:
            logger.exception("Facturama: error al timbrar")
            return {
                'success': False,
                'error': 'Error al timbrar la factura. Por favor intente más tarde o contacte a soporte.'
            }
    
    def _construir_cfdi_json(self, factura):
        """
        Construye el JSON en formato Facturama
        """
        tz_mexico = pytz.timezone('America/Mexico_City')
        fecha = factura.fecha_emision.astimezone(tz_mexico).strftime('%Y-%m-%dT%H:%M:%S')
        
        cfdi = {
            "Serie": factura.serie,
            "Folio": str(factura.folio),
            "Currency": "MXN",
            "ExpeditionPlace": factura.cliente.codigo_postal,
            "CfdiType": factura.tipo_comprobante,
            "PaymentForm": factura.forma_pago,
            "PaymentMethod": factura.metodo_pago,
            "Date": fecha,
            
            "Receiver": {
                "Rfc": factura.cliente.rfc,
                "Name": factura.cliente.razon_social,
                "CfdiUse": factura.cliente.uso_cfdi_default,
                "FiscalRegime": factura.cliente.regimen_fiscal,
                "TaxZipCode": factura.cliente.codigo_postal,
            },
            
            "Items": []
        }
        
        for concepto in factura.conceptos.all():
            item = {
                "ProductCode": concepto.clave_producto_servicio,
                "Description": concepto.descripcion,
                "Unit": "Servicio",
                "UnitCode": concepto.clave_unidad,
                "UnitPrice": float(concepto.valor_unitario),
                "Quantity": float(concepto.cantidad),
                "Subtotal": float(concepto.importe),
                "TaxObject": concepto.objeto_impuesto,
                "Taxes": []
            }
            
            for impuesto in concepto.impuestos.all():
                tax = {
                    "Total": float(impuesto.importe),
                    "Name": "IVA" if impuesto.impuesto == '002' else "ISR",
                    "Base": float(impuesto.base),
                    "Rate": float(impuesto.tasa_o_cuota),
                    "IsRetention": impuesto.tipo == 'RETENCION'
                }
                item["Taxes"].append(tax)
            
            cfdi["Items"].append(item)
        
        return cfdi
