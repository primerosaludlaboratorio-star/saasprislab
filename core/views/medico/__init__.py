"""
core/views/medico/__init__.py
Re-exporta todas las vistas del módulo médico.
core/views/__init__.py hace `from .medico import *` — este archivo mantiene esa compatibilidad.
"""
from .consulta import consulta_medica, verificar_existencia_farmacia
from .receta import (
    ver_receta_medica,
    generar_pdf_receta,
    calcular_hash_verificacion_receta,
    verificar_qr_receta,
)
from .ultrasonido import lista_trabajo_usg, captura_reporte_usg, descargar_pdf_ultrasonido

__all__ = [
    'consulta_medica',
    'verificar_existencia_farmacia',
    'ver_receta_medica',
    'generar_pdf_receta',
    'calcular_hash_verificacion_receta',
    'verificar_qr_receta',
    'lista_trabajo_usg',
    'captura_reporte_usg',
    'descargar_pdf_ultrasonido',
]
