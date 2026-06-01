"""
Módulo de vistas refactorizado para PRISLAB SaaS.
Importa todas las vistas desde los submódulos especializados.
"""

# Importar todas las vistas para mantener compatibilidad
from .farmacia import *
from .laboratorio import *
from .finanzas import *
from .pacientes import *
from .catalogos import *
from .general import *
from .ia import *
from .ia_dashboard import *
from .rh import *
from .director import *
from .medico import *
from .cotizacion import *
from .bot import *
from .manual import *
from .cerebro import *
from .ai_brain import *
from .configuracion import *
from .operaciones import *
from .excepciones_lab import *
from .consulta_ordenes import consulta_ordenes, detalle_orden_view, api_detalle_orden_completo
from .comunicacion import *
from .expediente import *
from .coach import *
from .buzon import *
from .biblioteca import *
from .autorizaciones import *
from .incidencias import *
from .ranking import *
from .impresion import *
from .contabilidad import *
from .nomina import *
from .asistencia import *
from .historial_resultados import *
from .transferencias import *
from .reportes_financieros import *
from .crm import *
from .analytics import *
from .dashboard_unificado import *
from .notificaciones import *
from .entrega_resultados import *
from .consentimientos import *
from .maquila import *
from .capacitacion import *
from .reporte_friccion import *
from .capacitacion_rag import *
from .bienestar_mejorado import *
from .pris_jarvis import *
from .auditoria_campo import api_auditoria_campo
from .sentinel_api import api_shield_telemetry, api_sentinel_reset, api_sentinel_diagnostico
from .monitor_produccion import monitor_produccion, api_monitor_datos, api_avanzar_estado
from .omnisearch import api_omnisearch
from .cuentas_por_cobrar import *

# Exponer explícitamente las funciones de pre-órdenes desde laboratorio.py
from .laboratorio import api_preordenes_pendientes, api_cargar_preorden
