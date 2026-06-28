"""
INVENTARIO V8.0 — Paquete de vistas
Re-exporta todas las vistas para mantener compatibilidad con `from . import views` en urls.py.
"""
from .helpers import _get_empresa, _empresa_required

# Silo Laboratorio
from .lab import (
    dashboard_reactivos,
    lista_reactivos,
    crear_reactivo,
    editar_reactivo,
    eliminar_reactivo,
    lista_lotes,
    crear_lote,
    detalle_lote,
    liberar_lote_qc,
    baja_lote,
    lista_salidas_tecnicas,
    crear_salida_tecnica,
    lista_consumo,
    crear_consumo,
    editar_consumo,
    eliminar_consumo,
    trazabilidad_lote,
    api_stock_critico,
    api_lotes_por_reactivo,
)

# Silo Consultorio
from .consultorio import (
    dashboard_consultorio,
    lista_insumos_consultorio,
    crear_insumo_consultorio,
    editar_insumo_consultorio,
    lista_lotes_consultorio,
    crear_lote_consultorio,
    lista_salidas_consultorio,
    registrar_salida_consultorio,
)

# Silo Insumos Generales
from .generales import (
    dashboard_generales,
    lista_insumos_generales,
    crear_insumo_general,
    editar_insumo_general,
    lista_lotes_generales,
    crear_lote_general,
    lista_vales,
    crear_vale,
    detalle_vale,
    cancelar_vale,
)

# Motor de Compras
from .compras import (
    lista_ordenes_compra,
    crear_orden_compra,
    detalle_oc,
    lista_proveedores,
    crear_proveedor,
    api_articulos_criticos,
)

# Logística Inter-Sedes
from .traspasos import (
    lista_traspasos,
    crear_traspaso,
    detalle_traspaso,
    lista_notificaciones,
    resolver_notificacion,
    api_lotes_silo,
)

__all__ = [
    "_get_empresa",
    "_empresa_required",
    "dashboard_reactivos",
    "lista_reactivos",
    "crear_reactivo",
    "editar_reactivo",
    "eliminar_reactivo",
    "lista_lotes",
    "crear_lote",
    "detalle_lote",
    "liberar_lote_qc",
    "baja_lote",
    "lista_salidas_tecnicas",
    "crear_salida_tecnica",
    "lista_consumo",
    "crear_consumo",
    "editar_consumo",
    "eliminar_consumo",
    "trazabilidad_lote",
    "api_stock_critico",
    "api_lotes_por_reactivo",
    "dashboard_consultorio",
    "lista_insumos_consultorio",
    "crear_insumo_consultorio",
    "editar_insumo_consultorio",
    "lista_lotes_consultorio",
    "crear_lote_consultorio",
    "lista_salidas_consultorio",
    "registrar_salida_consultorio",
    "dashboard_generales",
    "lista_insumos_generales",
    "crear_insumo_general",
    "editar_insumo_general",
    "lista_lotes_generales",
    "crear_lote_general",
    "lista_vales",
    "crear_vale",
    "detalle_vale",
    "cancelar_vale",
    "lista_ordenes_compra",
    "crear_orden_compra",
    "detalle_oc",
    "lista_proveedores",
    "crear_proveedor",
    "api_articulos_criticos",
    "lista_traspasos",
    "crear_traspaso",
    "detalle_traspaso",
    "lista_notificaciones",
    "resolver_notificacion",
    "api_lotes_silo",
]
