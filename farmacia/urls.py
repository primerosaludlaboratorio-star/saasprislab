"""
URLs del Módulo Farmacia - Sistema PRISLAB
Rutas para gestión completa de farmacia con Kardex, Compras y Corte de Caja
"""
from django.urls import path
from farmacia import views
from farmacia.views.semaforo import dashboard_semaforo_caducidad, dashboard_stock_critico

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
    path('api/lotes-producto/<int:producto_id>/', views.api_lotes_producto, name='api_lotes_producto'),
    
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
]
