from django.urls import path, include
from django.views.generic import RedirectView
from core import views
from core.views import farmacia as core_farmacia_views
from farmacia.views import pdv as farmacia_pdv
from farmacia.views import inventario as farmacia_inventario
from farmacia.views import reportes as farmacia_reportes

urlpatterns = [
    # Corte diario operativo
    path('farmacia/corte-caja/', core_farmacia_views.corte_caja_dia, name='corte_caja_legacy'),
    path('finanzas/corte/', core_farmacia_views.corte_caja_dia, name='corte_dia'),

    # 1. MÓDULO FARMACIA (Punto de Venta)
    path('farmacia/', farmacia_inventario.dashboard_farmacia, name='dashboard_farmacia'),
    path('farmacia/pdv/', farmacia_pdv.pdv_farmacia, name='pdv_farmacia'),
    path('farmacia/pdv/buscar-fragmento/', farmacia_pdv.pdv_buscar_fragmento, name='pdv_buscar_fragmento'),
    path('farmacia/historial-ventas/', farmacia_reportes.lista_ventas_farmacia, name='lista_ventas_farmacia'),
    path('farmacia/dashboard/', farmacia_inventario.dashboard_farmacia, name='dashboard_farmacia_v2'),
    path('farmacia/libro-control/', farmacia_inventario.libro_control_antibioticos, name='libro_control'),
    path('farmacia/inventario/', views.farmacia_inventario_general, name='farmacia_inventario_general'),
    path('farmacia/devoluciones/', views.historial_devoluciones, name='historial_devoluciones'),
    path('farmacia/devoluciones/buscar/', views.buscar_venta_devolucion, name='buscar_venta_devolucion'),
    path('farmacia/devoluciones/procesar/', views.procesar_devolucion, name='procesar_devolucion'),
    path('farmacia/ventas/cancelar/<int:venta_id>/', views.cancelar_venta, name='cancelar_venta'),
    path('farmacia/ticket/<int:venta_id>/', views.imprimir_ticket, name='imprimir_ticket'),
    path('farmacia/carga-masiva-excel/', views.carga_masiva_excel, name='carga_masiva_excel'),
    path('farmacia/ajustes-inventario/', views.ajustes_inventario, name='ajustes_inventario'),
    path('farmacia/estadisticas-ventas/', views.estadisticas_ventas, name='estadisticas_ventas'),
    path('farmacia/api/kpis/', views.api_farmacia_kpis, name='api_farmacia_kpis'),
    path('farmacia/politicas-descuento/', farmacia_inventario.gestionar_politicas_descuento, name='politicas_descuento'),
    path('farmacia/ticket/<int:venta_id>/raw/', views.imprimir_ticket_raw, name='imprimir_ticket_venta_raw'),

    # Compatibilidad con enlaces legacy previos al namespace ERP.
    path('farmacia/kardex/', RedirectView.as_view(pattern_name='farmacia:kardex_list', permanent=False), name='farmacia_kardex_legacy'),
    path('farmacia/reporte/valorizacion/', RedirectView.as_view(pattern_name='farmacia:reporte_valorizacion', permanent=False), name='farmacia_valorizacion_legacy'),
    path('farmacia/semaforo-caducidad/', RedirectView.as_view(pattern_name='farmacia:dashboard_semaforo_caducidad', permanent=False), name='farmacia_semaforo_legacy'),
    path('farmacia/stock-critico/', RedirectView.as_view(pattern_name='farmacia:dashboard_stock_critico', permanent=False), name='farmacia_stock_legacy'),
    path('farmacia/antibioticos/reporte-cofepris/', RedirectView.as_view(pattern_name='farmacia:reporte_cofepris', permanent=False), name='farmacia_cofepris_legacy'),

    # 2. MÓDULO ALMACÉN (Entradas de Mercancía)
    path('farmacia/almacen/entradas/', farmacia_inventario.entrada_mercancia, name='entrada_mercancia'),
    path('farmacia/api/carga-masiva/', farmacia_inventario.carga_masiva_productos, name='api_carga_masiva_productos'),
    path('farmacia/compras/registrar/', farmacia_inventario.registrar_compra, name='registrar_compra'),
    path('farmacia/api/listas-precio/', farmacia_inventario.api_listas_precio_pdv, name='api_listas_precio_pdv'),
    path('farmacia/api/buscar-productos-compra/', farmacia_inventario.api_buscar_productos_compra, name='api_buscar_productos_compra'),
    path('farmacia/api/buscar-producto-pdv/', farmacia_pdv.api_buscar_producto_pdv, name='api_buscar_producto_pdv'),
    path('farmacia/api/lotes-producto/<int:producto_id>/', farmacia_pdv.api_lotes_producto, name='api_lotes_producto'),
    path('farmacia/api/validar-cupon/', farmacia_inventario.api_validar_cupon, name='api_validar_cupon'),
    path('farmacia/api/saldo-caja/', farmacia_inventario.api_saldo_caja, name='api_saldo_caja'),
    path('farmacia/api/validar-pin-neto/', farmacia_inventario.validar_pin_precio_neto, name='validar_pin_precio_neto'),
    path('farmacia/etiquetas/imprimir/', farmacia_inventario.imprimir_etiquetas, name='imprimir_etiquetas'),

    # 16. API FARMACIA (lectura para médicos)
    path('farmacia/api/buscar-productos-lectura/', views.api_buscar_productos_compra, name='api_buscar_productos_lectura'),

    # 20B. MÓDULO FARMACIA ERP (Kardex + Proveedores + Alertas)
    path('farmacia/erp/', include(('farmacia.urls', 'farmacia'), namespace='farmacia')),
]

