from django.urls import path, include
from core.views.pris_jarvis import (
    api_dictado_resultado,
    api_dictado_inventario,
    api_dictado_busqueda,
    api_dictado_validar_orden,
    api_ocr_documento,
    api_crear_archivo_raw,
    api_consulta_voz,
    api_generar_hoja_trabajo,
    api_crear_alerta_clinica,
    api_coach_toma_muestra,
    api_confirmar_accion,
    api_rechazar_accion,
)
from core.views.pris_checklist import (
    api_detectar_intents_checklist,
    api_guia_preguntas,
)
from ._helpers import lazy_view

urlpatterns = [
    # PRIS SENTINEL V4: WEB PUSH NOTIFICATIONS
    path('api/push/vapid/', lazy_view('core.views.push.obtener_vapid_key'), name='push_vapid_key'),
    path('api/push/suscribir/', lazy_view('core.views.push.suscribir_push'), name='push_suscribir'),
    path('api/push/desuscribir/', lazy_view('core.views.push.desuscribir_push'), name='push_desuscribir'),
    path('api/push/estado/', lazy_view('core.views.push.estado_suscripciones'), name='push_estado'),
    path('api/push/test/', lazy_view('core.views.push.test_notificacion'), name='push_test'),

    # PRIS VOICE COMMANDER: CONTROL POR VOZ
    path('api/voice/process/', lazy_view('core.views.voice.procesar_comando_api'), name='voice_process'),
    path('api/voice/history/', lazy_view('core.views.voice.historial_comandos'), name='voice_history'),
    path('api/voice/verify-auth/', lazy_view('core.views.voice.verificar_webauthn'), name='voice_verify_auth'),
    path('voice/logs/', lazy_view('core.views.voice.dashboard_voice_logs'), name='voice_logs_dashboard'),

    # PRIS IA: ASISTENTE CONVERSACIONAL
    path('ia/asistente/', lazy_view('core.views.pris_ia.asistente_page'), name='pris_ia_asistente'),
    path('ia/asistente/chat/', lazy_view('core.views.pris_ia.asistente_chat'), name='pris_ia_chat'),
    path('ia/asistente/reset/', lazy_view('core.views.pris_ia.asistente_reset'), name='pris_ia_reset'),

    # Webhooks PRISCI
    path('api/prisci/webhook/', lazy_view('core.views.prisci_webhook.webhook'), name='prisci_webhook'),
    path('api/prisci/webhook/verify/', lazy_view('core.views.prisci_webhook.verify'), name='prisci_webhook_verify'),

    # AccionPRIS — Auditoría ISO 15189
    path('pris/api/acciones/pendientes/', lazy_view('core.views.pris_ia.api_acciones_pendientes'), name='pris_acciones_pendientes'),
    path('pris/api/accion/<int:accion_id>/confirmar/', lazy_view('core.views.pris_ia.api_confirmar_accion'), name='pris_confirmar_accion'),
    path('pris/api/accion/<int:accion_id>/rechazar/', lazy_view('core.views.pris_ia.api_rechazar_accion'), name='pris_rechazar_accion'),

    # PRIS — Sistema Nervioso Central (rutas directas legacy)
    path('pris/api/dictado-inventario/', lazy_view('core.views.pris_ia.api_dictado_inventario'), name='api_dictado_inventario'),
    path('pris/api/dictado-resultado/', lazy_view('core.views.pris_ia.api_dictado_resultado'), name='api_dictado_resultado'),
    path('pris/api/ocr-documento/', lazy_view('core.views.pris_ia.api_ocr_documento'), name='api_ocr_documento'),
    path('pris/api/crear-archivo-raw/', lazy_view('core.views.pris_ia.api_crear_archivo_raw'), name='api_crear_archivo_raw'),
    path('pris/api/consulta-voz/', lazy_view('core.views.pris_ia.api_consulta_voz'), name='api_consulta_voz'),
    path('pris/api/generar-hoja-trabajo/', lazy_view('core.views.pris_ia.api_generar_hoja_trabajo'), name='api_generar_hoja_trabajo'),
    path('pris/api/crear-alerta-clinica/', lazy_view('core.views.pris_ia.api_crear_alerta_clinica'), name='api_crear_alerta_clinica'),
    path('pris/acciones/', lazy_view('core.views.pris_ia.lista_acciones_pris'), name='lista_acciones_pris'),
    path('pris/acciones/<int:accion_id>/validar/', lazy_view('core.views.pris_ia.validar_accion_pris'), name='validar_accion_pris'),

    # Checklist Autónomo por Escucha Activa
    path('pris/api/checklist-nlp/', api_detectar_intents_checklist, name='pris_checklist_nlp'),
    path('pris/api/checklist-guia/', api_guia_preguntas, name='pris_checklist_guia'),

    # 20. PRIS JARVIS — APIs de Dictado, Voz y Acciones
    path('api/pris/dictado/resultado/', api_dictado_resultado, name='pris_dictado_resultado'),
    path('api/pris/dictado/inventario/', api_dictado_inventario, name='pris_dictado_inventario'),
    path('api/pris/dictado/buscar/', api_dictado_busqueda, name='pris_dictado_busqueda'),
    path('api/pris/dictado/validar-orden/', api_dictado_validar_orden, name='pris_dictado_validar_orden'),
    path('api/pris/ocr/', api_ocr_documento, name='pris_ocr_documento'),
    path('api/pris/archivo-raw/', api_crear_archivo_raw, name='pris_crear_archivo_raw'),
    path('api/pris/consulta-voz/', api_consulta_voz, name='pris_consulta_voz'),
    path('api/pris/hoja-trabajo/', api_generar_hoja_trabajo, name='pris_hoja_trabajo'),
    path('api/pris/alerta-clinica/', api_crear_alerta_clinica, name='pris_alerta_clinica'),
    path('api/pris/coach-toma-muestra/', api_coach_toma_muestra, name='pris_coach_toma_muestra'),
    path('api/pris/accion/<int:accion_id>/confirmar/', api_confirmar_accion, name='pris_jarvis_confirmar'),
    path('api/pris/accion/<int:accion_id>/rechazar/', api_rechazar_accion, name='pris_jarvis_rechazar'),

    # 7A. MÓDULO IA AVANZADO (OCR, Voz, Gemini)
    path('ia/', include(('ia.urls', 'ia'), namespace='ia')),
]
