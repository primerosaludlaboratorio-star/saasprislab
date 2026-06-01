"""
INVENTARIO V8.2 — URLs de los 4 Silos + Motor de Compras
Namespace: inventario
"""
from django.urls import path
from . import views
from . import views_consultorio as vc
from . import views_generales  as vg
from . import views_compras    as vcp
from . import views_traspasos  as vt

app_name = "inventario"

from django.views.generic import RedirectView as _RV

urlpatterns = [

    # Ruta raíz → redirige al Silo 1 (Lab) por defecto
    path("",      _RV.as_view(url='lab/', permanent=False),     name="inventario_root"),

    # ═══════════════════════════════════════════════════════════════
    # SILO 1: LABORATORIO
    # ═══════════════════════════════════════════════════════════════

    # Dashboard
    path("lab/",                                        views.dashboard_reactivos,      name="dashboard_reactivos"),

    # Catálogo de Reactivos
    path("lab/catalogo/",                               views.lista_reactivos,          name="lista_reactivos"),
    path("lab/catalogo/nuevo/",                         views.crear_reactivo,           name="crear_reactivo"),
    path("lab/catalogo/<int:pk>/",                      views.editar_reactivo,          name="editar_reactivo"),
    path("lab/catalogo/<int:pk>/eliminar/",             views.eliminar_reactivo,        name="eliminar_reactivo"),

    # Lotes Lab (FEFO + Cuarentena)
    path("lab/lotes/",                                  views.lista_lotes,              name="lista_lotes"),
    path("lab/lotes/nuevo/",                            views.crear_lote,               name="crear_lote"),
    path("lab/lotes/<int:pk>/",                         views.detalle_lote,             name="detalle_lote"),
    path("lab/lotes/<int:pk>/liberar/",                 views.liberar_lote_qc,          name="liberar_lote_qc"),
    path("lab/lotes/<int:pk>/baja/",                    views.baja_lote,                name="baja_lote"),

    # Salidas Técnicas Lab
    path("lab/salidas-tecnicas/",                       views.lista_salidas_tecnicas,   name="lista_salidas_tecnicas"),
    path("lab/salidas-tecnicas/nueva/",                 views.crear_salida_tecnica,     name="crear_salida_tecnica"),

    # Configurador de Consumo por Estudio
    path("lab/consumo/",                                views.lista_consumo,            name="lista_consumo"),
    path("lab/consumo/nuevo/",                          views.crear_consumo,            name="crear_consumo"),
    path("lab/consumo/<int:pk>/editar/",                views.editar_consumo,           name="editar_consumo"),
    path("lab/consumo/<int:pk>/eliminar/",              views.eliminar_consumo,         name="eliminar_consumo"),

    # Trazabilidad forense
    path("lab/trazabilidad/",                           views.trazabilidad_lote,        name="trazabilidad_lote"),

    # APIs Lab
    path("lab/api/stock-critico/",                      views.api_stock_critico,        name="api_stock_critico"),
    path("lab/api/lotes/<int:reactivo_id>/",            views.api_lotes_por_reactivo,   name="api_lotes_por_reactivo"),

    # ═══════════════════════════════════════════════════════════════
    # SILO 2: CONSULTORIO
    # ═══════════════════════════════════════════════════════════════

    path("consultorio/",                                vc.dashboard_consultorio,           name="dashboard_consultorio"),
    path("consultorio/catalogo/",                       vc.lista_insumos_consultorio,       name="lista_insumos_consultorio"),
    path("consultorio/catalogo/nuevo/",                 vc.crear_insumo_consultorio,        name="crear_insumo_consultorio"),
    path("consultorio/catalogo/<int:pk>/editar/",       vc.editar_insumo_consultorio,       name="editar_insumo_consultorio"),
    path("consultorio/lotes/",                          vc.lista_lotes_consultorio,         name="lista_lotes_consultorio"),
    path("consultorio/lotes/nuevo/",                    vc.crear_lote_consultorio,          name="crear_lote_consultorio"),
    path("consultorio/salidas/",                        vc.lista_salidas_consultorio,       name="lista_salidas_consultorio"),
    path("consultorio/salidas/nueva/",                  vc.registrar_salida_consultorio,    name="registrar_salida_consultorio"),

    # ═══════════════════════════════════════════════════════════════
    # SILO 3: INSUMOS GENERALES + VALES
    # ═══════════════════════════════════════════════════════════════

    path("generales/",                                  vg.dashboard_generales,             name="dashboard_generales"),
    path("generales/catalogo/",                         vg.lista_insumos_generales,         name="lista_insumos_generales"),
    path("generales/catalogo/nuevo/",                   vg.crear_insumo_general,            name="crear_insumo_general"),
    path("generales/catalogo/<int:pk>/editar/",         vg.editar_insumo_general,           name="editar_insumo_general"),
    path("generales/lotes/",                            vg.lista_lotes_generales,           name="lista_lotes_generales"),
    path("generales/lotes/nuevo/",                      vg.crear_lote_general,              name="crear_lote_general"),
    path("generales/vales/",                            vg.lista_vales,                     name="lista_vales"),
    path("generales/vales/nuevo/",                      vg.crear_vale,                      name="crear_vale"),
    path("generales/vales/<int:pk>/",                   vg.detalle_vale,                    name="detalle_vale"),
    path("generales/vales/<int:pk>/cancelar/",          vg.cancelar_vale,                   name="cancelar_vale"),

    # ═══════════════════════════════════════════════════════════════
    # MOTOR DE COMPRAS
    # ═══════════════════════════════════════════════════════════════

    path("compras/",                                    vcp.lista_ordenes_compra,           name="lista_ordenes_compra"),
    path("compras/nueva/",                              vcp.crear_orden_compra,             name="crear_orden_compra"),
    path("compras/<int:pk>/",                           vcp.detalle_oc,                     name="detalle_oc"),
    path("compras/proveedores/",                        vcp.lista_proveedores,              name="lista_proveedores"),
    path("compras/proveedores/nuevo/",                  vcp.crear_proveedor,                name="crear_proveedor"),
    path("compras/api/criticos/",                       vcp.api_articulos_criticos,         name="api_articulos_criticos"),

    # ═══════════════════════════════════════════════════════════════
    # LOGÍSTICA INTER-SEDES — TRASPASOS V8.3
    # ═══════════════════════════════════════════════════════════════
    path("traspasos/",                                  vt.lista_traspasos,                 name="lista_traspasos"),
    path("traspasos/nuevo/",                            vt.crear_traspaso,                  name="crear_traspaso"),
    path("traspasos/<int:pk>/",                         vt.detalle_traspaso,                name="detalle_traspaso"),
    path("notificaciones/",                             vt.lista_notificaciones,            name="lista_notificaciones"),
    path("notificaciones/<int:pk>/resolver/",           vt.resolver_notificacion,           name="resolver_notificacion"),
    path("api/lotes-silo/",                             vt.api_lotes_silo,                  name="api_lotes_silo"),
]
