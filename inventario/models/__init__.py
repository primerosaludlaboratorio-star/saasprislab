"""
INVENTARIO V8.0 — Paquete de modelos
Re-exporta todos los modelos para mantener compatibilidad con imports existentes.
"""
# Orden importa: los módulos posteriores referencian a los anteriores
from .base import UNIDAD_CHOICES, AREA_CHOICES, ProveedorCompras
from .lab import (
    CatalogoReactivoLab,
    ConsumoEstudioReactivo,
    LoteReactivoLab,
    SalidaAnaliticaLab,
    SalidaTecnicaLab,
)
from .consultorio import (
    CatalogoInsumoConsultorio,
    LoteInsumoConsultorio,
    SalidaConsumoConsultorio,
)
from .generales import (
    CatalogoInsumoGeneral,
    LoteInsumoGeneral,
    ValeRequisicion,
    LineaValeRequisicion,
)
from .compras import OrdenDeCompra, LineaOrdenCompra
from .logistica import TraspasoInventario, LineaTraspasoInventario, NotificacionDiscrepancia

__all__ = [
    "UNIDAD_CHOICES",
    "AREA_CHOICES",
    "ProveedorCompras",
    "CatalogoReactivoLab",
    "ConsumoEstudioReactivo",
    "LoteReactivoLab",
    "SalidaAnaliticaLab",
    "SalidaTecnicaLab",
    "CatalogoInsumoConsultorio",
    "LoteInsumoConsultorio",
    "SalidaConsumoConsultorio",
    "CatalogoInsumoGeneral",
    "LoteInsumoGeneral",
    "ValeRequisicion",
    "LineaValeRequisicion",
    "OrdenDeCompra",
    "LineaOrdenCompra",
    "TraspasoInventario",
    "LineaTraspasoInventario",
    "NotificacionDiscrepancia",
]
