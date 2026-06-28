from django.urls import path, include
from core import views
from core.views import medico as medico_views
from core.views.paciente_detalle import ExpedienteClinicoView, exportar_historial_pdf
from core.views.consentimiento_digital import (
    pagina_consentimiento,
    api_guardar_consentimiento as api_guardar_consentimiento_digital,
    descargar_pdf_consentimiento,
)
from core.views.onboarding import (
    OnboardingWizardView,
    OnboardingCrearEmpresaView,
    api_parse_excel_personal,
    api_listar_empresas,
)
from core.views.inventario_predictivo import (
    reporte_prediccion_stock,
    api_prediccion_stock,
)
from inventario.views import dashboard_reactivos
from ._helpers import lazy_view

urlpatterns = [
    # 3. MÓDULO MÉDICO (Consultorio)
    path('medico/', views.dashboard_medico, name='medico'),
    path('medico/consulta/', views.consulta_medica, name='consulta_medica'),
    path('medico/consulta/<int:paciente_id>/', views.consulta_medica, name='consulta_medica'),
    path('medico/api/buscar-paciente/', views.buscar_paciente, name='buscar_paciente'),
    path('medico/api/verificar-existencia-farmacia/', views.verificar_existencia_farmacia, name='verificar_existencia_farmacia'),
    path('medico/receta/<int:receta_id>/', medico_views.ver_receta_medica, name='ver_receta_medica'),
    path('medico/receta/<int:receta_id>/pdf/', medico_views.generar_pdf_receta, name='generar_pdf_receta'),
    path('medico/api/verificar-qr-receta/', views.verificar_qr_receta, name='verificar_qr_receta'),
    path('medico/api/buscar-paciente-avanzado/', views.api_buscar_paciente_avanzado, name='api_buscar_paciente_avanzado'),
    path('medico/expediente/<int:paciente_id>/', views.expediente_clinico, name='expediente_clinico_medico'),

    # 11B. MÓDULO MÉDICO: ULTRASONIDO
    path('medico/ultrasonido/lista-trabajo/', medico_views.lista_trabajo_usg, name='lista_trabajo_usg'),
    path('medico/ultrasonido/captura/', medico_views.captura_reporte_usg, name='captura_reporte_usg'),
    path('medico/ultrasonido/captura/<int:paciente_id>/', medico_views.captura_reporte_usg, name='captura_reporte_usg_paciente'),
    path('medico/ultrasonido/<int:reporte_id>/pdf/', medico_views.descargar_pdf_ultrasonido, name='descargar_pdf_ultrasonido'),

    # 4. MANUAL OPERATIVO
    path('manual/', views.manual_operativo, name='manual_operativo'),
    path('manual/pdf/', views.manual_operativo_pdf, name='manual_operativo_pdf'),

    # 8. MÓDULO CATÁLOGOS
    path('catalogos/estudios/', views.lista_estudios, name='lista_estudios'),
    path('catalogos/medicos/', views.catalogo_medicos, name='catalogo_medicos'),
    path('catalogos/convenios/', views.catalogo_convenios, name='catalogo_convenios'),
    path('catalogos/convenios/<int:convenio_id>/precios/', views.convenio_precios, name='convenio_precios'),

    # 9. MÓDULO INVENTARIO
    path('inventario/', dashboard_reactivos, name='inventario_general'),

    # 10. MÓDULO COTIZACIÓN
    path('cotizacion/', views.cotizacion_rapida, name='cotizacion_rapida'),
    path('cotizacion/api/buscar-paciente/', views.api_buscar_paciente_cotizacion, name='api_buscar_paciente_cotizacion'),
    path('cotizacion/api/crear-paciente/', views.api_crear_paciente_rapido, name='api_crear_paciente_rapido'),
    path('cotizacion/api/buscar-estudios/', views.api_buscar_estudios_cotizacion, name='api_buscar_estudios_cotizacion'),
    path('cotizacion/api/enviar-whatsapp/', views.api_enviar_whatsapp_cotizacion, name='api_enviar_whatsapp_cotizacion'),
    path('cotizacion/api/convertir-orden/', views.convertir_cotizacion_orden, name='convertir_cotizacion_orden'),

    # 13. MÓDULO DE NÓMINA
    path('nomina/periodos/<int:periodo_id>/calcular/', lazy_view('core.views.nomina.calcular_nomina'), name='calcular_nomina'),
    path('nomina/recibos/<int:nomina_id>/autorizar/', lazy_view('core.views.nomina.autorizar_nomina'), name='autorizar_nomina'),

    # 14. MÓDULO DE ASISTENCIA
    path('asistencia/', views.dashboard_asistencia, name='dashboard_asistencia'),
    path('asistencia/registros/', views.registro_asistencia, name='registro_asistencia'),
    path('asistencia/registrar/', views.registrar_entrada_salida, name='registrar_entrada_salida'),
    path('asistencia/horarios/', views.horarios_trabajo, name='horarios_trabajo'),
    path('asistencia/crear-horario/', views.crear_horario, name='crear_horario'),
    path('asistencia/incidencias/', views.incidencias_asistencia, name='incidencias_asistencia'),
    path('asistencia/crear-incidencia/', views.crear_incidencia, name='crear_incidencia'),
    path('asistencia/incidencia/<int:incidencia_id>/autorizar/', views.autorizar_incidencia, name='autorizar_incidencia'),

    # 15. MÓDULO DE ENTREGA DE RESULTADOS — rutas de logística de muestra
    path('logistica/rutas-recoleccion/', views.rutas_recoleccion, name='rutas_recoleccion_alias'),

    # 16. MÓDULO DE MAQUILA — alias logística
    # (rutas canónicas en laboratorio.py)

    # 17. MÓDULO DE CAPACITACIÓN
    path('capacitacion/personal/', views.capacitacion_personal, name='capacitacion_personal'),
    path('capacitacion/ejecutiva/', views.capacitacion_ejecutiva, name='capacitacion_ejecutiva'),

    # 19. MÓDULO DE CAPACITACIÓN CON RAG
    path('capacitacion/rag/', views.dashboard_capacitacion, name='dashboard_capacitacion'),
    path('capacitacion/rag/subir/', views.subir_documento_capacitacion, name='subir_documento_capacitacion'),
    path('capacitacion/rag/consultar/', views.consultar_pris_rag, name='consultar_pris_rag'),
    path('capacitacion/rag/worklist/', views.consultar_pris_worklist, name='consultar_pris_worklist'),
    path('capacitacion/rag/reprocesar/<uuid:documento_id>/', views.reprocesar_documento, name='reprocesar_documento_rag'),
    path('capacitacion/rag/estado/<uuid:documento_id>/', views.estado_documento_rag, name='estado_documento_rag'),
    path('capacitacion/rag/eliminar/<uuid:documento_id>/', views.eliminar_documento, name='eliminar_documento_rag'),
    path('capacitacion/rag/tip/', views.obtener_tip_dia, name='obtener_tip_dia'),

    # SISTEMA DE NOTIFICACIONES INTERNAS
    path('notificaciones/', lazy_view('core.views.notificaciones.lista_notificaciones'), name='notificaciones_lista'),
    path('notificaciones/badge/', lazy_view('core.views.notificaciones.api_notificaciones_badge'), name='notificaciones_badge'),
    path('notificaciones/<int:notificacion_id>/leer/', lazy_view('core.views.notificaciones.marcar_leida'), name='notificacion_leer'),
    path('notificaciones/marcar-todas/', lazy_view('core.views.notificaciones.marcar_todas_leidas'), name='notificaciones_marcar_todas'),
    path('notificaciones/configurar/', lazy_view('core.views.notificaciones.configurar_notificaciones'), name='configurar_notificaciones'),
    path('notificaciones/ejecutar-verificaciones/', lazy_view('core.views.notificaciones.ejecutar_verificaciones'), name='ejecutar_verificaciones'),

    # MÓDULO DE NÓMINA (dashboard y resto)
    path('nomina/', lazy_view('core.views.nomina.dashboard_nomina'), name='nomina_dashboard'),
    path('nomina/periodos/', lazy_view('core.views.nomina.lista_periodos'), name='nomina_lista_periodos'),
    path('nomina/periodos/nuevo/', lazy_view('core.views.nomina.crear_periodo'), name='nomina_crear_periodo'),
    path('nomina/periodos/<int:pk>/', lazy_view('core.views.nomina.detalle_periodo'), name='nomina_detalle_periodo'),
    path('nomina/periodos/<int:pk>/pagar/', lazy_view('core.views.nomina.marcar_periodo_pagado'), name='nomina_marcar_pagado'),
    path('nomina/recibos/<int:pk>/editar/', lazy_view('core.views.nomina.editar_recibo'), name='nomina_editar_recibo'),
    path('nomina/api/resumen/', lazy_view('core.views.nomina.api_resumen_nomina'), name='nomina_api_resumen'),

    # CRM
    path('crm/', lazy_view('core.views.crm.dashboard_crm'), name='crm_dashboard'),
    path('crm/prospectos/', lazy_view('core.views.crm.lista_prospectos'), name='crm_lista_prospectos'),
    path('crm/prospectos/nuevo/', lazy_view('core.views.crm.crear_prospecto'), name='crm_crear_prospecto'),
    path('crm/prospectos/<int:pk>/', lazy_view('core.views.crm.detalle_prospecto'), name='crm_detalle_prospecto'),
    path('crm/prospectos/<int:pk>/seguimiento/', lazy_view('core.views.crm.agregar_seguimiento'), name='crm_agregar_seguimiento'),
    path('crm/api/kanban/', lazy_view('core.views.crm.api_kanban_crm'), name='crm_api_kanban'),
    path('crm/clientes/', views.lista_clientes_crm, name='lista_clientes_crm'),
    path('crm/clientes/crear/', views.crear_cliente_crm, name='crear_cliente_crm'),
    path('crm/clientes/<int:cliente_id>/', views.ver_cliente_crm, name='ver_cliente_crm'),
    path('crm/clientes/<int:cliente_id>/interaccion/', views.crear_interaccion_crm, name='crear_interaccion_crm'),
    path('crm/oportunidades/', views.lista_oportunidades_crm, name='lista_oportunidades_crm'),
    path('crm/oportunidades/crear/', views.crear_oportunidad_crm, name='crear_oportunidad_crm'),
    path('crm/oportunidades/<int:oportunidad_id>/', views.ver_oportunidad_crm, name='ver_oportunidad_crm'),
    path('crm/oportunidades/<int:oportunidad_id>/cerrar/', views.cerrar_oportunidad, name='cerrar_oportunidad'),

    # 12. MÓDULO RECURSOS HUMANOS
    path('rh/evaluaciones/', views.lista_evaluaciones_39a, name='lista_evaluaciones_39a'),
    path('rh/evaluaciones/crear/', views.crear_evaluacion_39a, name='crear_evaluacion_39a'),
    path('rh/evaluaciones/crear/<int:empleado_id>/', views.crear_evaluacion_39a, name='crear_evaluacion_39a'),
    path('rh/evaluaciones/<int:evaluacion_id>/', views.ver_evaluacion_39a, name='ver_evaluacion_39a'),
    path('rh/evaluaciones/<int:evaluacion_id>/pdf/', views.descargar_pdf_evaluacion_39a, name='descargar_pdf_evaluacion_39a'),
    path('rh/desempeno/nueva/', views.nueva_evaluacion_desempeno, name='nueva_evaluacion_desempeno'),
    path('rh/desempeno/nueva/<int:empleado_id>/', views.nueva_evaluacion_desempeno, name='nueva_evaluacion_desempeno'),
    path('rh/desempeno/<int:evaluacion_id>/', views.ver_evaluacion_desempeno, name='ver_evaluacion_desempeno'),
    path('rh/mis-resultados/', views.mis_resultados, name='mis_resultados'),
    path('rh/matriz-talento/', views.matriz_talento, name='matriz_talento'),

    # 13. MÓDULO CEREBRO/IA
    path('cerebro/chat/', views.chat_experto, name='chat_experto'),
    path('api/cerebro/preguntar/', views.api_cerebro_preguntar, name='api_cerebro_preguntar'),

    # 15. PRIS-CHAT
    path('chat/', lazy_view('core.views.comunicacion.chat_page'), name='pris_chat'),
    path('chat/api/enviar/', lazy_view('core.views.comunicacion.api_enviar_mensaje'), name='api_enviar_mensaje'),
    path('chat/api/enviar-audio/', lazy_view('core.views.comunicacion.api_enviar_audio'), name='api_enviar_audio'),
    path('chat/api/mensajes/', lazy_view('core.views.comunicacion.api_obtener_mensajes'), name='api_obtener_mensajes'),
    path('chat/api/conversaciones/', lazy_view('core.views.comunicacion.api_listar_conversaciones'), name='api_listar_conversaciones'),
    path('chat/api/usuarios/', lazy_view('core.views.comunicacion.api_listar_usuarios'), name='api_listar_usuarios'),

    # 15. MÓDULO: ANALYTICS Y REPORTES CENTRALIZADOS
    path('analytics/', views.dashboard_analytics, name='dashboard_analytics'),
    path('analytics/trazabilidad/', views.reporte_trazabilidad, name='reporte_trazabilidad'),
    path('analytics/api/metricas-tiempo-real/', views.api_metricas_tiempo_real, name='api_metricas_tiempo_real'),

    # 16. DASHBOARD UNIFICADO
    path('dashboard-unificado/', views.dashboard_unificado, name='dashboard_unificado'),
    path('dashboard-unificado/api/kpis-tiempo-real/', views.api_kpis_tiempo_real, name='api_kpis_tiempo_real'),

    # API PACIENTES (compartida entre módulos)
    path('api/pacientes/guardar/', views.api_guardar_paciente, name='api_guardar_paciente'),
    path('api/pacientes/buscar/', views.api_buscar_pacientes, name='api_buscar_pacientes'),

    # OMNISEARCH
    path('api/omnisearch/', views.api_omnisearch, name='api_omnisearch'),

    # EXPEDIENTE CLÍNICO UNIFICADO
    path('pacientes/<int:pk>/expediente/', ExpedienteClinicoView.as_view(), name='expediente_clinico'),
    path('pacientes/<int:paciente_id>/exportar-historial/', exportar_historial_pdf, name='exportar_historial_pdf'),

    # 18. MÓDULO DE BIENESTAR
    path('bienestar/', include(('bienestar.urls', 'bienestar'), namespace='bienestar')),
    path('bienestar/pris/chat/', views.chat_bienestar, name='chat_bienestar'),
    path('bienestar/pris/chat/enviar/', views.enviar_mensaje_bienestar, name='enviar_mensaje_bienestar'),
    path('bienestar/pris/alertas/', views.alertas_bienestar_director, name='alertas_bienestar_director'),
    path('bienestar/pris/alertas/<int:alerta_id>/vista/', views.marcar_alerta_vista, name='marcar_alerta_vista'),

    # 23. BIENESTAR STAFF
    path('bienestar-staff/', lazy_view('core.views.bienestar.dashboard_bienestar'), name='bienestar_dashboard'),
    path('bienestar-staff/diario/', lazy_view('core.views.bienestar.diario_emocional'), name='diario_emocional'),
    path('bienestar-staff/nom035/', lazy_view('core.views.bienestar.evaluacion_nom035'), name='evaluacion_nom035'),
    path('bienestar-staff/alertas-rrhh/', lazy_view('core.views.bienestar.alertas_rrhh'), name='bienestar_alertas_rrhh'),
    path('bienestar-staff/capacitaciones/', lazy_view('core.views.bienestar.capacitaciones'), name='capacitaciones_bienestar'),

    # 26. PREDICCIÓN DE STOCK
    path('inventario/prediccion/', reporte_prediccion_stock, name='inventario_prediccion'),
    path('inventario/prediccion/api/', api_prediccion_stock, name='api_prediccion_stock'),

    # 27. CONSENTIMIENTO INFORMADO DIGITAL
    path('consentimiento/<int:orden_id>/', pagina_consentimiento, name='consentimiento_digital'),
    path('consentimiento/<int:orden_id>/guardar/', api_guardar_consentimiento_digital, name='api_guardar_consentimiento_digital'),
    path('consentimiento/pdf/<str:folio>/', descargar_pdf_consentimiento, name='descargar_pdf_consentimiento'),

    # ONBOARDING WIZARD
    path('onboarding/', OnboardingWizardView.as_view(), name='onboarding_wizard'),
    path('onboarding/crear/', OnboardingCrearEmpresaView.as_view(), name='onboarding_crear_empresa'),
    path('onboarding/parse-excel/', api_parse_excel_personal, name='onboarding_parse_excel'),
    path('onboarding/empresas/', api_listar_empresas, name='onboarding_listar_empresas'),

    # 14. MÓDULOS CON NAMESPACE (Apps separadas)
    path('seguridad/', include(('seguridad.urls', 'seguridad'), namespace='seguridad')),
    path('academia/', include(('academia.urls', 'academia'), namespace='academia')),
    path('recepcion/', include(('recepcion.urls', 'recepcion'), namespace='recepcion')),
    path('consultorio/', include(('consultorio.urls', 'consultorio'), namespace='consultorio')),
    path('pacientes/', include(('pacientes.urls', 'pacientes'), namespace='pacientes')),
    path('logistica/', include(('logistica.urls', 'logistica'), namespace='logistica')),
    path('marketing/', include(('marketing.urls', 'marketing'), namespace='marketing')),
    path('enfermeria/', include(('enfermeria.urls', 'enfermeria'), namespace='enfermeria')),
    path('iot/', include(('iot.urls', 'iot'), namespace='iot')),
    path('silo-lab/', include('inventario.urls', namespace='inventario')),
    path('mantenimiento/', include('mantenimiento.urls', namespace='mantenimiento')),

    # 25. CADENA DE FRIO
    path('api/logistica/transferencia/<int:transferencia_id>/temperatura/', lazy_view('logistica.views.api_cadena_frio_temperatura'), name='api_cadena_frio_temperatura'),
]
