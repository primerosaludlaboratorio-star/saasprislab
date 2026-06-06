from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from core import views
from core.views import impresion as impresion_views
from core.views import farmacia as farmacia_views
from core.views import medico as medico_views
from core.views import laboratorio_config as lims_views
from core.views import laboratorio_captura as captura_views
from core.views import laboratorio_reportes as reportes_views
from core.views import finanzas as finanzas_views
from core.views import motor_financiero as motor_fin_views
from core.views import push as push_views
from core.views import notificaciones as notif_views
from core.views import nomina as nomina_views
from core.views import crm as crm_views
from core.views import voice as voice_views
from core.views import comunicacion as chat_views
from core.views import pris_ia as ia_views
from core.views import prisci_webhook
from core.views.administracion_usuarios import gestionar_usuarios
from core.views.general import CustomLoginView, service_worker_view
from core.views import autenticacion_2fa as views_2fa
from core.views import sucursal_modo_inventario_lab as sucursal_inv_lab_views
from laboratorio.views.hl7_receptor import receptor_hl7
from core.api_contracts.ninja_api import api as api_contracts_v3
from laboratorio.views.imprimir_zpl import (
    imprimir_etiqueta_zpl,
    imprimir_etiquetas_lote_zpl,
    kiosko_check_in_qr,
    kiosko_index,
)
from core.views.paciente_detalle import ExpedienteClinicoView, exportar_historial_pdf
from laboratorio.views.etiquetas import (
    imprimir_etiqueta_tubo,
    imprimir_etiquetas_lote,
    imprimir_etiqueta_qr,
    vista_previa_etiqueta
)

# ── Páginas de error elegantes (activas cuando DEBUG=False) ──────────────────
from core.views.general import error_404, error_500, error_403  # noqa: E402

handler404 = error_404
handler500 = error_500
handler403 = error_403

urlpatterns = [
    # Favicon — redirige al icono SVG para evitar 404 del browser
    path('favicon.ico', RedirectView.as_view(url='/static/img/icon-192.svg', permanent=True)),

    # Legacy logo path — evita 404 en producción cuando el logo histórico ya no existe en MEDIA.
    path('media/logos/LOGO_PRISLAB.png', RedirectView.as_view(url='/static/img/icon-192.svg', permanent=True)),

    # Panel Administrativo de Django — Site personalizado con departamentos PRISLAB V5.4
    path('admin/', admin.site.urls),
    # Alias con reorganización departamental (mismo site, URLs registradas en ambos)
    # path('admin/', prislab_admin_site.urls),   # ← descomenta para migrar completamente

    # RUTA PRINCIPAL - Login personalizado (single name='login' for reverse/redirect)
    path('', CustomLoginView.as_view(), name='login_root'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),

    # FASE 4: Autenticación de dos factores (2FA/TOTP)
    path('auth/2fa/verificar/', views_2fa.verificar_2fa, name='verificar_2fa'),
    path('auth/2fa/configurar/', views_2fa.setup_2fa, name='setup_2fa'),
    path('auth/2fa/desactivar/', views_2fa.desactivar_2fa, name='desactivar_2fa'),

    # FASE 6: IoT HL7/ASTM — Receptor de resultados de analizadores de laboratorio
    path('api/iot/hl7/', receptor_hl7, name='hl7_receptor'),

    # FASE 3 (v8.5): Contratos API estrictos — Django Ninja + Cadenero (errores uniformes)
    path('api/v3/', api_contracts_v3.urls),

    # FASE 7: ZPL — Impresión directa TCP/IP para impresoras Zebra
    path('api/lab/imprimir-zpl/<int:orden_id>/', imprimir_etiqueta_zpl, name='imprimir_zpl'),
    path('api/lab/imprimir-zpl/lote/', imprimir_etiquetas_lote_zpl, name='imprimir_zpl_lote'),
    # FASE 7: Kiosco auto-check-in por QR
    path('kiosko/', kiosko_index, name='kiosko_index'),
    path('kiosko/check-in/<str:qr_token>/', kiosko_check_in_qr, name='kiosko_check_in'),

    # FASE 8: Corte de caja unificado (Lab + Farmacia)
    path('api/caja/corte-unificado/', __import__('farmacia.views.corte_caja_api', fromlist=['api_corte_caja_unificado']).api_corte_caja_unificado, name='corte_caja_unificado'),

    # FASE 9: Bienestar Staff NOM-035 (Caja Fuerte Interna)
    path('bienestar/', __import__('core.views.bienestar', fromlist=['dashboard_bienestar']).dashboard_bienestar, name='bienestar_dashboard'),
    path('bienestar/diario/', __import__('core.views.bienestar', fromlist=['diario_emocional']).diario_emocional, name='diario_emocional'),
    path('bienestar/nom035/', __import__('core.views.bienestar', fromlist=['evaluacion_nom035']).evaluacion_nom035, name='evaluacion_nom035'),
    path('bienestar/alertas-rrhh/', __import__('core.views.bienestar', fromlist=['alertas_rrhh']).alertas_rrhh, name='bienestar_alertas_rrhh'),

    # Home (redirige según rol después del login - SIN @login_required para evitar bucles)
    path('home/', views.home_view, name='home'),
    
    # Dashboard principal (redirige al Director Dashboard para admin/gerente/superuser)
    path('dashboard/', views.dashboard_director, name='dashboard'),
    
    # ========== VALIDACIÓN PÚBLICA DE RESULTADOS (QR) ==========
    path('validar/resultado/<uuid:token>/', reportes_views.validar_resultado, name='validar_resultado'),
    
    # ========== PRIS SENTINEL V4: WEB PUSH NOTIFICATIONS ==========
    path('api/push/vapid/', push_views.obtener_vapid_key, name='push_vapid_key'),
    path('api/push/suscribir/', push_views.suscribir_push, name='push_suscribir'),
    path('api/push/desuscribir/', push_views.desuscribir_push, name='push_desuscribir'),
    path('api/push/estado/', push_views.estado_suscripciones, name='push_estado'),
    path('api/push/test/', push_views.test_notificacion, name='push_test'),
    
    # ========== PRIS VOICE COMMANDER: CONTROL POR VOZ ==========
    path('api/voice/process/', voice_views.procesar_comando_api, name='voice_process'),
    path('api/voice/history/', voice_views.historial_comandos, name='voice_history'),
    path('api/voice/verify-auth/', voice_views.verificar_webauthn, name='voice_verify_auth'),
    path('voice/logs/', voice_views.dashboard_voice_logs, name='voice_logs_dashboard'),
    
    # ========== PRIS IA: ASISTENTE CONVERSACIONAL ==========
    path('ia/asistente/', ia_views.asistente_page, name='pris_ia_asistente'),
    path('ia/asistente/chat/', ia_views.asistente_chat, name='pris_ia_chat'),
    path('ia/asistente/reset/', ia_views.asistente_reset, name='pris_ia_reset'),
    path('api/prisci/webhook/', prisci_webhook.webhook, name='prisci_webhook'),
    path('api/prisci/webhook/verify/', prisci_webhook.verify, name='prisci_webhook_verify'),
    # AccionPRIS — Auditoría ISO 15189
    path('pris/api/acciones/pendientes/', ia_views.api_acciones_pendientes, name='pris_acciones_pendientes'),
    path('pris/api/accion/<int:accion_id>/confirmar/', ia_views.api_confirmar_accion, name='pris_confirmar_accion'),
    path('pris/api/accion/<int:accion_id>/rechazar/', ia_views.api_rechazar_accion, name='pris_rechazar_accion'),
    
    # ========== SISTEMA DE NOTIFICACIONES INTERNAS ==========
    path('notificaciones/', notif_views.lista_notificaciones, name='notificaciones_lista'),
    path('notificaciones/badge/', notif_views.api_notificaciones_badge, name='notificaciones_badge'),
    path('notificaciones/<int:notificacion_id>/leer/', notif_views.marcar_leida, name='notificacion_leer'),
    path('notificaciones/marcar-todas/', notif_views.marcar_todas_leidas, name='notificaciones_marcar_todas'),
    path('api/notificaciones/crear/', notif_views.api_crear_notificacion, name='api_crear_notificacion'),

    # ========== MÓDULO DE NÓMINA ==========
    path('nomina/', nomina_views.dashboard_nomina, name='nomina_dashboard'),
    path('nomina/periodos/', nomina_views.lista_periodos, name='nomina_lista_periodos'),
    path('nomina/periodos/nuevo/', nomina_views.crear_periodo, name='nomina_crear_periodo'),
    path('nomina/periodos/<int:pk>/', nomina_views.detalle_periodo, name='nomina_detalle_periodo'),
    path('nomina/periodos/<int:pk>/pagar/', nomina_views.marcar_periodo_pagado, name='nomina_marcar_pagado'),
    path('nomina/recibos/<int:pk>/editar/', nomina_views.editar_recibo, name='nomina_editar_recibo'),
    path('nomina/api/resumen/', nomina_views.api_resumen_nomina, name='nomina_api_resumen'),

    # ========== MÓDULO CRM ==========
    path('crm/', crm_views.dashboard_crm, name='crm_dashboard'),
    path('crm/prospectos/', crm_views.lista_prospectos, name='crm_lista_prospectos'),
    path('crm/prospectos/nuevo/', crm_views.crear_prospecto, name='crm_crear_prospecto'),
    path('crm/prospectos/<int:pk>/', crm_views.detalle_prospecto, name='crm_detalle_prospecto'),
    path('crm/prospectos/<int:pk>/seguimiento/', crm_views.agregar_seguimiento, name='crm_agregar_seguimiento'),
    path('crm/api/kanban/', crm_views.api_kanban_crm, name='crm_api_kanban'),

    # ========== PRIS SENTINEL SHIELD — Telemetria Frontend (Rev 128) ==========
    path('api/sentinel/shield-telemetry/', views.api_shield_telemetry, name='sentinel_shield_telemetry'),
    path('api/sentinel/reset/', views.api_sentinel_reset, name='sentinel_reset'),
    path('api/sentinel/diagnostico/', views.api_sentinel_diagnostico, name='sentinel_diagnostico'),
    
    # ========== MÓDULO DE SEGURIDAD (2FA, Sesiones, Auditoría) ==========
    path('seguridad/', include(('seguridad.urls', 'seguridad'), namespace='seguridad')),
    
    # ========== MÓDULO DE CONTABILIDAD (Facturación CFDI 4.0) ==========
    path('contabilidad/', include(('contabilidad.urls', 'contabilidad'), namespace='contabilidad')),

    # ── Redirects legacy (eliminan 404s detectados por Omnitex) ─────────────
    # /farmacia/corte-caja/ era referenciado en war_room_stress_test → redirige al POS
    path('farmacia/corte-caja/', RedirectView.as_view(url='/farmacia/pdv/?accion=corte', permanent=False), name='corte_caja_legacy'),
    # /laboratorio/captura/ sin ID → redirige al worklist con mensaje amigable
    path('laboratorio/captura/', views.registro_resultados_entrada, name='captura_sin_id'),

    # 1. MÓDULO FARMACIA (Punto de Venta)
    path('farmacia/', views.dashboard_farmacia, name='dashboard_farmacia'),  # Dashboard principal
    path('farmacia/pdv/', views.pdv_farmacia, name='pdv_farmacia'),
    path('farmacia/pdv/buscar-fragmento/', views.pdv_buscar_fragmento, name='pdv_buscar_fragmento'),
    path('farmacia/historial-ventas/', views.lista_ventas_farmacia, name='lista_ventas_farmacia'),
    path('farmacia/dashboard/', views.dashboard_farmacia, name='dashboard_farmacia_v2'),
    path('farmacia/libro-control/', views.libro_control_antibioticos, name='libro_control'),
    path('farmacia/devoluciones/', views.historial_devoluciones, name='historial_devoluciones'),
    path('farmacia/devoluciones/buscar/', views.buscar_venta_devolucion, name='buscar_venta_devolucion'),
    path('farmacia/devoluciones/procesar/', views.procesar_devolucion, name='procesar_devolucion'),
    path('farmacia/ventas/cancelar/<int:venta_id>/', views.cancelar_venta, name='cancelar_venta'),
    path('farmacia/politicas-descuento/', views.gestionar_politicas_descuento, name='politicas_descuento'),
    path('farmacia/ticket/<int:venta_id>/', views.imprimir_ticket, name='imprimir_ticket'),
    path('farmacia/ticket/<int:venta_id>/raw/', farmacia_views.imprimir_ticket_raw, name='imprimir_ticket_venta_raw'),
    
    # 2. MÓDULO ALMACÉN (Entradas de Mercancía)
    path('farmacia/almacen/entradas/', views.entrada_mercancia, name='entrada_mercancia'),
    path('farmacia/api/carga-masiva/', views.api_carga_masiva_productos, name='api_carga_masiva_productos'),
    path('farmacia/api/carga-masiva/excel/', views.carga_masiva_excel, name='carga_masiva_excel'),
    path('farmacia/compras/registrar/', views.registrar_compra, name='registrar_compra'),
    path('farmacia/almacen/ajustes/', views.ajustes_inventario, name='ajustes_inventario'),
    path('farmacia/inventario/', farmacia_views.inventario_general, name='farmacia_inventario_general'),
    path('farmacia/estadisticas/', views.estadisticas_ventas, name='estadisticas_ventas'),
    path('farmacia/api/kpis/', farmacia_views.api_farmacia_kpis, name='api_farmacia_kpis'),
    path('farmacia/api/listas-precio/', farmacia_views.api_listas_precio_pdv, name='api_listas_precio_pdv'),
    path('farmacia/api/buscar-productos-compra/', views.api_buscar_productos_compra, name='api_buscar_productos_compra'),
    path('farmacia/api/buscar-producto-pdv/', views.api_buscar_producto_pdv, name='api_buscar_producto_pdv'),
    path('farmacia/api/lotes-producto/<int:producto_id>/', views.api_lotes_producto, name='api_lotes_producto'),
    path('farmacia/api/validar-cupon/', views.api_validar_cupon, name='api_validar_cupon'),
    path('farmacia/api/saldo-caja/', views.api_saldo_caja, name='api_saldo_caja'),
    path('farmacia/api/validar-pin-neto/', farmacia_views.validar_pin_precio_neto, name='validar_pin_precio_neto'),
    path('farmacia/etiquetas/imprimir/', views.imprimir_etiquetas, name='imprimir_etiquetas'),

    # 3. MÓDULO MÉDICO (Consultorio)
    path('medico/', views.dashboard_medico, name='medico'),
    
    # 4. MANUAL OPERATIVO (Capacitación)
    path('manual/', views.manual_operativo, name='manual_operativo'),
    path('manual/pdf/', views.manual_operativo_pdf, name='manual_operativo_pdf'),
    
    # 5. MÓDULO LABORATORIO
    path('laboratorio/', views.recepcion_lab, name='laboratorio_dashboard'),  # Dashboard principal
    path('laboratorio/dashboard/', views.dashboard_laboratorio, name='dashboard_laboratorio'),
    path('laboratorio/recepcion/', views.recepcion_lab, name='recepcion_lab'),
    path('laboratorio/consulta-ordenes/', views.consulta_ordenes, name='consulta_ordenes'),
    path('laboratorio/detalle-orden/<int:orden_id>/', views.detalle_orden_view, name='detalle_orden_view'),
    path('laboratorio/api/detalle-orden-completo/<int:orden_id>/', views.api_detalle_orden_completo, name='api_detalle_orden_completo'),
    path('laboratorio/lista-trabajo/', views.lista_trabajo_lab, name='lista_trabajo_lab'),
    # Punto de entrada inteligente "Registro de Resultados" — carga el primer paciente pendiente
    path('laboratorio/registro-resultados/', views.registro_resultados_entrada, name='registro_resultados'),
    
    # 5.1 LIMS - Configuración de Estudios (SaaS Dinámico)
    path('lims/estudios/', lims_views.lista_pruebas, name='lista_pruebas'),
    path('lims/estudios/nuevo/', lims_views.configurar_prueba, name='configurar_prueba'),
    path('lims/estudios/<int:estudio_id>/editar/', lims_views.configurar_prueba, name='editar_prueba_lims'),
    path('lims/estudios/<int:estudio_id>/duplicar/', lims_views.duplicar_prueba, name='duplicar_prueba'),
    path('lims/estudios/<int:estudio_id>/eliminar/', lims_views.eliminar_prueba, name='eliminar_prueba'),
    # Parámetros: CRUD independiente + APIs AJAX
    path('lims/parametros/', lims_views.lista_parametros, name='lista_parametros'),
    path('lims/parametros/nuevo/', lims_views.editar_parametro, name='nuevo_parametro'),
    path('lims/parametros/nuevo/estudio/<int:estudio_id>/', lims_views.editar_parametro, name='nuevo_parametro_estudio'),
    path('lims/parametros/<int:parametro_id>/editar/', lims_views.editar_parametro, name='editar_parametro'),
    # Soft Delete vía API (requiere rol admin)
    path('lims/api/parametros/<int:parametro_id>/eliminar/', lims_views.api_soft_delete_parametro, name='api_soft_delete_parametro'),
    # Rangos de referencia (inmutabilidad/versionado)
    path('lims/api/parametros/<int:parametro_id>/rangos/', lims_views.api_rangos_parametro, name='api_rangos_parametro'),
    path('lims/api/parametros/<int:parametro_id>/rangos/<int:rango_id>/', lims_views.api_rango_detalle, name='api_rango_detalle'),
    # Autocompletar parámetros
    path('lims/api/parametros/buscar/', lims_views.api_buscar_parametros, name='api_buscar_parametros'),
    path('lims/parametros/<int:parametro_id>/rangos/', lims_views.configurar_rangos, name='configurar_rangos'),
    path('lims/api/estudios/<int:estudio_id>/parametros/', lims_views.api_parametros_estudio, name='api_parametros_estudio'),
    path('laboratorio/hoja-trabajo/pdf/', views.imprimir_hoja_trabajo_pdf, name='imprimir_hoja_trabajo_pdf'),
    path('laboratorio/worklist/qr/<str:token>/', views.abrir_worklist_qr, name='abrir_worklist_qr'),
    path('laboratorio/control-calidad/', views.control_calidad, name='control_calidad'),
    path('laboratorio/toma-muestra/', views.toma_muestra_index, name='toma_muestra_index'),
    # Captura de Resultados con IA
    path('laboratorio/captura/<int:orden_id>/', captura_views.captura_resultados_industrial, name='captura_resultados'),
    # Notificación de Valores Críticos (ISO 15189)
    path('laboratorio/notificacion-panico/<int:orden_id>/', captura_views.registrar_notificacion_panico, name='registrar_notificacion_panico'),
    # Impresión de PDF de Resultados
    path('laboratorio/imprimir/<int:orden_id>/', reportes_views.imprimir_resultados, name='imprimir_resultados'),
    path('laboratorio/resultados/<int:orden_id>/pdf/', views.imprimir_resultados_pdf, name='imprimir_resultados_pdf'),
    path('laboratorio/ticket/<int:orden_id>/', views.imprimir_ticket_lab, name='imprimir_ticket_lab'),
    path('laboratorio/ticket/<int:orden_id>/raw/', impresion_views.imprimir_ticket_raw, name='imprimir_ticket_raw'),
    path('laboratorio/etiquetas/<int:orden_id>/raw/', impresion_views.imprimir_etiquetas_raw, name='imprimir_etiquetas_raw'),
    path('laboratorio/api/buscar-estudios/', views.api_buscar_estudios, name='api_buscar_estudios'),
    path('laboratorio/api/medicos/', views.api_listar_medicos, name='api_listar_medicos'),
    path('laboratorio/api/convenios/', views.api_listar_convenios, name='api_listar_convenios'),
    path('laboratorio/api/convenios/<int:convenio_id>/precios/', views.api_precios_convenio, name='api_precios_convenio'),
    path('laboratorio/api/crear-orden/', views.crear_orden_servicio, name='crear_orden_servicio'),
    path('laboratorio/api/ordenes-recientes/', views.api_ordenes_recientes, name='api_ordenes_recientes'),
    path('laboratorio/api/preordenes-pendientes/', views.api_preordenes_pendientes, name='api_preordenes_pendientes'),
    path('laboratorio/api/cargar-preorden/', views.api_cargar_preorden, name='api_cargar_preorden'),
    path('laboratorio/api/cobrar-orden/<int:orden_id>/', views.api_cobrar_orden, name='api_cobrar_orden'),
    # ── Fase 2-B: Historial forense de pagos + cancelación ────────────────────
    path('laboratorio/api/orden/<int:orden_id>/pagos/', views.api_historial_pagos, name='api_historial_pagos'),
    path('laboratorio/api/pago/<int:pago_id>/cancelar/', views.api_cancelar_pago, name='api_cancelar_pago'),
    # ── Fase 4: Edición Dual ──────────────────────────────────────────────────
    path('laboratorio/api/orden/<int:orden_id>/datos/', views.api_datos_orden, name='api_datos_orden'),
    path('laboratorio/api/orden/<int:orden_id>/editar-datos/', views.api_editar_datos_orden, name='api_editar_datos_orden'),
    path('laboratorio/api/orden/<int:orden_id>/editar-estudios/', views.api_editar_estudios_orden, name='api_editar_estudios_orden'),
    # ─────────────────────────────────────────────────────────────────────────
    path('laboratorio/api/guardar-resultados/<int:orden_id>/', views.api_guardar_resultados, name='api_guardar_resultados'),
    path(
        'laboratorio/api/preview-formulas/<int:orden_id>/',
        views.api_preview_formulas_lims,
        name='api_preview_formulas_lims',
    ),
    path('laboratorio/api/bulk-validar/', views.api_bulk_validar, name='api_bulk_validar'),
    path('laboratorio/api/bulk-imprimir/', views.api_bulk_imprimir, name='api_bulk_imprimir'),
    path('laboratorio/api/toma-muestra/<int:orden_id>/', views.api_toma_muestra, name='api_toma_muestra'),
    path('laboratorio/api/validar-pin/<int:orden_id>/', views.api_validar_pin, name='api_validar_pin'),
    path('laboratorio/api/estado/<int:orden_id>/', views.api_estado_orden, name='api_estado_orden'),
    path('laboratorio/reporte-tiempos/', views.reporte_tiempos_proceso, name='reporte_tiempos_proceso'),
    
    # ========================================
    # ETIQUETAS TÉRMICAS (BLOQUE 7)
    # ========================================
    path('laboratorio/etiqueta-termica/<int:orden_id>/', imprimir_etiqueta_tubo, name='imprimir_etiqueta_tubo'),
    path('laboratorio/etiquetas-lote/', imprimir_etiquetas_lote, name='imprimir_etiquetas_lote'),
    path('laboratorio/etiqueta-termica-qr/<int:orden_id>/', imprimir_etiqueta_qr, name='imprimir_etiqueta_qr'),
    path('laboratorio/etiqueta-previa/<int:orden_id>/', vista_previa_etiqueta, name='vista_previa_etiqueta'),
    
    # API de Auditoría Nativa (Reglas de Varilla de Alta Resistencia)
    path('api/auditoria/campo/', views.api_auditoria_campo, name='api_auditoria_campo'),
    
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
    
    # 6. MÓDULO FINANZAS
    path('finanzas/facturacion/', views.facturacion_40, name='facturacion_40'),
    path('finanzas/registro-gasto/', views.registrar_gasto, name='registro_gasto'),
    path('finanzas/api/registro-gasto/', views.registrar_gasto, name='api_registro_gasto'),
    path('finanzas/corte/', views.corte_caja_dia, name='corte_dia'),
    
    # 6B. CUENTAS POR COBRAR Y CONVENIOS
    path('finanzas/cuentas-por-cobrar/', views.cuentas_por_cobrar_dashboard, name='cuentas_por_cobrar'),
    path('finanzas/api/pago-cxc/', views.api_registrar_pago_cxc, name='api_pago_cxc'),
    path('finanzas/api/crear-cxc/', views.api_crear_cxc, name='api_crear_cxc'),
    path('finanzas/convenios/', views.convenios_lista, name='convenios_lista'),
    path('finanzas/api/crear-convenio/', views.api_crear_convenio, name='api_crear_convenio'),
    path('finanzas/reporte-fiscal/', views.reporte_fiscal_mensual, name='reporte_fiscal'),
    
    # 7. MÓDULO CONFIGURACIÓN Y ADMINISTRACIÓN
    path('configuracion/', views.configuracion_dashboard, name='configuracion_dashboard'),
    path('configuracion/usuarios/', gestionar_usuarios, name='gestionar_usuarios'),
    # Feature Flags — Interruptores del Director
    path('configuracion/flags/', __import__('core.views.feature_flags_admin', fromlist=['panel_feature_flags']).panel_feature_flags, name='panel_feature_flags'),
    # ── Gobernanza IA (BYOK / consumo / modo) ──────────────────────────────
    path('api/ia/consumo/', __import__('core.views.configuracion', fromlist=['api_ia_consumo']).api_ia_consumo, name='api_ia_consumo'),
    path('api/ia/modo/', __import__('core.views.configuracion', fromlist=['api_cambiar_modo_ia']).api_cambiar_modo_ia, name='api_cambiar_modo_ia'),
    path('api/ia/byok/', __import__('core.views.configuracion', fromlist=['api_guardar_byok']).api_guardar_byok, name='api_guardar_byok'),
    path('configuracion/flags/<str:codigo>/toggle/', __import__('core.views.feature_flags_admin', fromlist=['api_toggle_flag']).api_toggle_flag, name='api_toggle_flag'),
    path('api/flags/estado/', __import__('core.views.feature_flags_admin', fromlist=['api_flags_estado']).api_flags_estado, name='api_flags_estado'),
    # Audio Legal — verificación de integridad de transcripciones
    path('api/audio/verificar-integridad/<int:registro_id>/', __import__('core.views.audio_legal', fromlist=['api_verificar_integridad_audio']).api_verificar_integridad_audio, name='api_verificar_integridad_audio'),
    path('api/audio/sellar/', __import__('core.views.audio_legal', fromlist=['api_sellar_audio']).api_sellar_audio, name='api_sellar_audio'),
    path('ia/panel/', views.ia_dashboard, name='ia_dashboard'),
    path('api/ia/chat/', views.api_ia_chat, name='api_ia_chat'),
    path('api/ia/consultar-negocios/', views.api_ia_consultar_negocios, name='api_ia_consultar_negocios'),
    path('api/ia/diagnostico/', views.api_ia_diagnostico, name='api_ia_diagnostico'),
    path('director/', views.dashboard_director, name='dashboard_director'),
    path(
        'director/sucursales/modo-inventario-lab/',
        sucursal_inv_lab_views.sucursales_modo_inventario_lab,
        name='sucursales_modo_inventario_lab',
    ),
    
    # 7A. MÓDULO IA AVANZADO (OCR, Voz, Gemini)
    path('ia/', include(('ia.urls', 'ia'), namespace='ia')),
    
    # 7B. MÓDULO CRECIMIENTO Y CONTROL GERENCIAL
    path('director/coach/', views.coach_ejecutivo, name='coach_ejecutivo'),
    path('director/coach/api/preguntar/', views.api_coach_preguntar, name='api_coach_preguntar'),
    path('director/buzon/', views.buzon_kanban, name='buzon_kanban'),
    path('reporte-friccion/', views.reporte_friccion, name='reporte_friccion'),
    path('api/pris-ayuda/', views.api_pris_ayuda, name='api_pris_ayuda'),
    path('director/calidad/', views.buzon_kanban, name='dashboard_calidad'),  # Alias para /director/calidad/
    path('director/biblioteca/', views.biblioteca_liderazgo, name='biblioteca_liderazgo'),
    path('director/biblioteca/agregar/', views.agregar_libro, name='agregar_libro'),
    path('director/biblioteca/api/cambiar-estado/<int:libro_id>/', views.api_cambiar_estado_libro, name='api_cambiar_estado_libro'),
    path('director/buzon/api/cambiar-estado/<int:queja_id>/', views.api_cambiar_estado_queja, name='api_cambiar_estado_queja'),
    path('director/buzon/api/obtener/', views.api_obtener_quejas, name='api_obtener_quejas'),
    path('tu-opinion/', views.tu_opinion, name='tu_opinion'),  # URL pública
    
    # 7C. SISTEMA DE AUTORIZACIONES EN TIEMPO REAL
    path('director/autorizaciones/', views.listar_autorizaciones_pendientes, name='listar_autorizaciones_pendientes'),
    path('director/autorizar/<uuid:uuid>/', views.autorizar_solicitud, name='autorizar_solicitud'),
    path('api/autorizaciones/crear/', views.crear_solicitud_autorizacion, name='crear_solicitud_autorizacion'),
    path('api/autorizaciones/<int:solicitud_id>/verificar/', views.verificar_estado_solicitud, name='verificar_estado_solicitud'),
    path('api/autorizaciones/<int:solicitud_id>/aprobar/', views.api_aprobar_solicitud, name='api_aprobar_solicitud'),
    path('api/autorizaciones/<int:solicitud_id>/rechazar/', views.api_rechazar_solicitud, name='api_rechazar_solicitud'),
    
    # 7D. SISTEMA DE REGISTRO DE INCIDENCIAS POR EXCEPCIÓN DE POLÍTICA
    path('director/auditoria/incidencias/', views.panel_auditoria_incidencias, name='panel_auditoria_incidencias'),
    path('api/incidencias/registrar/', views.registrar_incidencia, name='registrar_incidencia'),
    path('api/incidencias/<int:incidencia_id>/marcar-revisada/', views.marcar_incidencia_revisada, name='marcar_incidencia_revisada'),
    
    # 7E. SISTEMA DE RANKING DE DESEMPEÑO
    path('director/ranking/', views.ranking_desempeno, name='ranking_desempeno'),
    path('director/ranking/empleado/<int:empleado_id>/', views.detalle_empleado_ranking, name='detalle_empleado_ranking'),
    
    # 8. MÓDULO CATÁLOGOS
    path('catalogos/estudios/', views.lista_estudios, name='lista_estudios'),
    path('catalogos/medicos/', views.catalogo_medicos, name='catalogo_medicos'),
    path('catalogos/convenios/', views.catalogo_convenios, name='catalogo_convenios'),
    path('catalogos/convenios/<int:convenio_id>/precios/', views.convenio_precios, name='convenio_precios'),
    
    # 9. MÓDULO INVENTARIO
    path('inventario/', __import__('inventario.views', fromlist=['dashboard_reactivos']).dashboard_reactivos, name='inventario_general'),
    
    # 10. MÓDULO COTIZACIÓN
    path('cotizacion/', views.cotizacion_rapida, name='cotizacion_rapida'),
    path('cotizacion/api/buscar-paciente/', views.api_buscar_paciente_cotizacion, name='api_buscar_paciente_cotizacion'),
    path('cotizacion/api/crear-paciente/', views.api_crear_paciente_rapido, name='api_crear_paciente_rapido'),
    path('cotizacion/api/buscar-estudios/', views.api_buscar_estudios_cotizacion, name='api_buscar_estudios_cotizacion'),
    path('cotizacion/api/enviar-whatsapp/', views.api_enviar_whatsapp_cotizacion, name='api_enviar_whatsapp_cotizacion'),
    path('cotizacion/api/convertir-orden/', views.convertir_cotizacion_orden, name='convertir_cotizacion_orden'),
    
    # 11. MÓDULO MÉDICO
    path('medico/consulta/', views.consulta_medica, name='consulta_medica'),
    path('medico/consulta/<int:paciente_id>/', views.consulta_medica, name='consulta_medica'),
    path('medico/api/buscar-paciente/', views.buscar_paciente, name='buscar_paciente'),
    path('medico/api/verificar-existencia-farmacia/', views.verificar_existencia_farmacia, name='verificar_existencia_farmacia'),
    path('medico/receta/<int:receta_id>/', medico_views.ver_receta_medica, name='ver_receta_medica'),
    path('medico/receta/<int:receta_id>/pdf/', medico_views.generar_pdf_receta, name='generar_pdf_receta'),
    path('medico/api/verificar-qr-receta/', views.verificar_qr_receta, name='verificar_qr_receta'),
    
    # 11B. MÓDULO MÉDICO: ULTRASONIDO
    path('medico/ultrasonido/lista-trabajo/', medico_views.lista_trabajo_usg, name='lista_trabajo_usg'),
    path('medico/ultrasonido/captura/', medico_views.captura_reporte_usg, name='captura_reporte_usg'),
    path('medico/ultrasonido/captura/<int:paciente_id>/', medico_views.captura_reporte_usg, name='captura_reporte_usg_paciente'),
    path('medico/ultrasonido/<int:reporte_id>/pdf/', medico_views.descargar_pdf_ultrasonido, name='descargar_pdf_ultrasonido'),
    
    # 12. MÓDULO DE CONTABILIDAD
    path('contabilidad/', views.dashboard_contabilidad, name='dashboard_contabilidad'),
    path('contabilidad/catalogo-cuentas/', views.catalogo_cuentas, name='catalogo_cuentas'),
    path('contabilidad/crear-cuenta/', views.crear_cuenta, name='crear_cuenta'),
    path('contabilidad/polizas/', views.lista_polizas, name='lista_polizas'),
    path('contabilidad/crear-poliza/', views.crear_poliza, name='crear_poliza'),
    path('contabilidad/poliza/<int:poliza_id>/', views.ver_poliza, name='ver_poliza'),
    path('contabilidad/poliza/<int:poliza_id>/autorizar/', views.autorizar_poliza, name='autorizar_poliza'),
    path('contabilidad/api/cuentas/', views.api_cuentas, name='api_cuentas'),
    
    # 13. MÓDULO DE NÓMINA — rutas adicionales (cálculo y autorización)
    path('nomina/periodos/<int:periodo_id>/calcular/', nomina_views.calcular_nomina, name='calcular_nomina'),
    path('nomina/recibos/<int:nomina_id>/autorizar/', nomina_views.autorizar_nomina, name='autorizar_nomina'),
    
    # 14. MÓDULO DE ASISTENCIA
    path('asistencia/', views.dashboard_asistencia, name='dashboard_asistencia'),
    path('asistencia/registros/', views.registro_asistencia, name='registro_asistencia'),
    path('asistencia/registrar/', views.registrar_entrada_salida, name='registrar_entrada_salida'),
    path('asistencia/horarios/', views.horarios_trabajo, name='horarios_trabajo'),
    path('asistencia/crear-horario/', views.crear_horario, name='crear_horario'),
    path('asistencia/incidencias/', views.incidencias_asistencia, name='incidencias_asistencia'),
    path('asistencia/crear-incidencia/', views.crear_incidencia, name='crear_incidencia'),
    path('asistencia/incidencia/<int:incidencia_id>/autorizar/', views.autorizar_incidencia, name='autorizar_incidencia'),
    
    # 15. MÓDULO DE ENTREGA DE RESULTADOS
    path('laboratorio/dashboard-pendientes/', views.dashboard_pendientes, name='dashboard_pendientes'),
    path('laboratorio/entrega-resultados/', views.entrega_resultados, name='entrega_resultados'),
    path('laboratorio/reporte-tiempos-proceso/', views.reporte_tiempos_proceso, name='reporte_tiempos_proceso_v2'),
    
    # 15B. MÓDULO DE LOGÍSTICA Y RUTAS
    path('logistica/rutas-recoleccion/', views.rutas_recoleccion, name='rutas_recoleccion'),
    path('laboratorio/entrega-resultados/<int:orden_id>/marcar-entregado/', views.marcar_entregado, name='marcar_entregado'),
    path('laboratorio/entrega-resultados/api/enviar-email/', views.api_enviar_email_masivo_resultados, name='api_enviar_email_masivo_resultados'),
    path('laboratorio/entrega-resultados/<int:orden_id>/whatsapp-enviado/', views.api_marcar_whatsapp_enviado, name='api_marcar_whatsapp_enviado'),
    path('laboratorio/resultados/publico/<str:token>/pdf/', views.resultados_publicos_pdf, name='resultados_publicos_pdf'),
    path('laboratorio/resultados/publico/<str:token>/', views.resultados_publicos, name='resultados_publicos'),
    
    # 16. MÓDULO DE MAQUILA
    path('laboratorio/maquila/', views.maquila_envios, name='maquila_envios'),
    path('laboratorio/maquila/<int:orden_id>/enviar/', views.enviar_a_maquila, name='enviar_a_maquila'),
    
    # 17. MÓDULO DE CAPACITACIÓN
    path('capacitacion/personal/', views.capacitacion_personal, name='capacitacion_personal'),
    path('capacitacion/ejecutiva/', views.capacitacion_ejecutiva, name='capacitacion_ejecutiva'),
    
    # 18. MÓDULO DE BIENESTAR
    path('bienestar/', include(('bienestar.urls', 'bienestar'), namespace='bienestar')),
    path('bienestar/pris/chat/', views.chat_bienestar, name='chat_bienestar'),
    path('bienestar/pris/chat/enviar/', views.enviar_mensaje_bienestar, name='enviar_mensaje_bienestar'),
    path('bienestar/pris/alertas/', views.alertas_bienestar_director, name='alertas_bienestar_director'),
    path('bienestar/pris/alertas/<int:alerta_id>/vista/', views.marcar_alerta_vista, name='marcar_alerta_vista'),

    # 19. MÓDULO DE CAPACITACIÓN CON RAG — Biblioteca de Entrenamiento PRIS-IA
    path('capacitacion/rag/', views.dashboard_capacitacion, name='dashboard_capacitacion'),
    path('capacitacion/rag/subir/', views.subir_documento_capacitacion, name='subir_documento_capacitacion'),
    path('capacitacion/rag/consultar/', views.consultar_pris_rag, name='consultar_pris_rag'),
    path('capacitacion/rag/worklist/', views.consultar_pris_worklist, name='consultar_pris_worklist'),
    path('capacitacion/rag/reprocesar/<uuid:documento_id>/', views.reprocesar_documento, name='reprocesar_documento_rag'),
    path('capacitacion/rag/estado/<uuid:documento_id>/', views.estado_documento_rag, name='estado_documento_rag'),
    path('capacitacion/rag/eliminar/<uuid:documento_id>/', views.eliminar_documento, name='eliminar_documento_rag'),
    path('capacitacion/rag/tip/', views.obtener_tip_dia, name='obtener_tip_dia'),
    
    # 20. ARQUITECTURA FINANCIERA SEGREGADA (PRISLAB v5.0)
    path('finanzas/lab/caja/', finanzas_views.LabCajaView.as_view(), name='caja_laboratorio'),
    path('finanzas/farmacia/caja/', finanzas_views.FarmaciaCajaView.as_view(), name='caja_farmacia'),
    path('finanzas/master/', finanzas_views.MasterDashboardView.as_view(), name='master_dashboard'),
    
    # 20B. MÓDULO FARMACIA ERP (Kardex + Proveedores + Alertas)
    path('farmacia/erp/', include(('farmacia.urls', 'farmacia'), namespace='farmacia')),
    
    # 21. PRIS - SISTEMA NERVIOSO CENTRAL
    path('pris/api/dictado-inventario/', views.api_dictado_inventario, name='api_dictado_inventario'),
    path('pris/api/dictado-resultado/', views.api_dictado_resultado, name='api_dictado_resultado'),
    path('pris/api/ocr-documento/', views.api_ocr_documento, name='api_ocr_documento'),
    path('pris/api/crear-archivo-raw/', views.api_crear_archivo_raw, name='api_crear_archivo_raw'),
    path('pris/api/consulta-voz/', views.api_consulta_voz, name='api_consulta_voz'),
    path('pris/api/generar-hoja-trabajo/', views.api_generar_hoja_trabajo, name='api_generar_hoja_trabajo'),
    path('pris/api/crear-alerta-clinica/', views.api_crear_alerta_clinica, name='api_crear_alerta_clinica'),
    path('pris/acciones/', views.lista_acciones_pris, name='lista_acciones_pris'),
    path('pris/acciones/<int:accion_id>/validar/', views.validar_accion_pris, name='validar_accion_pris'),
    # ── Checklist Autónomo por Escucha Activa (NLP en tiempo real) ────────
    path('pris/api/checklist-nlp/',
         __import__('core.views.pris_checklist', fromlist=['api_detectar_intents_checklist']).api_detectar_intents_checklist,
         name='pris_checklist_nlp'),
    path('pris/api/checklist-guia/',
         __import__('core.views.pris_checklist', fromlist=['api_guia_preguntas']).api_guia_preguntas,
         name='pris_checklist_guia'),
    
    # 11. MÓDULO: HISTORIAL DE RESULTADOS CON GRÁFICAS (con namespace 'core')
    path('', include('core.urls', namespace='core')),
    
    # 12. MÓDULO: TRANSFERENCIAS ENTRE SUCURSALES
    path('transferencias/', views.lista_transferencias, name='lista_transferencias'),
    path('transferencias/crear/', views.crear_transferencia, name='crear_transferencia'),
    path('transferencias/<int:transferencia_id>/', views.ver_transferencia, name='ver_transferencia'),
    path('transferencias/<int:transferencia_id>/enviar/', views.enviar_transferencia, name='enviar_transferencia'),
    path('transferencias/<int:transferencia_id>/recibir/', views.recibir_transferencia, name='recibir_transferencia'),
    path('transferencias/api/buscar-productos/', views.api_buscar_productos_transferencia, name='api_buscar_productos_transferencia'),
    
    # 13. MÓDULO: REPORTES FINANCIEROS DETALLADOS
    path('reportes/ingresos-egresos/', views.reporte_ingresos_egresos, name='reporte_ingresos_egresos'),
    path('reportes/balance-general/', views.reporte_balance_general, name='reporte_balance_general'),
    path('reportes/flujo-caja/', views.reporte_flujo_caja, name='reporte_flujo_caja'),
    path('reportes/api/ventas-por-mes/', views.api_ventas_por_mes, name='api_ventas_por_mes'),
    path('reportes/ingresos-egresos/excel/', views.exportar_excel_ingresos_egresos, name='exportar_excel_ingresos_egresos'),
    path('reportes/flujo-caja/excel/', views.exportar_excel_flujo_caja, name='exportar_excel_flujo_caja'),
    path('reportes/balance-general/excel/', views.exportar_excel_balance, name='exportar_excel_balance'),
    path('reportes/reporte-caja/', motor_fin_views.genera_reporte_caja, name='genera_reporte_caja'),

    # 14. MÓDULO: CRM INTEGRADO — clientes (convertidos) y oportunidades
    path('crm/clientes/', views.lista_clientes_crm, name='lista_clientes_crm'),
    path('crm/clientes/crear/', views.crear_cliente_crm, name='crear_cliente_crm'),
    path('crm/clientes/<int:cliente_id>/', views.ver_cliente_crm, name='ver_cliente_crm'),
    path('crm/clientes/<int:cliente_id>/interaccion/', views.crear_interaccion_crm, name='crear_interaccion_crm'),
    path('crm/oportunidades/', views.lista_oportunidades_crm, name='lista_oportunidades_crm'),
    path('crm/oportunidades/crear/', views.crear_oportunidad_crm, name='crear_oportunidad_crm'),
    path('crm/oportunidades/<int:oportunidad_id>/', views.ver_oportunidad_crm, name='ver_oportunidad_crm'),
    path('crm/oportunidades/<int:oportunidad_id>/cerrar/', views.cerrar_oportunidad, name='cerrar_oportunidad'),
    
    # 15. MÓDULO: ANALYTICS Y REPORTES CENTRALIZADOS
    path('analytics/', views.dashboard_analytics, name='dashboard_analytics'),
    path('analytics/trazabilidad/', views.reporte_trazabilidad, name='reporte_trazabilidad'),
    path('analytics/api/metricas-tiempo-real/', views.api_metricas_tiempo_real, name='api_metricas_tiempo_real'),

    # 16. DASHBOARD UNIFICADO (KPIs de todos los módulos)
    path('dashboard-unificado/', views.dashboard_unificado, name='dashboard_unificado'),
    path('dashboard-unificado/api/kpis-tiempo-real/', views.api_kpis_tiempo_real, name='api_kpis_tiempo_real'),
    
    # 17. SISTEMA DE NOTIFICACIONES — rutas adicionales
    path('notificaciones/<int:notificacion_id>/marcar-leida/', notif_views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    path('notificaciones/marcar-todas-leidas/', notif_views.marcar_todas_leidas, name='marcar_todas_leidas'),
    path('notificaciones/api/no-leidas/', notif_views.api_notificaciones_no_leidas, name='api_notificaciones_no_leidas'),
    path('notificaciones/configurar/', notif_views.configurar_notificaciones, name='configurar_notificaciones'),
    path('notificaciones/ejecutar-verificaciones/', notif_views.ejecutar_verificaciones, name='ejecutar_verificaciones'),
    
    # API PACIENTES (compartida entre módulos)
    path('api/pacientes/guardar/', views.api_guardar_paciente, name='api_guardar_paciente'),
    path('api/pacientes/buscar/', views.api_buscar_pacientes, name='api_buscar_pacientes'),
    
    # ========== OMNISEARCH (BUSCADOR GLOBAL NAVBAR) ==========
    path('api/omnisearch/', views.api_omnisearch, name='api_omnisearch'),
    
    # EXPEDIENTE CLÍNICO UNIFICADO (BLOQUE 2)
    path('pacientes/<int:pk>/expediente/', ExpedienteClinicoView.as_view(), name='expediente_clinico'),
    path('pacientes/<int:paciente_id>/exportar-historial/', exportar_historial_pdf, name='exportar_historial_pdf'),
    
    # 12. MÓDULO RECURSOS HUMANOS
    path('rh/evaluaciones/', views.lista_evaluaciones_39a, name='lista_evaluaciones_39a'),
    path('rh/evaluaciones/crear/', views.crear_evaluacion_39a, name='crear_evaluacion_39a'),
    path('rh/evaluaciones/crear/<int:empleado_id>/', views.crear_evaluacion_39a, name='crear_evaluacion_39a'),
    path('rh/evaluaciones/<int:evaluacion_id>/', views.ver_evaluacion_39a, name='ver_evaluacion_39a'),
    path('rh/evaluaciones/<int:evaluacion_id>/pdf/', views.descargar_pdf_evaluacion_39a, name='descargar_pdf_evaluacion_39a'),
    
    # 12B. MÓDULO EVALUACIÓN DE DESEMPEÑO Y TALENTO (Buk-Inspired)
    path('rh/desempeno/nueva/', views.nueva_evaluacion_desempeno, name='nueva_evaluacion_desempeno'),
    path('rh/desempeno/nueva/<int:empleado_id>/', views.nueva_evaluacion_desempeno, name='nueva_evaluacion_desempeno'),
    path('rh/desempeno/<int:evaluacion_id>/', views.ver_evaluacion_desempeno, name='ver_evaluacion_desempeno'),
    path('rh/mis-resultados/', views.mis_resultados, name='mis_resultados'),
    path('rh/matriz-talento/', views.matriz_talento, name='matriz_talento'),
    
    # 13. MÓDULO CEREBRO/IA
    path('cerebro/chat/', views.chat_experto, name='chat_experto'),
    path('api/cerebro/preguntar/', views.api_cerebro_preguntar, name='api_cerebro_preguntar'),
    
    # 14. MÓDULOS CON NAMESPACE (Apps separadas)
    path('recepcion/', include(('recepcion.urls', 'recepcion'), namespace='recepcion')),
    path('consultorio/', include(('consultorio.urls', 'consultorio'), namespace='consultorio')),
    path('pacientes/', include(('pacientes.urls', 'pacientes'), namespace='pacientes')),
    path('logistica/', include(('logistica.urls', 'logistica'), namespace='logistica')),
    path('marketing/', include(('marketing.urls', 'marketing'), namespace='marketing')),
    path('enfermeria/', include(('enfermeria.urls', 'enfermeria'), namespace='enfermeria')),
    path('iot/', include(('iot.urls', 'iot'), namespace='iot')),
    path('laboratorio/', include(('laboratorio.urls', 'laboratorio'), namespace='laboratorio')),
    path('lims/', include('lims.urls')),
    
    # 15. PRIS-CHAT: MENSAJERIA INTERNA (ESTILO WHATSAPP)
    path('chat/', chat_views.chat_page, name='pris_chat'),
    path('chat/api/enviar/', chat_views.api_enviar_mensaje, name='api_enviar_mensaje'),
    path('chat/api/enviar-audio/', chat_views.api_enviar_audio, name='api_enviar_audio'),
    path('chat/api/mensajes/', chat_views.api_obtener_mensajes, name='api_obtener_mensajes'),
    path('chat/api/conversaciones/', chat_views.api_listar_conversaciones, name='api_listar_conversaciones'),
    path('chat/api/usuarios/', chat_views.api_listar_usuarios, name='api_listar_usuarios'),
    
    # 16. API FARMACIA (LECTURA PARA MÉDICOS)
    path('farmacia/api/buscar-productos-lectura/', views.api_buscar_productos_lectura, name='api_buscar_productos_lectura'),
    
    # 17. EXPEDIENTE CLÍNICO UNIVERSAL
    path('medico/api/buscar-paciente-avanzado/', views.api_buscar_paciente_avanzado, name='api_buscar_paciente_avanzado'),
    path('medico/expediente/<int:paciente_id>/', views.expediente_clinico, name='expediente_clinico_medico'),
    
    # 18. SISTEMA DE AUDITORÍA: Captura de Errores del Frontend
    path('api/log-frontend-error/', views.log_frontend_error, name='log_frontend_error'),

    # 19. SERVICE WORKER (PWA) - served from root for full scope
    path('sw.js', service_worker_view, name='service_worker'),

    # 20. PRIS JARVIS — APIs de Dictado, Voz y Acciones (modelos reales activos)
    path('api/pris/dictado/resultado/', __import__('core.views.pris_jarvis', fromlist=['api_dictado_resultado']).api_dictado_resultado, name='pris_dictado_resultado'),
    path('api/pris/dictado/inventario/', __import__('core.views.pris_jarvis', fromlist=['api_dictado_inventario']).api_dictado_inventario, name='pris_dictado_inventario'),
    path('api/pris/dictado/buscar/', __import__('core.views.pris_jarvis', fromlist=['api_dictado_busqueda']).api_dictado_busqueda, name='pris_dictado_busqueda'),
    path('api/pris/dictado/validar-orden/', __import__('core.views.pris_jarvis', fromlist=['api_dictado_validar_orden']).api_dictado_validar_orden, name='pris_dictado_validar_orden'),
    path('api/pris/ocr/', __import__('core.views.pris_jarvis', fromlist=['api_ocr_documento']).api_ocr_documento, name='pris_ocr_documento'),
    path('api/pris/archivo-raw/', __import__('core.views.pris_jarvis', fromlist=['api_crear_archivo_raw']).api_crear_archivo_raw, name='pris_crear_archivo_raw'),
    path('api/pris/consulta-voz/', __import__('core.views.pris_jarvis', fromlist=['api_consulta_voz']).api_consulta_voz, name='pris_consulta_voz'),
    path('api/pris/hoja-trabajo/', __import__('core.views.pris_jarvis', fromlist=['api_generar_hoja_trabajo']).api_generar_hoja_trabajo, name='pris_hoja_trabajo'),
    path('api/pris/alerta-clinica/', __import__('core.views.pris_jarvis', fromlist=['api_crear_alerta_clinica']).api_crear_alerta_clinica, name='pris_alerta_clinica'),
    path('api/pris/coach-toma-muestra/', __import__('core.views.pris_jarvis', fromlist=['api_coach_toma_muestra']).api_coach_toma_muestra, name='pris_coach_toma_muestra'),
    path('api/pris/accion/<int:accion_id>/confirmar/', __import__('core.views.pris_jarvis', fromlist=['api_confirmar_accion']).api_confirmar_accion, name='pris_jarvis_confirmar'),
    path('api/pris/accion/<int:accion_id>/rechazar/', __import__('core.views.pris_jarvis', fromlist=['api_rechazar_accion']).api_rechazar_accion, name='pris_jarvis_rechazar'),
    # Nota: lista_acciones_pris y validar_accion_pris ya están definidas en líneas ~425-426
    # Se eliminaron duplicados para evitar conflicto en reverse()

    # 21. FEATURE FLAGS y AUDIO LEGAL — definiciones canónicas en sección 7 (líneas ~273-278)
    # Rutas duplicadas eliminadas para evitar conflicto en reverse()

    # 23. BIENESTAR STAFF — Capacitaciones
    path('bienestar/capacitaciones/', __import__('core.views.bienestar', fromlist=['capacitaciones']).capacitaciones, name='capacitaciones_bienestar'),

    # ══════════════════════════════════════════════════════════════════════════
    # BRECHAS DE ORO v5.1 — 5 Módulos de Élite
    # ══════════════════════════════════════════════════════════════════════════

    # 24. WAR ROOM — Dashboard de Excepciones del Director
    path('director/war-room/', __import__('core.views.war_room', fromlist=['war_room']).war_room, name='war_room'),
    path('director/war-room/api/anomalias/', __import__('core.views.war_room', fromlist=['api_war_room_anomalias']).api_war_room_anomalias, name='api_war_room_anomalias'),

    # 24b. GESTIÓN DE ANALIZADORES — Director
    path('director/analizadores/', __import__('core.views.director', fromlist=['director_analizadores']).director_analizadores, name='director_analizadores'),
    path('director/analizadores/crear/', __import__('core.views.director', fromlist=['director_analizadores_crear']).director_analizadores_crear, name='director_analizadores_crear'),
    path('director/analizadores/<int:equipo_id>/toggle/', __import__('core.views.director', fromlist=['director_analizadores_toggle']).director_analizadores_toggle, name='director_analizadores_toggle'),
    path('director/analizadores/<int:equipo_id>/mapeos/', __import__('core.views.director', fromlist=['director_analizadores_mapeos']).director_analizadores_mapeos, name='director_analizadores_mapeos'),
    path('director/analizadores/probar-conexion/', __import__('core.views.director', fromlist=['director_analizadores_probar_conexion']).director_analizadores_probar_conexion, name='director_analizadores_probar_conexion'),
    path('director/analizadores/mapeo/<int:mapeo_id>/eliminar/', __import__('core.views.director', fromlist=['director_analizadores_eliminar_mapeo']).director_analizadores_eliminar_mapeo, name='director_analizadores_eliminar_mapeo'),

    # 25. CADENA DE FRIO — Validación ISO 15189 de temperatura en traslado
    path('api/logistica/transferencia/<int:transferencia_id>/temperatura/', __import__('logistica.views', fromlist=['api_cadena_frio_temperatura']).api_cadena_frio_temperatura, name='api_cadena_frio_temperatura'),

    # 26. PREDICCIÓN DE STOCK — Reporte predictivo IA
    path('inventario/prediccion/', __import__('core.views.inventario_predictivo', fromlist=['reporte_prediccion_stock']).reporte_prediccion_stock, name='inventario_prediccion'),
    path('inventario/prediccion/api/', __import__('core.views.inventario_predictivo', fromlist=['api_prediccion_stock']).api_prediccion_stock, name='api_prediccion_stock'),

    # 27. CONSENTIMIENTO INFORMADO DIGITAL — Firma biométrica en pantalla
    path('consentimiento/<int:orden_id>/', __import__('core.views.consentimiento_digital', fromlist=['pagina_consentimiento']).pagina_consentimiento, name='consentimiento_digital'),
    path('consentimiento/<int:orden_id>/guardar/', __import__('core.views.consentimiento_digital', fromlist=['api_guardar_consentimiento']).api_guardar_consentimiento, name='api_guardar_consentimiento'),
    path('consentimiento/pdf/<str:folio>/', __import__('core.views.consentimiento_digital', fromlist=['descargar_pdf_consentimiento']).descargar_pdf_consentimiento, name='descargar_pdf_consentimiento'),

    # ══════════════════════════════════════════════════════════════════════════
    # PRISLAB V8.1 — SILO LABORATORIO: Inventario de Reactivos ISO 15189
    # FEFO automático · Cuarentena QC · Dashboard Director · Trazabilidad
    # ══════════════════════════════════════════════════════════════════════════
    path('silo-lab/', include('inventario.urls', namespace='inventario')),

    # ══════════════════════════════════════════════════════════════════════════
    # PRISLAB V8.2 — CMMS: Mantenimiento de Equipos (Protocolos, Checklist,
    # Árbol de Diagnóstico, Tickets, TCO, QR Gemelo Digital)
    # ══════════════════════════════════════════════════════════════════════════
    path('mantenimiento/', include('mantenimiento.urls', namespace='mantenimiento')),

    # ══════════════════════════════════════════════════════════════════════════
    # PRISLAB V6.0 — ONBOARDING WIZARD (Solo Superusuario PRISLAB)
    # ══════════════════════════════════════════════════════════════════════════
    path(
        'onboarding/',
        __import__('core.views.onboarding', fromlist=['OnboardingWizardView']).OnboardingWizardView.as_view(),
        name='onboarding_wizard',
    ),
    path(
        'onboarding/crear/',
        __import__('core.views.onboarding', fromlist=['OnboardingCrearEmpresaView']).OnboardingCrearEmpresaView.as_view(),
        name='onboarding_crear_empresa',
    ),
    path(
        'onboarding/parse-excel/',
        __import__('core.views.onboarding', fromlist=['api_parse_excel_personal']).api_parse_excel_personal,
        name='onboarding_parse_excel',
    ),
    path(
        'onboarding/empresas/',
        __import__('core.views.onboarding', fromlist=['api_listar_empresas']).api_listar_empresas,
        name='onboarding_listar_empresas',
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # CFDI 4.0 — Portal público de autofacturación (sin login, para pacientes)
    # El QR del ticket apunta aquí: /facturacion/autofactura/?folio=VTA-0001
    # ══════════════════════════════════════════════════════════════════════════
    path(
        'facturacion/autofactura/',
        __import__('core.views.autofactura', fromlist=['autofactura_publica']).autofactura_publica,
        name='autofactura_publica',
    ),
    path(
        'facturacion/solicitudes/',
        __import__('core.views.autofactura', fromlist=['bandeja_cfdi']).bandeja_cfdi,
        name='bandeja_cfdi',
    ),
    path(
        'facturacion/cfdi/<int:factura_id>/timbrar/',
        __import__('core.views.autofactura', fromlist=['api_marcar_cfdi_timbrada']).api_marcar_cfdi_timbrada,
        name='api_marcar_cfdi_timbrada',
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # CRON INTERNO — Endpoints protegidos para tareas programadas del sistema
    # Llamados por cron, systemd timer o un scheduler externo con X-Cron-Secret
    # ══════════════════════════════════════════════════════════════════════════
    path(
        'cron/check-metrologia/',
        __import__('core.views.cron_tasks', fromlist=['cron_check_metrologia']).cron_check_metrologia,
        name='cron_check_metrologia',
    ),
    path(
        'cron/check-stock-critico/',
        __import__('core.views.cron_tasks', fromlist=['cron_check_stock_critico']).cron_check_stock_critico,
        name='cron_check_stock_critico',
    ),
    path(
        'cron/verify-escudo-clinico/',
        __import__('core.views.cron_tasks', fromlist=['cron_verify_escudo_clinico']).cron_verify_escudo_clinico,
        name='cron_verify_escudo_clinico',
    ),
]

# Servir archivos media en desarrollo
from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
