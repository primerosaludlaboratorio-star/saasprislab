"""
Views package entrypoint for Farmacia.
Exports all views for backwards compatibility.
"""
from farmacia.views.movimientos import (
    FarmaciaAlertasView, KardexListView, crear_movimiento_manual, autorizar_movimiento,
    api_lotes_producto, reporte_valorizacion_inventario
)
from farmacia.views.compras import (
    registrar_compra, api_agregar_producto_compra, api_agregar_multi_lote, api_eliminar_producto_compra,
    entrada_express
)
from farmacia.views.caja import (
    corte_caja_farmacia, verificar_apertura_caja, abrir_caja
)
from farmacia.views.regulatorio import (
    validar_venta_antibiotico, reporte_cofepris, generar_etiquetas
)
from farmacia.views.devoluciones import (
    buscar_venta_para_devolucion, procesar_devolucion, dashboard_devoluciones, autorizar_devolucion,
    historial_devoluciones, buscar_venta_devolucion, procesar_devolucion_venta, detalle_devolucion
)
from farmacia.views.semaforo import dashboard_semaforo_caducidad, dashboard_stock_critico
