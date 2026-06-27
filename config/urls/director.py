from django.urls import path
from core import views
from core.views.administracion_usuarios import gestionar_usuarios
from core.views import sucursal_modo_inventario_lab as sucursal_inv_lab_views
from core.views.configuracion import (
    configuracion_empresa,
    api_ia_consumo,
    api_cambiar_modo_ia,
    api_guardar_byok,
)
from core.views.feature_flags_admin import (
    panel_feature_flags,
    api_toggle_flag,
    api_flags_estado,
)
from core.views.audio_legal import (
    api_verificar_integridad_audio,
    api_sellar_audio,
)
from core.views.war_room import war_room, api_war_room_anomalias
from core.views.director import (
    director_analizadores,
    director_analizadores_crear,
    director_analizadores_toggle,
    director_analizadores_mapeos,
    director_analizadores_probar_conexion,
    director_analizadores_eliminar_mapeo,
)

urlpatterns = [
    # 7. MÓDULO CONFIGURACIÓN Y ADMINISTRACIÓN
    path('configuracion/', views.configuracion_dashboard, name='configuracion_dashboard'),
    path('configuracion/empresa/', configuracion_empresa, name='configuracion_empresa'),
    path('configuracion/usuarios/', gestionar_usuarios, name='gestionar_usuarios'),

    # Feature Flags — Interruptores del Director
    path('configuracion/flags/', panel_feature_flags, name='panel_feature_flags'),
    path('configuracion/flags/<str:codigo>/toggle/', api_toggle_flag, name='api_toggle_flag'),
    path('api/flags/estado/', api_flags_estado, name='api_flags_estado'),

    # Gobernanza IA (BYOK / consumo / modo)
    path('api/ia/consumo/', api_ia_consumo, name='api_ia_consumo'),
    path('api/ia/modo/', api_cambiar_modo_ia, name='api_cambiar_modo_ia'),
    path('api/ia/byok/', api_guardar_byok, name='api_guardar_byok'),

    # Audio Legal — verificación de integridad de transcripciones
    path('api/audio/verificar-integridad/<int:registro_id>/', api_verificar_integridad_audio, name='api_verificar_integridad_audio'),
    path('api/audio/sellar/', api_sellar_audio, name='api_sellar_audio'),

    # IA Dashboard
    path('ia/panel/', views.ia_dashboard, name='ia_dashboard'),
    path('api/ia/chat/', views.api_ia_chat, name='api_ia_chat'),
    path('api/ia/consultar-negocios/', views.api_ia_consultar_negocios, name='api_ia_consultar_negocios'),
    path('api/ia/diagnostico/', views.api_ia_diagnostico, name='api_ia_diagnostico'),

    # Director principal
    path('director/', views.dashboard_director, name='dashboard_director'),
    path('director/sucursales/modo-inventario-lab/', sucursal_inv_lab_views.sucursales_modo_inventario_lab, name='sucursales_modo_inventario_lab'),

    # 7B. MÓDULO CRECIMIENTO Y CONTROL GERENCIAL
    path('director/coach/', views.coach_ejecutivo, name='coach_ejecutivo'),
    path('director/coach/api/preguntar/', views.api_coach_preguntar, name='api_coach_preguntar'),
    path('director/buzon/', views.buzon_kanban, name='buzon_kanban'),
    path('reporte-friccion/', views.reporte_friccion, name='reporte_friccion'),
    path('api/pris-ayuda/', views.api_pris_ayuda, name='api_pris_ayuda'),
    path('director/calidad/', views.buzon_kanban, name='dashboard_calidad'),
    path('director/biblioteca/', views.biblioteca_liderazgo, name='biblioteca_liderazgo'),
    path('director/biblioteca/agregar/', views.agregar_libro, name='agregar_libro'),
    path('director/biblioteca/api/cambiar-estado/<int:libro_id>/', views.api_cambiar_estado_libro, name='api_cambiar_estado_libro'),
    path('director/buzon/api/cambiar-estado/<int:queja_id>/', views.api_cambiar_estado_queja, name='api_cambiar_estado_queja'),
    path('director/buzon/api/obtener/', views.api_obtener_quejas, name='api_obtener_quejas'),
    path('tu-opinion/', views.tu_opinion, name='tu_opinion'),

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

    # 24. WAR ROOM — Dashboard de Excepciones del Director
    path('director/war-room/', war_room, name='war_room'),
    path('director/war-room/api/anomalias/', api_war_room_anomalias, name='api_war_room_anomalias'),

    # 24b. GESTIÓN DE ANALIZADORES — Director
    path('director/analizadores/', director_analizadores, name='director_analizadores'),
    path('director/analizadores/crear/', director_analizadores_crear, name='director_analizadores_crear'),
    path('director/analizadores/<int:equipo_id>/toggle/', director_analizadores_toggle, name='director_analizadores_toggle'),
    path('director/analizadores/<int:equipo_id>/mapeos/', director_analizadores_mapeos, name='director_analizadores_mapeos'),
    path('director/analizadores/probar-conexion/', director_analizadores_probar_conexion, name='director_analizadores_probar_conexion'),
    path('director/analizadores/mapeo/<int:mapeo_id>/eliminar/', director_analizadores_eliminar_mapeo, name='director_analizadores_eliminar_mapeo'),
]
