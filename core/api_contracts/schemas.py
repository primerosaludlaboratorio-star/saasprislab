"""Esquemas Pydantic del contrato API v3 (errores y payloads PDV)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiErrorEnvelope(BaseModel):
    """Contrato estricto de error para el frontend (Cadenero)."""

    code: str = Field(..., description="Código estable de negocio o sistema")
    message: str = Field(..., description="Mensaje legible para el usuario")
    detail: dict[str, Any] = Field(default_factory=dict, description="Contexto estructurado opcional")
    request_id: str = Field(..., description="UUID de correlación de la petición")


class PdvProductoItem(BaseModel):
    """Ítem de catálogo devuelto por VentaFarmaciaService.buscar_productos_pdv."""

    model_config = {"extra": "ignore"}

    id: int
    nombre_comercial: str
    sustancia_activa: str = ""
    codigo_barras: str = ""
    precio_base: float
    precio_venta: float
    precio_compra: float
    costo_lote: float
    stock: int
    stock_total: int
    proxima_caducidad: str | None = None
    dias_restantes_fefo: int | None = None
    numero_lote_proximo: str | None = None
    iva_pct: float = 0.0
    es_controlado: bool
    es_antibiotico: bool
    requiere_receta: bool
    categoria: str = ""
    dias_restantes: int | None = None
    lote_id: int | None = None
    sin_stock_vigente: bool
    alerta_precio_bajo: bool


class BuscarProductosPdvResponse(BaseModel):
    """Respuesta 200 — búsqueda PDV tipada."""

    productos: list[PdvProductoItem]
    request_id: str


class PdvCobroV3Response(BaseModel):
    """Respuesta 200 — cobro PDV (payload del servicio + request_id)."""

    model_config = ConfigDict(extra="allow")

    request_id: str


class LimsCapturaV3Response(BaseModel):
    """Respuesta 200 — captura/validación LIMS (payload del servicio + request_id)."""

    model_config = ConfigDict(extra="allow")

    request_id: str
