"""
Re-exporta todas las vistas del módulo consultorio para que urls.py
siga funcionando con `from . import views` sin cambios.
"""

from .recepcion import (
    tablero_recepcion,
    check_in_cita,
    agendar_cita,
)

from .triage import (
    lista_triage,
    captura_signos_vitales,
)

from .clinico import (
    lista_trabajo_medico,
    consulta_sin_cita,
    nueva_consulta_soap,
    nueva_consulta_simplificada,
    nueva_consulta_con_paciente,
)

from .historial import (
    historial_clinico_paciente,
    dashboard_consultorio,
    ver_consulta_detalle,
)

from .certificados import (
    generar_certificado,
    ver_certificado,
)

from .api_consulta import (
    api_crear_consulta_directa,
    api_crear_paciente_y_consulta,
    api_buscar_pacientes,
    api_analizar_transcripcion,
    api_generar_receta_inmediata,
    api_generar_certificado_inmediato,
    api_generar_orden_laboratorio_inmediata,
    archivos_paciente,
    api_subir_archivo,
    api_eliminar_archivo,
    api_buscar_vademecum,
    api_signos_vitales_tendencia,
    api_plantillas_especialidad,
    api_usar_plantilla,
    api_resultados_disponibles,
)

from .cobros import (
    cobro_consulta,
    api_registrar_cobro,
    api_liquidar_vale,
    reporte_liquidacion,
)

from .reportes import (
    analisis_patrones,
    api_generar_analisis_patron,
    lista_espera,
    api_agregar_lista_espera,
    vademecum_lista,
    historial_signos_vitales,
    agenda_medico,
    triaje_pre_cita,
    campanas_marketing,
    encuestas_satisfaccion,
    seguimiento_tratamiento,
    reportes_productividad,
    configuracion_medico,
    crear_paciente_express,
)

from .videollamada import (
    videollamada_segura,
    api_crear_sala_videollamada,
)

from .sentinel import (
    sentinel_dashboard,
    sentinel_ssh_guide,
    sentinel_detalle,
    api_sentinel_feedback,
    api_sentinel_exportar_cursor,
    api_sentinel_ssh,
    api_test_github_sentinel,
    api_resolver_incidencias_sentinel,
    api_sentinel_listar_feedback,
)
