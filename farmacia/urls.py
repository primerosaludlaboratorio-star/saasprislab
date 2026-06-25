"""
URLs del Módulo Farmacia - Sistema PRISLAB
Rutas para gestión completa de farmacia con Kardex, Compras y Corte de Caja
"""
from django.urls import path
from farmacia import views
from farmacia.views.semaforo import dashboard_semaforo_caducidad, dashboard_stock_critico

# Importar vistas de los nuevos módulos
from farmacia.views import pdv, inventario, devoluciones, reportes

app_name = 'farmacia'

urlpatterns = [
    # ======================================================================
    # DASHBOARD Y ALERTAS
    # ======================================================================
    path('alertas/', views.FarmaciaAlertasView.as_view(), name='dashboard_alertas'),
    
    # ======================================================================
    # KARDEX - MOVIMIENTOS DE INVENTARIO
    # ======================================================================
    path('kardex/', views.KardexListView.as_view(), name='kardex_list'),
    path('kardex/crear-movimiento/', views.crear_movimiento_manual, name='crear_movimiento'),
    path('kardex/autorizar/<int:movimiento_id>/', views.autorizar_movimiento, name='autorizar_movimiento'),
    
    # ======================================================================
    # ABASTECIMIENTO - REGISTRO DE COMPRAS
    # ======================================================================
    path('compras/registrar/', views.registrar_compra, name='registrar_compra'),
    path('api/agregar-producto-compra/', views.api_agregar_producto_compra, name='api_agregar_producto_compra'),
    path('api/agregar-multi-lote/', views.api_agregar_multi_lote, name='api_agregar_multi_lote'),
    path('api/eliminar-producto-compra/<int:index>/', views.api_eliminar_producto_compra, name='api_eliminar_producto_compra'),
    
    # ======================================================================
    # CORTE DE CAJA (ARQUEO CIEGO)
    # ======================================================================
    path('corte-caja/', views.corte_caja_farmacia, name='corte_caja'),
    
    # ======================================================================
    # ETIQUETAS CON CÓDIGO DE BARRAS
    # ======================================================================
    path('generar-etiquetas/', views.generar_etiquetas, name='generar_etiquetas'),
    
    # ======================================================================
    # REPORTES
    # ======================================================================
    path('reporte/valorizacion/', views.reporte_valorizacion_inventario, name='reporte_valorizacion'),
    
    # ======================================================================
    # API - UTILIDADES
    # ======================================================================
    path('api/lotes-producto/<int:producto_id>/', pdv.api_lotes_producto, name='api_lotes_producto'),
    
    # ======================================================================
    # SOPORTE OPERATIVO V5.0 (DEVOLUCIONES, APERTURA, ANTIBIÓTICOS, FAST RESTOCK)
    # ======================================================================
    # Devoluciones y Cancelaciones
    path('devoluciones/', views.dashboard_devoluciones, name='dashboard_devoluciones'),
    path('devoluciones/buscar/', views.buscar_venta_para_devolucion, name='buscar_venta_devolucion'),
    path('devoluciones/procesar/', views.procesar_devolucion, name='procesar_devolucion'),
    path('devoluciones/autorizar/<int:devolucion_id>/', views.autorizar_devolucion, name='autorizar_devolucion'),
    
    # Apertura de Caja
    path('caja/verificar/', views.verificar_apertura_caja, name='verificar_apertura_caja'),
    path('caja/abrir/', views.abrir_caja, name='abrir_caja'),
    
    # Control de Antibióticos (COFEPRIS)
    path('antibioticos/validar/', views.validar_venta_antibiotico, name='validar_antibiotico'),
    path('antibioticos/reporte-cofepris/', views.reporte_cofepris, name='reporte_cofepris'),
    
    # Entrada Express (Fast Restock)
    path('entrada-express/', views.entrada_express, name='entrada_express'),
    
    # ======================================================================
    # SEMÁFORO DE CADUCIDAD Y STOCK CRÍTICO
    # ======================================================================
    path('semaforo-caducidad/', dashboard_semaforo_caducidad, name='dashboard_semaforo_caducidad'),
    path('stock-critico/', dashboard_stock_critico, name='dashboard_stock_critico'),
    
    # ======================================================================
    # PDV - PUNTO DE VENTA (NUEVAS RUTAS)
    # ======================================================================
    path('pdv/', pdv.pdv_farmacia, name='pdv_farmacia'),
    path('api/buscar-producto-pdv/', pdv.api_buscar_producto_pdv, name='api_buscar_producto_pdv'),
    path('pdv/buscar-fragmento/', pdv.pdv_buscar_fragmento, name='pdv_buscar_fragmento'),
    # H1 RESUELTO: ruta duplicada eliminada — consolidada en línea 53 como 'api_lotes_producto'
    
    # ======================================================================
    # INVENTARIO (NUEVAS RUTAS)
    # ======================================================================
    path('entrada-mercancia/', inventario.entrada_mercancia, name='entrada_mercancia'),
    path('registrar-compra/', inventario.registrar_compra, name='registrar_compra_inv'),
    path('api/buscar-productos-compra/', inventario.api_buscar_productos_compra, name='api_buscar_productos_compra'),
    path('carga-masiva-productos/', inventario.carga_masiva_productos, name='carga_masiva_productos'),
    path('libro-control-antibioticos/', inventario.libro_control_antibioticos, name='libro_control_antibioticos'),
    path('dashboard-farmacia/', inventario.dashboard_farmacia, name='dashboard_farmacia'),
    path('gestionar-politicas-descuento/', inventario.gestionar_politicas_descuento, name='gestionar_politicas_descuento'),
    path('api/listas-precio-pdv/', inventario.api_listas_precio_pdv, name='api_listas_precio_pdv'),
    path('registro-gasto/', inventario.registro_gasto, name='registro_gasto'),
    path('api/saldo-caja/', inventario.api_saldo_caja, name='api_saldo_caja'),
    path('validar-pin-precio-neto/', inventario.validar_pin_precio_neto, name='validar_pin_precio_neto'),
    path('imprimir-etiquetas/', inventario.imprimir_etiquetas, name='imprimir_etiquetas'),
    path('api/validar-cupon/', inventario.api_validar_cupon, name='api_validar_cupon'),
    
    # ======================================================================
    # DEVOLUCIONES (NUEVAS RUTAS)
    # ======================================================================
    path('historial-devoluciones/', devoluciones.historial_devoluciones, name='historial_devoluciones'),
    path('buscar-venta-devolucion/', devoluciones.buscar_venta_devolucion, name='buscar_venta_devolucion'),
    path('procesar-devolucion-venta/', devoluciones.procesar_devolucion_venta, name='procesar_devolucion_venta'),
    path('detalle-devolucion/<int:devolucion_id>/', devoluciones.detalle_devolucion, name='detalle_devolucion'),
    
    # ======================================================================
    # REPORTES (NUEVAS RUTAS)
    # ======================================================================
    path('lista-ventas-farmacia/', reportes.lista_ventas_farmacia, name='lista_ventas_farmacia'),
    path('facturacion-40/', reportes.facturacion_40, name='facturacion_40'),
    path('reporte-ventas-fecha/', reportes.reporte_ventas_fecha, name='reporte_ventas_fecha'),
    path('reporte-productos-mas-vendidos/', reportes.reporte_productos_mas_vendidos, name='reporte_productos_mas_vendidos'),
    path('reporte-ventas-metodo-pago/', reportes.reporte_ventas_metodo_pago, name='reporte_ventas_metodo_pago'),
]
