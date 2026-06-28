"""
URLs del Módulo de Consultorio Médico
Sistema Adaptativo Híbrido + Forense + Imagenología + Isla Independiente
(NOM-004-SSA3-2012)
"""
from django.urls import path
from . import views
from . import pdf_views
from . import pdf_views_prislab
from . import api_views

app_name = "consultorio"

urlpatterns = [
    # Dashboard Principal
    path("", views.dashboard_consultorio, name="dashboard_consultorio"),
    
    # ========== REGISTRO RÁPIDO DE PACIENTES ==========
    path("paciente/nuevo/", views.crear_paciente_express, name="crear_paciente_express"),
    
    # ========== RECEPCIÓN ==========
    path("recepcion/", views.tablero_recepcion, name="tablero_recepcion"),
    path("recepcion/agendar/", views.agendar_cita, name="agendar_cita"),
    path("recepcion/check-in/<int:cita_id>/", views.check_in_cita, name="check_in_cita"),
    
    # ========== ENFERMERÍA (TRIAGE OPCIONAL) ==========
    path("enfermeria/triage/", views.lista_triage, name="lista_triage"),
    path("enfermeria/triage/<int:cita_id>/signos/", views.captura_signos_vitales, name="captura_signos_vitales"),
    
    # ========== CONSULTORIO MÉDICO ==========
    path("medico/lista-trabajo/", views.lista_trabajo_medico, name="lista_trabajo_medico"),
    path("medico/nueva-consulta/", views.nueva_consulta_simplificada, name="nueva_consulta"),
    path("medico/consulta/nueva/<uuid:paciente_uuid>/", views.nueva_consulta_con_paciente, name="nueva_consulta_paciente"),
    path("medico/consulta/<int:cita_id>/", views.nueva_consulta_soap, name="nueva_consulta_soap"),
    
    # Ruta alternativa sin "medico/" para compatibilidad
    path("consulta/<int:cita_id>/", views.nueva_consulta_soap, name="consulta_soap_alt"),
    
    # Consulta sin cita previa (Walk-in)
    path("medico/consulta-sin-cita/", views.consulta_sin_cita, name="consulta_sin_cita"),
    
    # Aliases para compatibilidad de templates
    path("medico/captura/<int:cita_id>/", views.nueva_consulta_soap, name="captura_consulta"),
    path("medico/detalle/<int:cita_id>/", views.nueva_consulta_soap, name="detalle_consulta"),
    path("medico/consulta/ver/<int:consulta_id>/", views.ver_consulta_detalle, name="ver_consulta_detalle"),
    
    # ========== CONFIGURACIÓN DEL MÉDICO (ISLA INDEPENDIENTE) ==========
    path("configuracion/", views.configuracion_medico, name="configuracion_medico"),
    
    # ========== ARCHIVOS ADJUNTOS (Rx, Tomografías, Docs) ==========
    path("paciente/<int:paciente_id>/archivos/", views.archivos_paciente, name="archivos_paciente"),
    
    # ========== LISTA DE ESPERA ==========
    path("lista-espera/", views.lista_espera, name="lista_espera"),
    
    # ========== ANÁLISIS DE PATRONES (IA Confidencial) ==========
    path("analisis-patrones/", views.analisis_patrones, name="analisis_patrones"),
    
    # ========== APIs FLUJO SIMPLIFICADO ==========
    path("api/crear-consulta-directa/", views.api_crear_consulta_directa, name="api_crear_consulta_directa"),
    path("api/crear-paciente-y-consulta/", views.api_crear_paciente_y_consulta, name="api_crear_paciente_y_consulta"),
    path("api/buscar-pacientes/", views.api_buscar_pacientes, name="api_buscar_pacientes"),
    
    # ========== APIs IA (TRANSCRIPCIÓN SOAP INTELIGENTE) ==========
    path("api/analizar-transcripcion/", views.api_analizar_transcripcion, name="api_analizar_transcripcion"),
    path("api/procesar-audio-consulta/", api_views.procesar_audio_consulta, name="api_procesar_audio_consulta"),
    path("api/verificar-gemini/", api_views.verificar_api_gemini, name="api_verificar_gemini"),
    
    # ========== APIs VADEMÉCUM ==========
    path("api/buscar-vademecum/", views.api_buscar_vademecum, name="api_buscar_vademecum"),
    
    # ========== APIs ARCHIVOS ==========
    path("api/subir-archivo/", views.api_subir_archivo, name="api_subir_archivo"),
    path("api/eliminar-archivo/<int:archivo_id>/", views.api_eliminar_archivo, name="api_eliminar_archivo"),
    
    # ========== APIs SIGNOS VITALES (Tendencias/Charts) ==========
    path("api/signos-vitales/<int:paciente_id>/tendencia/", views.api_signos_vitales_tendencia, name="api_signos_vitales_tendencia"),
    
    # ========== APIs PLANTILLAS ==========
    path("api/plantillas/", views.api_plantillas_especialidad, name="api_plantillas_especialidad"),
    path("api/plantillas/<int:plantilla_id>/usar/", views.api_usar_plantilla, name="api_usar_plantilla"),
    
    # ========== APIs ANÁLISIS DE PATRONES ==========
    path("api/generar-analisis-patron/", views.api_generar_analisis_patron, name="api_generar_analisis_patron"),
    
    # ========== APIs LISTA DE ESPERA ==========
    path("api/lista-espera/agregar/", views.api_agregar_lista_espera, name="api_agregar_lista_espera"),

    # ========== API RESULTADOS DISPONIBLES (Dashboard Médico) ==========
    path("api/resultados-disponibles/", views.api_resultados_disponibles, name="api_resultados_disponibles"),
    
    # ========== APIs GENERACIÓN INMEDIATA (sin esperar al final) ==========
    path("api/generar-receta-inmediata/", views.api_generar_receta_inmediata, name="api_generar_receta_inmediata"),
    path("api/generar-certificado-inmediato/", views.api_generar_certificado_inmediato, name="api_generar_certificado_inmediato"),
    path("api/generar-orden-laboratorio-inmediata/", views.api_generar_orden_laboratorio_inmediata, name="api_generar_orden_laboratorio_inmediata"),
    
    # ========== HISTORIAL Y REPORTES ==========
    path("paciente/<int:paciente_id>/historial/", views.historial_clinico_paciente, name="historial_clinico_paciente"),
    path("paciente/<int:paciente_id>/signos-vitales/", views.historial_signos_vitales, name="historial_signos_vitales"),
    
    # ========== VADEMÉCUM ==========
    path("vademecum/", views.vademecum_lista, name="vademecum_lista"),
    
    # ========== AGENDA DEL MÉDICO ==========
    path("agenda/", views.agenda_medico, name="agenda_medico"),
    
    # ========== TRIAJE DIGITAL PRE-CITA ==========
    path("triaje-pre-cita/", views.triaje_pre_cita, name="triaje_pre_cita"),
    
    # ========== MARKETING MÉDICO ==========
    path("marketing/campanas/", views.campanas_marketing, name="campanas_marketing"),
    
    # ========== ENCUESTAS DE SATISFACCIÓN (NPS) ==========
    path("encuestas/satisfaccion/", views.encuestas_satisfaccion, name="encuestas_satisfaccion"),
    
    # ========== SEGUIMIENTO DE TRATAMIENTO ==========
    path("seguimiento/tratamiento/", views.seguimiento_tratamiento, name="seguimiento_tratamiento"),
    
    # ========== REPORTES DE PRODUCTIVIDAD ==========
    path("reportes/productividad/", views.reportes_productividad, name="reportes_productividad"),
    
    # ========== TELEMEDICINA (VIDEOLLAMADA) ==========
    path("telemedicina/", views.videollamada_segura, name="videollamada_segura"),
    path("api/telemedicina/sala/", views.api_crear_sala_videollamada, name="api_crear_sala_videollamada"),
    
    # ========== COBRO DE CONSULTA (FASE 10: BLINDAJE) ==========
    path("cobros/", views.cobro_consulta, name="cobro_consulta"),
    path("cobros/liquidacion/", views.reporte_liquidacion, name="reporte_liquidacion"),
    path("api/registrar-cobro/", views.api_registrar_cobro, name="api_registrar_cobro"),
    path("api/liquidar-vale/", views.api_liquidar_vale, name="api_liquidar_vale"),
    
    # ========== CERTIFICADOS MÉDICOS ==========
    path("certificado/nuevo/", views.generar_certificado, name="generar_certificado"),
    path("certificado/nuevo/<int:consulta_id>/", views.generar_certificado, name="generar_certificado_consulta"),
    path("certificado/<int:certificado_id>/", views.ver_certificado, name="ver_certificado"),
    
    # ========== PDFs PROFESIONALES ==========
    path("pdf/receta/<int:consulta_id>/", pdf_views_prislab.imprimir_receta_profesional, name="pdf_receta_paciente"),
    path("api/receta-pdf/<int:consulta_id>/", pdf_views_prislab.api_generar_receta_pdf, name="api_receta_pdf"),
    path("pdf/forense/<int:consulta_id>/", pdf_views.imprimir_expediente_forense, name="pdf_expediente_forense"),

    # ========== PRIS SENTINEL: TELEMETRÍA INTELIGENTE Y AUTOCURACIÓN ==========
    path("sentinel/", views.sentinel_dashboard, name="sentinel_dashboard"),
    path("sentinel/ssh-guide/", views.sentinel_ssh_guide, name="sentinel_ssh_guide"),
    path("sentinel/<int:incidencia_id>/", views.sentinel_detalle, name="sentinel_detalle"),
    path("api/sentinel/feedback/", views.api_sentinel_feedback, name="api_sentinel_feedback"),
    path("api/sentinel/exportar/<int:incidencia_id>/", views.api_sentinel_exportar_cursor, name="api_sentinel_exportar_cursor"),
    path("api/sentinel/ssh/<int:incidencia_id>/", views.api_sentinel_ssh, name="api_sentinel_ssh"),
    path("api/sentinel/test-github/", views.api_test_github_sentinel, name="api_test_github_sentinel"),
    path("api/sentinel/resolver-conocidas/", views.api_resolver_incidencias_sentinel, name="api_resolver_incidencias_sentinel"),
    path("api/sentinel/feedback-lista/", views.api_sentinel_listar_feedback, name="api_sentinel_listar_feedback"),
]
