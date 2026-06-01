"""
URLs para el módulo de Laboratorio Clínico.
Sistema LIMS (Laboratory Information Management System) completo.
"""
from django.urls import path
from core import views
from core.views import impresion as impresion_views
from core.views import laboratorio_config as lims_views
from core.views import laboratorio_captura as captura_views
from core.views import laboratorio_reportes as reportes_views
from laboratorio import views_admin as admin_views
from laboratorio import views as lab_views
from laboratorio.views import cci_api as cci_api_views

app_name = 'laboratorio'

urlpatterns = [
    # ========== MONITOR DE PRODUCCIÓN (SEMAFORIZACIÓN KANBAN) ==========
    path('monitor/', views.monitor_produccion, name='monitor_produccion'),
    path('monitor/api/datos/', views.api_monitor_datos, name='api_monitor_datos'),
    path('monitor/api/avanzar-estado/', views.api_avanzar_estado, name='api_avanzar_estado'),
    
    # ========== RECEPCIÓN Y LISTA DE TRABAJO ==========
    path('recepcion/', views.recepcion_lab, name='recepcion'),
    path('lista-trabajo/', views.lista_trabajo_lab, name='lista_trabajo'),
    path('toma-muestra/', views.toma_muestra_index, name='toma_muestra'),
    path('control-calidad/', views.control_calidad, name='control_calidad'),

    # ========== FLUJO CUBÍCULO — TOMA DE MUESTRA CLÍNICO ==========
    path('toma-muestra/<int:orden_id>/preparacion/', views.preparacion_toma, name='preparacion_toma'),
    path('api/toma-muestra/<int:orden_id>/iniciar/', views.api_iniciar_toma, name='api_iniciar_toma'),
    path('api/toma-muestra/<int:orden_id>/finalizar/', views.api_finalizar_toma, name='api_finalizar_toma'),
    
    # ========== LIMS - CONFIGURACIÓN DE ESTUDIOS ==========
    path('lims/estudios/', lims_views.lista_pruebas, name='lista_pruebas'),
    path('lims/estudios/nuevo/', lims_views.configurar_prueba, name='configurar_prueba'),
    path('lims/estudios/<int:estudio_id>/editar/', lims_views.configurar_prueba, name='configurar_prueba_editar'),
    path('lims/estudios/<int:estudio_id>/duplicar/', lims_views.duplicar_prueba, name='duplicar_prueba'),
    path('lims/estudios/<int:estudio_id>/eliminar/', lims_views.eliminar_prueba, name='eliminar_prueba'),
    path('lims/parametros/<int:parametro_id>/rangos/', lims_views.configurar_rangos, name='configurar_rangos'),
    
    # ========== CAPTURA DE RESULTADOS ==========
    path('captura/<int:orden_id>/', captura_views.captura_resultados_industrial, name='captura_resultados'),
    path('notificacion-panico/<int:orden_id>/', captura_views.registrar_notificacion_panico, name='notificacion_panico'),
    
    # ========== IMPRESIÓN Y REPORTES ==========
    path('imprimir/<int:orden_id>/', reportes_views.imprimir_resultados, name='imprimir_resultados'),
    path('api/generar-reporte/<int:orden_id>/', reportes_views.api_generar_y_guardar_reporte, name='api_generar_reporte'),
    path('resultados/<int:orden_id>/pdf/', views.imprimir_resultados_pdf, name='resultados_pdf'),
    path('ticket/<int:orden_id>/', views.imprimir_ticket_lab, name='ticket'),
    path('ticket/<int:orden_id>/raw/', impresion_views.imprimir_ticket_raw, name='ticket_raw'),
    path('etiquetas/<int:orden_id>/', views.imprimir_etiquetas_lab, name='etiquetas'),
    path('etiquetas/<int:orden_id>/raw/', impresion_views.imprimir_etiquetas_raw, name='etiquetas_raw'),
    path('hoja-trabajo/pdf/', views.imprimir_hoja_trabajo_pdf, name='hoja_trabajo_pdf'),
    path('worklist/qr/<str:token>/', views.abrir_worklist_qr, name='worklist_qr'),
    
    # ========== APIS - BÚSQUEDA Y CONSULTA ==========
    path('api/buscar-estudios/', views.api_buscar_estudios, name='api_buscar_estudios'),
    path('api/medicos/', views.api_listar_medicos, name='api_medicos'),
    path('api/convenios/', views.api_listar_convenios, name='api_convenios'),
    path('api/convenios/<int:convenio_id>/precios/', views.api_precios_convenio, name='api_precios_convenio'),
    path('api/ordenes-recientes/', views.api_ordenes_recientes, name='api_ordenes_recientes'),
    path('api/preordenes-pendientes/', views.api_preordenes_pendientes, name='api_preordenes_pendientes'),
    path('api/cargar-preorden/', views.api_cargar_preorden, name='api_cargar_preorden'),
    
    # ========== APIS - GESTIÓN DE ÓRDENES ==========
    path('api/crear-orden/', views.crear_orden_servicio, name='api_crear_orden'),
    path('api/cobrar-orden/<int:orden_id>/', views.api_cobrar_orden, name='api_cobrar_orden'),
    path('api/cancelar-orden/<int:orden_id>/', views.cancelar_orden, name='api_cancelar_orden'),
    path('api/editar-paciente/<int:orden_id>/', views.editar_paciente_orden, name='api_editar_paciente'),
    
    # ========== APIS - CAPTURA Y VALIDACIÓN ==========
    path('api/guardar-resultados/<int:orden_id>/', views.api_guardar_resultados, name='api_guardar_resultados'),
    path('api/cci/lj-summary/', cci_api_views.api_cci_lj_summary, name='api_cci_lj_summary'),
    path('api/cci/lj-series/', cci_api_views.api_cci_lj_series, name='api_cci_lj_series'),
    path('api/toma-muestra/<int:orden_id>/', views.api_toma_muestra, name='api_toma_muestra'),
    path('api/validar-valor-critico/<int:detalle_id>/', views.validar_valor_critico, name='api_validar_critico'),
    path('api/rechazar-muestra/<int:detalle_id>/', views.rechazar_muestra, name='api_rechazar_muestra'),
    
    # ========== APIS - IA Y ESCANEO ==========
    path('api/escanear-receta/', views.escanear_receta_ia, name='api_escanear_receta'),
    path('api/escanear-identidad/', views.escanear_identidad_ia, name='api_escanear_identidad'),
    
    # ========== APIS - LIMS ==========
    path('api/estudios/<int:estudio_id>/parametros/', lims_views.api_parametros_estudio, name='api_parametros_estudio'),
    
    # ========== APIS - CREACIÓN RÁPIDA ==========
    path('api/crear-medico/', lab_views.crear_medico_ajax, name='api_crear_medico'),

    # ========== HISTORIAL DE PACIENTE (CONTEXTO LABORATORIO) ==========
    # Solo muestra visitas, órdenes y resultados — sin expediente clínico ni consultas.
    path('pacientes/', views.lista_pacientes_lab, name='lista_pacientes'),
    path('paciente/<int:paciente_id>/historial/', views.historial_lab_paciente, name='historial_paciente'),

    # ========== ADMINISTRACIÓN ==========
    path('admin/cargar-tarifas/', admin_views.vista_cargar_tarifas, name='vista_cargar_tarifas'),
    path('admin/cargar-tarifas-csv/', admin_views.cargar_tarifas_desde_csv, name='cargar_tarifas_csv'),
]
