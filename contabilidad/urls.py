from django.urls import path
from . import views
from core.views import contabilidad as core_contab_views

app_name = 'contabilidad'

urlpatterns = [
    # Dashboard contable
    path('dashboard/', core_contab_views.dashboard_contabilidad, name='dashboard_contabilidad'),

    # Catálogo de cuentas
    path('catalogo-cuentas/', core_contab_views.catalogo_cuentas, name='catalogo_cuentas'),
    path('crear-cuenta/', core_contab_views.crear_cuenta, name='crear_cuenta'),

    # Pólizas
    path('polizas/', core_contab_views.lista_polizas, name='lista_polizas'),
    path('crear-poliza/', core_contab_views.crear_poliza, name='crear_poliza'),
    path('poliza/<int:poliza_id>/', core_contab_views.ver_poliza, name='ver_poliza'),
    path('poliza/<int:poliza_id>/autorizar/', core_contab_views.autorizar_poliza, name='autorizar_poliza'),

    # API contable
    path('api/cuentas/', core_contab_views.api_cuentas, name='api_cuentas'),

    # Clientes
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/crear/', views.crear_cliente, name='crear_cliente'),

    # Facturas
    path('facturas/', views.lista_facturas, name='lista_facturas'),
    path('facturas/crear/', views.crear_factura, name='crear_factura'),
    path('facturas/<int:factura_id>/', views.detalle_factura, name='detalle_factura'),
    path('facturas/<int:factura_id>/timbrar/', views.timbrar_factura, name='timbrar_factura'),
    path('facturas/<int:factura_id>/pdf/', views.descargar_pdf, name='descargar_pdf'),
    path('facturas/<int:factura_id>/xml/', views.descargar_xml, name='descargar_xml'),

    # API clientes
    path('api/clientes/buscar/', views.api_buscar_cliente, name='api_buscar_cliente'),
]
