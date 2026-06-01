"""
Compatibilidad: dominio PDV en core.services.ventas (v8.5 Fase 2).
Importar desde aquí o desde core.services.ventas según capa.
"""
from core.services.ventas.venta_farmacia_service import VentaFarmaciaService, ejecutar_venta_pdv

__all__ = ['VentaFarmaciaService', 'ejecutar_venta_pdv']
