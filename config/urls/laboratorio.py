from django.urls import path, include
from core import views
from core.views import impresion as impresion_views
from core.views.laboratorio import config_lims as lims_views
from core.views.laboratorio import captura as captura_views
from core.views.laboratorio import reportes as reportes_views
from laboratorio.views.hl7_receptor import receptor_hl7
from laboratorio.views.imprimir_zpl import (
    imprimir_etiqueta_zpl,
    imprimir_etiquetas_lote_zpl,
    kiosko_check_in_qr,
    kiosko_index,
)
from laboratorio.views.etiquetas import (
    imprimir_etiqueta_tubo,
    imprimir_etiquetas_lote,
    imprimir_etiqueta_qr,
    vista_previa_etiqueta,
)

urlpatterns = [
    # FASE 6: IoT HL7/ASTM — Receptor de resultados de analizadores
    path('api/iot/hl7/', receptor_hl7, name='hl7_receptor'),

    # FASE 7: ZPL — Impresión directa TCP/IP para impresoras Zebra
    path('api/lab/imprimir-zpl/<int:orden_id>/', imprimir_etiqueta_zpl, name='imprimir_zpl'),
    path('api/lab/imprimir-zpl/lote/', imprimir_etiquetas_lote_zpl, name='imprimir_zpl_lote'),

    # FASE 7: Kiosco auto-check-in por QR
    path('kiosko/', kiosko_index, name='kiosko_index'),
    path('kiosko/check-in/<str:qr_token>/', kiosko_check_in_qr, name='kiosko_check_in'),

    # Validación pública de resultados (QR)
    path('validar/resultado/<uuid:token>/', reportes_views.validar_resultado, name='validar_resultado'),

    # /laboratorio/captura/ sin ID — redirect al worklist
    path('laboratorio/captura/', views.registro_resultados_entrada, name='captura_sin_id'),

    # 5. MÓDULO LABORATORIO
    path('laboratorio/', views.recepcion_lab, name='laboratorio_dashboard'),
    path('laboratorio/dashboard/', views.dashboard_laboratorio, name='dashboard_laboratorio'),
    path('laboratorio/recepcion/', views.recepcion_lab, name='recepcion_lab'),
    path('laboratorio/consulta-ordenes/', views.consulta_ordenes, name='consulta_ordenes'),
    path('laboratorio/detalle-orden/<int:orden_id>/', views.detalle_orden_view, name='detalle_orden_view'),
    path('laboratorio/api/detalle-orden-completo/<int:orden_id>/', views.api_detalle_orden_completo, name='api_detalle_orden_completo'),
    path('laboratorio/lista-trabajo/', views.lista_trabajo_lab, name='lista_trabajo_lab'),
    path('laboratorio/registro-resultados/', views.registro_resultados_entrada, name='registro_resultados'),

    # 5.1 LIMS - Configuración de Estudios
    path('lims/estudios/', lims_views.lista_pruebas, name='lista_pruebas'),
    path('lims/estudios/nuevo/', lims_views.configurar_prueba, name='configurar_prueba'),
    path('lims/estudios/<int:estudio_id>/editar/', lims_views.configurar_prueba, name='editar_prueba_lims'),
    path('lims/estudios/<int:estudio_id>/duplicar/', lims_views.duplicar_prueba, name='duplicar_prueba'),
    path('lims/estudios/<int:estudio_id>/eliminar/', lims_views.eliminar_prueba, name='eliminar_prueba'),
    path('lims/parametros/', lims_views.lista_parametros, name='lista_parametros'),
    path('lims/parametros/nuevo/', lims_views.editar_parametro, name='nuevo_parametro'),
    path('lims/parametros/nuevo/estudio/<int:estudio_id>/', lims_views.editar_parametro, name='nuevo_parametro_estudio'),
    path('lims/parametros/<int:parametro_id>/editar/', lims_views.editar_parametro, name='editar_parametro'),
    path('lims/api/parametros/<int:parametro_id>/eliminar/', lims_views.api_soft_delete_parametro, name='api_soft_delete_parametro'),
    path('lims/api/parametros/<int:parametro_id>/rangos/', lims_views.api_rangos_parametro, name='api_rangos_parametro'),
    path('lims/api/parametros/<int:parametro_id>/rangos/<int:rango_id>/', lims_views.api_rango_detalle, name='api_rango_detalle'),
    path('lims/api/parametros/buscar/', lims_views.api_buscar_parametros, name='api_buscar_parametros'),
    path('lims/parametros/<int:parametro_id>/rangos/', lims_views.configurar_rangos, name='configurar_rangos'),
    path('lims/api/estudios/<int:estudio_id>/parametros/', lims_views.api_parametros_estudio, name='api_parametros_estudio'),

    path('laboratorio/hoja-trabajo/pdf/', views.imprimir_hoja_trabajo_pdf, name='imprimir_hoja_trabajo_pdf'),
    path('laboratorio/worklist/qr/<str:token>/', views.abrir_worklist_qr, name='abrir_worklist_qr'),
    path('laboratorio/control-calidad/', views.control_calidad, name='control_calidad'),
    path('laboratorio/toma-muestra/', views.toma_muestra_index, name='toma_muestra_index'),

    # Captura de Resultados
    path('laboratorio/captura/<int:orden_id>/', captura_views.captura_resultados_industrial, name='captura_resultados'),
    path('laboratorio/notificacion-panico/<int:orden_id>/', captura_views.registrar_notificacion_panico, name='registrar_notificacion_panico'),

    # Impresión de PDFs de Resultados
    path('laboratorio/imprimir/<int:orden_id>/', reportes_views.imprimir_resultados, name='imprimir_resultados'),
    path('laboratorio/resultados/<int:orden_id>/pdf/', views.imprimir_resultados_pdf, name='imprimir_resultados_pdf'),
    path('laboratorio/ticket/<int:orden_id>/', views.imprimir_ticket_lab, name='imprimir_ticket_lab'),
    path('laboratorio/ticket/<int:orden_id>/raw/', impresion_views.imprimir_ticket_raw, name='imprimir_ticket_raw'),
    path('laboratorio/etiquetas/<int:orden_id>/raw/', impresion_views.imprimir_etiquetas_raw, name='imprimir_etiquetas_raw'),

    # APIs de laboratorio
    path('laboratorio/api/buscar-estudios/', views.api_buscar_estudios, name='api_buscar_estudios'),
    path('laboratorio/api/medicos/', views.api_listar_medicos, name='api_listar_medicos'),
    path('laboratorio/api/convenios/', views.api_listar_convenios, name='api_listar_convenios'),
    path('laboratorio/api/convenios/<int:convenio_id>/precios/', views.api_precios_convenio, name='api_precios_convenio'),
    path('laboratorio/api/crear-orden/', views.crear_orden_servicio, name='crear_orden_servicio'),
    path('laboratorio/api/ordenes-recientes/', views.api_ordenes_recientes, name='api_ordenes_recientes'),
    path('laboratorio/api/preordenes-pendientes/', views.api_preordenes_pendientes, name='api_preordenes_pendientes'),
    path('laboratorio/api/cargar-preorden/', views.api_cargar_preorden, name='api_cargar_preorden'),
    path('laboratorio/api/cobrar-orden/<int:orden_id>/', views.api_cobrar_orden, name='api_cobrar_orden'),
    path('laboratorio/api/orden/<int:orden_id>/pagos/', views.api_historial_pagos, name='api_historial_pagos'),
    path('laboratorio/api/pago/<int:pago_id>/cancelar/', views.api_cancelar_pago, name='api_cancelar_pago'),
    path('laboratorio/api/orden/<int:orden_id>/datos/', views.api_datos_orden, name='api_datos_orden'),
    path('laboratorio/api/orden/<int:orden_id>/editar-datos/', views.api_editar_datos_orden, name='api_editar_datos_orden'),
    path('laboratorio/api/orden/<int:orden_id>/editar-estudios/', views.api_editar_estudios_orden, name='api_editar_estudios_orden'),
    path('laboratorio/api/guardar-resultados/<int:orden_id>/', views.api_guardar_resultados, name='api_guardar_resultados'),
    path('laboratorio/api/preview-formulas/<int:orden_id>/', views.api_preview_formulas_lims, name='api_preview_formulas_lims'),
    path('laboratorio/api/bulk-validar/', views.api_bulk_validar, name='api_bulk_validar'),
    path('laboratorio/api/bulk-imprimir/', views.api_bulk_imprimir, name='api_bulk_imprimir'),
    path('laboratorio/api/toma-muestra/<int:orden_id>/', views.api_toma_muestra, name='api_toma_muestra'),
    path('laboratorio/api/validar-pin/<int:orden_id>/', views.api_validar_pin, name='api_validar_pin'),
    path('laboratorio/api/estado/<int:orden_id>/', views.api_estado_orden, name='api_estado_orden'),
    path('laboratorio/reporte-tiempos/', views.reporte_tiempos_proceso, name='reporte_tiempos_proceso'),

    # ETIQUETAS TÉRMICAS
    path('laboratorio/etiqueta-termica/<int:orden_id>/', imprimir_etiqueta_tubo, name='imprimir_etiqueta_tubo'),
    path('laboratorio/etiquetas-lote/', imprimir_etiquetas_lote, name='imprimir_etiquetas_lote'),
    path('laboratorio/etiqueta-termica-qr/<int:orden_id>/', imprimir_etiqueta_qr, name='imprimir_etiqueta_qr'),
    path('laboratorio/etiqueta-previa/<int:orden_id>/', vista_previa_etiqueta, name='vista_previa_etiqueta'),

    # Trazabilidad Legal (Consentimientos)
    path('api/consentimiento/guardar/<int:orden_id>/', views.api_guardar_consentimiento, name='api_guardar_consentimiento'),
    path('api/consentimiento/verificar/<int:orden_id>/', views.api_verificar_consentimiento, name='api_verificar_consentimiento'),
    path('laboratorio/etiquetas/<int:orden_id>/', views.imprimir_etiquetas_lab, name='imprimir_etiquetas_lab'),
    path('laboratorio/api/cancelar-orden/<int:orden_id>/', views.cancelar_orden, name='cancelar_orden'),
    path('laboratorio/api/editar-paciente/<int:orden_id>/', views.editar_paciente_orden, name='editar_paciente_orden'),
    path('laboratorio/api/detalle-orden/<int:orden_id>/', views.api_detalle_orden, name='api_detalle_orden'),
    path('laboratorio/api/agregar-estudio/<int:orden_id>/', views.agregar_estudio_orden, name='agregar_estudio_orden'),
    path('laboratorio/api/eliminar-estudio/<int:orden_id>/<int:detalle_id>/', views.eliminar_estudio_orden, name='eliminar_estudio_orden'),
    path('laboratorio/api/validar-valor-critico/<int:detalle_id>/', views.validar_valor_critico, name='validar_valor_critico'),
    path('laboratorio/api/rechazar-muestra/<int:detalle_id>/', views.rechazar_muestra, name='rechazar_muestra'),
    path('laboratorio/api/escanear-receta/', views.escanear_receta_ia, name='escanear_receta_ia'),
    path('laboratorio/api/escanear-identidad/', views.escanear_identidad_ia, name='escanear_identidad_ia'),
    path('inventario/api/registrar-merma/', views.registrar_merma, name='registrar_merma'),

    # Entrega y logística
    path('laboratorio/dashboard-pendientes/', views.dashboard_pendientes, name='dashboard_pendientes'),
    path('laboratorio/entrega-resultados/', views.entrega_resultados, name='entrega_resultados'),
    path('laboratorio/reporte-tiempos-proceso/', views.reporte_tiempos_proceso, name='reporte_tiempos_proceso_v2'),
    path('logistica/rutas-recoleccion/', views.rutas_recoleccion, name='rutas_recoleccion'),
    path('laboratorio/entrega-resultados/<int:orden_id>/marcar-entregado/', views.marcar_entregado, name='marcar_entregado'),
    path('laboratorio/entrega-resultados/api/enviar-email/', views.api_enviar_email_masivo_resultados, name='api_enviar_email_masivo_resultados'),
    path('laboratorio/entrega-resultados/<int:orden_id>/whatsapp-enviado/', views.api_marcar_whatsapp_enviado, name='api_marcar_whatsapp_enviado'),
    path('laboratorio/resultados/publico/<str:token>/pdf/', views.resultados_publicos_pdf, name='resultados_publicos_pdf'),
    path('laboratorio/resultados/publico/<str:token>/', views.resultados_publicos, name='resultados_publicos'),

    # Maquila
    path('laboratorio/maquila/', views.maquila_envios, name='maquila_envios'),
    path('laboratorio/maquila/<int:orden_id>/enviar/', views.enviar_a_maquila, name='enviar_a_maquila'),

    # Auditoría de campo
    path('api/auditoria/campo/', views.api_auditoria_campo, name='api_auditoria_campo'),

    # includes con namespace
    path('laboratorio/', include(('laboratorio.urls', 'laboratorio'), namespace='laboratorio')),
    path('lims/', include('lims.urls')),
]
