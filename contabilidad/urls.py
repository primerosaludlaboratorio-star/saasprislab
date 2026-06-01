from django.urls import path
from . import views

app_name = 'contabilidad'

urlpatterns = [
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
    
    # API
    path('api/clientes/buscar/', views.api_buscar_cliente, name='api_buscar_cliente'),
]
