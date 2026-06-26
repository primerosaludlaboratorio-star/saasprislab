"""
Shim de compatibilidad — la implementacion vive en:
  core.services.ventas.cobro_service      -> VentaFarmaciaService
  core.services.ventas.catalogo_service   -> CatalogoService, _int_or_none
  core.services.ventas.devolucion_service -> DevolucionService
"""
from core.services.ventas.cobro_service import VentaFarmaciaService, ejecutar_venta_pdv  # noqa: F401
from core.services.ventas.catalogo_service import CatalogoService, _int_or_none  # noqa: F401
from core.services.ventas.devolucion_service import DevolucionService  # noqa: F401

__all__ = ['VentaFarmaciaService', 'ejecutar_venta_pdv', 'CatalogoService', 'DevolucionService', '_int_or_none']
