"""CMMS V8.2/8.3 — URLs. Namespace: mantenimiento"""
from django.urls import path
from . import views
from . import views_metrologia as vm

app_name = "mantenimiento"

from django.views.generic import RedirectView as _RV

urlpatterns = [
    # Ruta raíz → redirige a lista de equipos (CMMS) por defecto
    path("",      _RV.as_view(url='equipos/', permanent=False),  name="mantenimiento_root"),

    # ── Wizard Director (Biblioteca Técnica) ──────────────────────────────
    path("wizard/",                           views.wizard_dashboard,          name="wizard_dashboard"),
    path("wizard/protocolo/nuevo/",           views.wizard_protocolo,          name="wizard_protocolo_nuevo"),
    path("wizard/protocolo/<int:pk>/",        views.wizard_protocolo,          name="wizard_protocolo_editar"),
    path("wizard/arbol/nuevo/",               views.wizard_arbol,              name="wizard_arbol_nuevo"),
    path("wizard/arbol/<int:pk>/",            views.wizard_arbol,              name="wizard_arbol_editar"),

    # ── Expedientes (Gemelo Digital — gestión) ────────────────────────────
    path("equipos/",                          views.lista_expedientes,         name="lista_expedientes"),
    path("equipos/nuevo/",                    views.crear_expediente,          name="crear_expediente"),
    path("equipos/<int:pk>/",                 views.detalle_expediente,        name="detalle_expediente"),

    # ── Panel Operativo (Químico) ─────────────────────────────────────────
    path("operativo/",                        views.lista_equipos_operativo,   name="lista_equipos_operativo"),
    path("checklist/<int:protocolo_pk>/<int:expediente_pk>/",
                                              views.ejecutar_checklist,        name="ejecutar_checklist"),
    path("checklist/bypass/<int:ejecucion_pk>/",
                                              views.bypass_checklist,          name="bypass_checklist"),

    # ── Diagnóstico ────────────────────────────────────────────────────────
    path("diagnostico/<int:expediente_pk>/",  views.diagnostico_inicio,        name="diagnostico_inicio"),
    path("diagnostico/arbol/<int:arbol_pk>/", views.diagnostico_nodo,          name="diagnostico_nodo_raiz"),
    path("diagnostico/arbol/<int:arbol_pk>/nodo/<int:nodo_pk>/",
                                              views.diagnostico_nodo,          name="diagnostico_nodo"),

    # ── Tickets ────────────────────────────────────────────────────────────
    path("tickets/",                          views.lista_tickets,             name="lista_tickets"),
    path("tickets/nuevo/",                    views.crear_ticket,              name="crear_ticket"),
    path("tickets/nuevo/<int:expediente_pk>/",views.crear_ticket,              name="crear_ticket_equipo"),
    path("tickets/<int:pk>/",                 views.detalle_ticket,            name="detalle_ticket"),

    # ── TCO / War Room ─────────────────────────────────────────────────────
    path("tco/",                              views.dashboard_tco,             name="dashboard_tco"),

    # ── QR Gemelo Digital (público, sin login) ────────────────────────────
    path("qr/<uuid:uid>/",                    views.qr_equipo_publico,         name="qr_equipo"),

    # ── APIs ───────────────────────────────────────────────────────────────
    path("api/checklist-bloqueado/",          views.api_checklist_bloqueado,   name="api_checklist_bloqueado"),
    path("api/stock-lote/",                   views.api_stock_lote_para_refaccion, name="api_stock_lote"),

    # ── Metrología V8.3 ────────────────────────────────────────────────────
    path("metrologia/",                        vm.lista_certificados,           name="lista_certificados"),
    path("metrologia/nuevo/",                  vm.subir_certificado,            name="subir_certificado"),
    path("metrologia/equipo/<int:expediente_pk>/", vm.subir_certificado,        name="subir_certificado_equipo"),
    path("metrologia/<int:pk>/eliminar/",      vm.eliminar_certificado,         name="eliminar_certificado"),

    # ── Sensores IoT V8.3 ──────────────────────────────────────────────────
    path("sensores/",                          vm.lista_sensores,               name="lista_sensores"),
    path("sensores/nuevo/",                    vm.crear_sensor,                 name="crear_sensor"),
    path("sensores/dashboard/",                vm.dashboard_sensores,           name="dashboard_sensores"),
    path("sensores/lectura/",                  vm.registrar_lectura_manual,     name="registrar_lectura"),
    path("api/iot/lectura/",                   vm.api_iot_lectura,              name="api_iot_lectura"),
]
