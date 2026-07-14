# Resumen de inventario de URLs/API

- Total de rutas: 1812
- Rutas no-admin: 769
- Protocolo: PRISLAB_URL_INVENTORY
- OK: True

## Distribución por tipo

| Tipo | Cantidad |
|------|----------|
| ui | 1544 |
| api | 252 |
| pdf | 16 |

## Distribución por segmento raíz

| Segmento | Cantidad |
|----------|----------|
| /admin | 1043 |
| /laboratorio | 118 |
| /consultorio | 68 |
| /api | 61 |
| /farmacia | 53 |
| /silo-lab | 50 |
| /lims | 42 |
| /mantenimiento | 32 |
| /director | 24 |
| /bienestar | 21 |
| /pacientes | 18 |
| /contabilidad | 17 |
| /marketing | 16 |
| /seguridad | 15 |
| /ia | 14 |
| /pris | 14 |
| /crm | 14 |
| /medico | 14 |
| /finanzas | 13 |
| /logistica | 11 |
| /capacitacion | 10 |
| /rh | 10 |
| /notificaciones | 9 |
| /nomina | 9 |
| /asistencia | 8 |
| /reportes | 8 |
| /recepcion | 7 |
| /iot | 7 |
| /cotizacion | 6 |
| /blindaje | 6 |
| /transferencias | 6 |
| /enfermeria | 6 |
| /chat | 6 |
| /inventario | 4 |
| /configuracion | 4 |
| /catalogos | 4 |
| /historial-resultados | 4 |
| /onboarding | 4 |
| /auth | 3 |
| /analytics | 3 |

## Muestra de rutas no-admin

| Ruta | Nombre | View | Tipo |
|------|--------|------|------|
| `/favicon.ico` | - | `django.views.generic.base.RedirectView` | ui |
| `/media/logos/LOGO_PRISLAB.png` | - | `django.views.generic.base.RedirectView` | ui |
| `/` | login_root | `core.views.general.CustomLoginView` | ui |
| `/login/` | login | `core.views.general.CustomLoginView` | ui |
| `/logout/` | logout | `core.views.general.logout_view` | ui |
| `/auth/2fa/verificar/` | verificar_2fa | `core.views.autenticacion_2fa.verificar_2fa` | ui |
| `/auth/2fa/configurar/` | setup_2fa | `core.views.autenticacion_2fa.setup_2fa` | ui |
| `/auth/2fa/desactivar/` | desactivar_2fa | `core.views.autenticacion_2fa.desactivar_2fa` | ui |
| `/api/iot/hl7/` | hl7_receptor | `core.services.lims.interfaces_lims_service.receptor_hl7` | api |
| `/api/v3/openapi.json` | openapi-json | `ninja.openapi.views.openapi_json` | api |
| `/api/v3/docs` | openapi-view | `ninja.openapi.views.openapi_view` | api |
| `/api/v3/farmacia/pdv/productos` | buscar_productos_pdv_v3 | `ninja.operation.PathView.get_view.<locals>.sync_view_wrapper` | api |
| `/api/v3/farmacia/pdv/cobrar` | farmacia_pdv_cobrar_v3 | `ninja.operation.PathView.get_view.<locals>.sync_view_wrapper` | api |
| `/api/v3/lims/resultados/captura` | lims_resultados_captura_v3 | `ninja.operation.PathView.get_view.<locals>.sync_view_wrapper` | api |
| `/api/v3/` | api-root | `ninja.openapi.views.default_home` | api |
| `/api/lab/imprimir-zpl/<int:orden_id>/` | imprimir_zpl | `laboratorio.views.imprimir_zpl.imprimir_etiqueta_zpl` | api |
| `/api/lab/imprimir-zpl/lote/` | imprimir_zpl_lote | `laboratorio.views.imprimir_zpl.imprimir_etiquetas_lote_zpl` | api |
| `/kiosko/` | kiosko_index | `laboratorio.views.imprimir_zpl.kiosko_index` | ui |
| `/kiosko/check-in/<str:qr_token>/` | kiosko_check_in | `laboratorio.views.imprimir_zpl.kiosko_check_in_qr` | ui |
| `/api/caja/corte-unificado/` | corte_caja_unificado | `farmacia.views.corte_caja_api.api_corte_caja_unificado` | api |
| `/bienestar/` | bienestar_dashboard | `core.views.bienestar.dashboard_bienestar` | ui |
| `/bienestar/diario/` | diario_emocional | `core.views.bienestar.diario_emocional` | ui |
| `/bienestar/nom035/` | evaluacion_nom035 | `core.views.bienestar.evaluacion_nom035` | ui |
| `/bienestar/alertas-rrhh/` | bienestar_alertas_rrhh | `core.views.bienestar.alertas_rrhh` | ui |
| `/home/` | home | `core.views.general.home_view` | ui |
| `/dashboard/` | dashboard | `core.views.director.dashboard_director` | ui |
| `/validar/resultado/<uuid:token>/` | validar_resultado | `core.views.laboratorio_reportes.validar_resultado` | ui |
| `/api/push/vapid/` | push_vapid_key | `core.views.push.obtener_vapid_key` | api |
| `/api/push/suscribir/` | push_suscribir | `core.views.push.suscribir_push` | api |
| `/api/push/desuscribir/` | push_desuscribir | `core.views.push.desuscribir_push` | api |
| `/api/push/estado/` | push_estado | `core.views.push.estado_suscripciones` | api |
| `/api/push/test/` | push_test | `core.views.push.test_notificacion` | api |
| `/api/voice/process/` | voice_process | `core.views.voice.procesar_comando_api` | api |
| `/api/voice/history/` | voice_history | `core.views.voice.historial_comandos` | api |
| `/api/voice/verify-auth/` | voice_verify_auth | `core.views.voice.verificar_webauthn` | api |
| `/voice/logs/` | voice_logs_dashboard | `core.views.voice.dashboard_voice_logs` | ui |
| `/ia/asistente/` | pris_ia_asistente | `core.views.pris_ia.asistente_page` | ui |
| `/ia/asistente/chat/` | pris_ia_chat | `core.views.pris_ia.asistente_chat` | ui |
| `/ia/asistente/reset/` | pris_ia_reset | `core.views.pris_ia.asistente_reset` | ui |
| `/api/prisci/webhook/` | prisci_webhook | `core.views.prisci_webhook.webhook` | api |
| `/api/prisci/webhook/verify/` | prisci_webhook_verify | `core.views.prisci_webhook.verify` | api |
| `/pris/api/acciones/pendientes/` | pris_acciones_pendientes | `core.views.pris_ia.api_acciones_pendientes` | api |
| `/pris/api/accion/<int:accion_id>/confirmar/` | pris_confirmar_accion | `core.views.pris_ia.api_confirmar_accion` | api |
| `/pris/api/accion/<int:accion_id>/rechazar/` | pris_rechazar_accion | `core.views.pris_ia.api_rechazar_accion` | api |
| `/notificaciones/` | notificaciones_lista | `core.views.notificaciones.lista_notificaciones` | ui |
| `/notificaciones/badge/` | notificaciones_badge | `core.views.notificaciones.api_notificaciones_badge` | ui |
| `/notificaciones/<int:notificacion_id>/leer/` | notificacion_leer | `core.views.notificaciones.marcar_leida` | ui |
| `/notificaciones/marcar-todas/` | notificaciones_marcar_todas | `core.views.notificaciones.marcar_todas_leidas` | ui |
| `/api/notificaciones/crear/` | api_crear_notificacion | `core.views.notificaciones.api_crear_notificacion` | api |
| `/nomina/` | nomina_dashboard | `core.views.nomina.dashboard_nomina` | ui |