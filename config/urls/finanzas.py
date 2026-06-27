from django.urls import path, include
from django.views.generic import RedirectView
from core import views
from core.views import finanzas as finanzas_views
from core.views import motor_financiero as motor_fin_views
from core.views import contabilidad_personal as contabilidad_personal_views
from farmacia.views import inventario as farmacia_inventario
from core.views.autofactura import (
    autofactura_publica,
    bandeja_cfdi,
    api_marcar_cfdi_timbrada,
)

urlpatterns = [
    # 6. MÓDULO FINANZAS
    path('finanzas/facturacion/', views.facturacion_40, name='facturacion_40'),
    path('finanzas/registro-gasto/', farmacia_inventario.registro_gasto, name='registro_gasto'),
    path('finanzas/api/registro-gasto/', farmacia_inventario.registro_gasto, name='api_registro_gasto'),
    path('finanzas/corte/', RedirectView.as_view(pattern_name='corte_caja_legacy', permanent=False), name='corte_dia'),

    # 6B. CUENTAS POR COBRAR Y CONVENIOS
    path('finanzas/cuentas-por-cobrar/', views.cuentas_por_cobrar_dashboard, name='cuentas_por_cobrar'),
    path('finanzas/api/pago-cxc/', views.api_registrar_pago_cxc, name='api_pago_cxc'),
    path('finanzas/api/crear-cxc/', views.api_crear_cxc, name='api_crear_cxc'),
    path('finanzas/convenios/', views.convenios_lista, name='convenios_lista'),
    path('finanzas/api/crear-convenio/', views.api_crear_convenio, name='api_crear_convenio'),
    path('finanzas/reporte-fiscal/', views.reporte_fiscal_mensual, name='reporte_fiscal'),

    # 20. ARQUITECTURA FINANCIERA SEGREGADA
    path('finanzas/lab/caja/', finanzas_views.LabCajaView.as_view(), name='caja_laboratorio'),
    path('finanzas/farmacia/caja/', finanzas_views.FarmaciaCajaView.as_view(), name='caja_farmacia'),
    path('finanzas/master/', finanzas_views.MasterDashboardView.as_view(), name='master_dashboard'),

    # 12. MÓDULO DE CONTABILIDAD
    # Todas las rutas viven en contabilidad/urls.py para evitar superposición
    path('contabilidad/', include(('contabilidad.urls', 'contabilidad'), namespace='contabilidad')),

    # Contabilidad Personal — exclusiva del Director
    path('contabilidad-personal/', contabilidad_personal_views.contabilidad_personal_dashboard, name='contabilidad_personal_dashboard'),
    path('contabilidad-personal/orden/<int:orden_id>/pagar/', contabilidad_personal_views.marcar_orden_pagada, name='marcar_orden_pagada'),
    path('contabilidad-personal/historial-pagos/', contabilidad_personal_views.historial_pagos_proveedores, name='historial_pagos_proveedores'),

    # 13. MÓDULO DE REPORTES FINANCIEROS
    path('reportes/ingresos-egresos/', views.reporte_ingresos_egresos, name='reporte_ingresos_egresos'),
    path('reportes/balance-general/', views.reporte_balance_general, name='reporte_balance_general'),
    path('reportes/flujo-caja/', views.reporte_flujo_caja, name='reporte_flujo_caja'),
    path('reportes/api/ventas-por-mes/', views.api_ventas_por_mes, name='api_ventas_por_mes'),
    path('reportes/ingresos-egresos/excel/', views.exportar_excel_ingresos_egresos, name='exportar_excel_ingresos_egresos'),
    path('reportes/flujo-caja/excel/', views.exportar_excel_flujo_caja, name='exportar_excel_flujo_caja'),
    path('reportes/balance-general/excel/', views.exportar_excel_balance, name='exportar_excel_balance'),
    path('reportes/reporte-caja/', motor_fin_views.genera_reporte_caja, name='genera_reporte_caja'),
    path('reportes/api/resumen-ejecutivo/', motor_fin_views.api_resumen_ejecutivo_pris, name='api_resumen_ejecutivo_pris'),

    # 12. MÓDULO: TRANSFERENCIAS ENTRE SUCURSALES
    path('transferencias/', views.lista_transferencias, name='lista_transferencias'),
    path('transferencias/crear/', views.crear_transferencia, name='crear_transferencia'),
    path('transferencias/<int:transferencia_id>/', views.ver_transferencia, name='ver_transferencia'),
    path('transferencias/<int:transferencia_id>/enviar/', views.enviar_transferencia, name='enviar_transferencia'),
    path('transferencias/<int:transferencia_id>/recibir/', views.recibir_transferencia, name='recibir_transferencia'),
    path('transferencias/api/buscar-productos/', views.api_buscar_productos_transferencia, name='api_buscar_productos_transferencia'),

    # CFDI 4.0 — Portal público de autofacturación
    path('facturacion/autofactura/', autofactura_publica, name='autofactura_publica'),
    path('facturacion/solicitudes/', bandeja_cfdi, name='bandeja_cfdi'),
    path('facturacion/cfdi/<int:factura_id>/timbrar/', api_marcar_cfdi_timbrada, name='api_marcar_cfdi_timbrada'),
]
