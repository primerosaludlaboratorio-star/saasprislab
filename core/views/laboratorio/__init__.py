"""
Shim de compatibilidad — re-exporta todas las vistas públicas del paquete
para que `from core.views.laboratorio import <vista>` siga funcionando.

Este archivo sustituye al monolito core/views/laboratorio.py.
"""
from ._helpers import (
    _convenio_desde_tarifa,
    _lims_line_key_detalle,
    _lims_line_key_row,
    _detalle_codigo_lista,
)

from .recepcion import (
    recepcion_lab,
    dashboard_laboratorio,
    api_buscar_estudios,
    api_listar_medicos,
    api_listar_convenios,
    api_precios_convenio,
    crear_orden_servicio,
    api_ordenes_recientes,
)

from .caja import (
    imprimir_ticket_lab,
    api_cobrar_orden,
    api_historial_pagos,
    api_cancelar_pago,
)

from .resultados import (
    registro_resultados_entrada,
    lista_trabajo_lab,
    api_guardar_resultados,
    api_preview_formulas_lims,
    api_estado_orden,
    api_bulk_validar,
    api_bulk_imprimir,
)

from .pdf_impresion import (
    imprimir_hoja_trabajo_pdf,
    abrir_worklist_qr,
    generar_qr_orden,
    imprimir_resultados_pdf,
    imprimir_etiquetas_lab,
)

from .calidad import (
    control_calidad,
    toma_muestra_index,
    api_toma_muestra,
    api_validar_pin,
    preparacion_toma,
    api_iniciar_toma,
    api_finalizar_toma,
    reporte_tiempos_proceso,
    parsear_tiempo_proceso,
    ORDEN_EXTRACCION_TUBOS,
    TUBO_INFO,
)

from .edicion_orden import (
    api_datos_orden,
    api_editar_datos_orden,
    api_editar_estudios_orden,
    api_preordenes_pendientes,
    api_cargar_preorden,
)

from .escaneo_ia import (
    escanear_receta_ia,
    escanear_identidad_ia,
    dashboard_pendientes,
)

from .pacientes_lab import (
    lista_pacientes_lab,
    historial_lab_paciente,
)

from .captura import (
    captura_resultados_industrial,
    registrar_notificacion_panico,
)

from .config_lims import (
    lista_pruebas,
    configurar_prueba,
    configurar_rangos,
    eliminar_prueba,
    duplicar_prueba,
    api_parametros_estudio,
    lista_parametros,
    editar_parametro,
    api_rangos_parametro,
    api_rango_detalle,
    api_soft_delete_parametro,
    api_buscar_parametros,
)

from .reportes import (
    imprimir_resultados,
    api_generar_y_guardar_reporte,
    validar_resultado,
)


__all__ = [
    # helpers
    '_convenio_desde_tarifa',
    '_lims_line_key_detalle',
    '_lims_line_key_row',
    '_detalle_codigo_lista',
    # recepcion
    'recepcion_lab',
    'dashboard_laboratorio',
    'api_buscar_estudios',
    'api_listar_medicos',
    'api_listar_convenios',
    'api_precios_convenio',
    'crear_orden_servicio',
    'api_ordenes_recientes',
    # caja
    'imprimir_ticket_lab',
    'api_cobrar_orden',
    'api_historial_pagos',
    'api_cancelar_pago',
    # resultados
    'registro_resultados_entrada',
    'lista_trabajo_lab',
    'api_guardar_resultados',
    'api_preview_formulas_lims',
    'api_estado_orden',
    'api_bulk_validar',
    'api_bulk_imprimir',
    # pdf_impresion
    'imprimir_hoja_trabajo_pdf',
    'abrir_worklist_qr',
    'generar_qr_orden',
    'imprimir_resultados_pdf',
    'imprimir_etiquetas_lab',
    # calidad
    'control_calidad',
    'toma_muestra_index',
    'api_toma_muestra',
    'api_validar_pin',
    'preparacion_toma',
    'api_iniciar_toma',
    'api_finalizar_toma',
    'reporte_tiempos_proceso',
    'parsear_tiempo_proceso',
    'ORDEN_EXTRACCION_TUBOS',
    'TUBO_INFO',
    # edicion_orden
    'api_datos_orden',
    'api_editar_datos_orden',
    'api_editar_estudios_orden',
    'api_preordenes_pendientes',
    'api_cargar_preorden',
    # escaneo_ia
    'escanear_receta_ia',
    'escanear_identidad_ia',
    'dashboard_pendientes',
    # pacientes_lab
    'lista_pacientes_lab',
    'historial_lab_paciente',
]
