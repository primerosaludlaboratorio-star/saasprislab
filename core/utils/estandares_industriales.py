"""
Utilidades para implementar los Estándares Industriales PRISLAB v5.
Reglas de Varilla de Alta Resistencia (Basadas en Deltec/Velab).
"""
from django.utils import timezone
from django.contrib.auth import get_user_model
# NOTA: Modelo TrazabilidadOperacion pendiente de migración. Descomentar la importación cuando exista en DB.
# from core.models import TrazabilidadOperacion
from core.utils.trazabilidad import registrar_trazabilidad
from core.utils.detalle_orden import get_detalle_codigo
import json

Usuario = get_user_model()


def obtener_resultados_anteriores_paciente(paciente, empresa, codigo_estudio=None, limite=5):
    """
    REGLA 3: Sistema de Delta-Check
    Obtiene resultados anteriores del paciente para comparación.
    
    Args:
        paciente: Instancia de Paciente
        empresa: Instancia de Empresa
        codigo_estudio: Código del estudio (opcional, para filtrar)
        limite: Número máximo de órdenes a consultar
    
    Returns:
        dict: {codigo_estudio: {'valor': valor, 'fecha': fecha, 'folio': folio}}
    """
    from core.models import OrdenDeServicio
    
    resultados_anteriores = {}
    
    if not paciente:
        return resultados_anteriores
    
    # Buscar órdenes anteriores del mismo paciente con resultados validados
    ordenes_anteriores = OrdenDeServicio.objects.filter(
        empresa=empresa,
        paciente=paciente,
        estado='RESULTADOS_LISTOS'
    ).select_related('paciente').prefetch_related(
        'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
    ).order_by('-fecha_creacion')[:limite]
    
    # Extraer resultados por código de estudio (tomar el más reciente)
    for orden_ant in ordenes_anteriores:
        for detalle_ant in orden_ant.detalles.select_related('analito', 'perfil_lims', 'paquete_lims').all():
            codigo_estudio_actual = get_detalle_codigo(detalle_ant)
            if detalle_ant.resultado and codigo_estudio_actual:
                
                # Filtrar por código si se especifica
                if codigo_estudio and codigo_estudio_actual != codigo_estudio:
                    continue
                
                # Solo guardar si no existe ya (para tomar el más reciente)
                if codigo_estudio_actual not in resultados_anteriores:
                    # Intentar extraer valor numérico del resultado
                    resultado_texto = detalle_ant.resultado
                    valor_numerico = None
                    
                    # Buscar patrón numérico en el resultado
                    import re
                    match = re.search(r'(\d+\.?\d*)', resultado_texto)
                    if match:
                        try:
                            valor_numerico = float(match.group(1))
                        except (ValueError, TypeError):
                            pass
                    
                    resultados_anteriores[codigo_estudio_actual] = {
                        'valor': valor_numerico if valor_numerico is not None else resultado_texto,
                        'valor_texto': resultado_texto,
                        'fecha': orden_ant.fecha_creacion,
                        'folio': orden_ant.folio_orden or f'ORD-{orden_ant.id}'
                    }
    
    return resultados_anteriores


def auditar_cambio_campo(campo_nombre, valor_anterior, valor_nuevo, modelo_instancia, 
                         request, modulo='LABORATORIO', accion='UPDATE'):
    """
    REGLA 6: Auditoría Nativa
    Registra automáticamente un cambio en un campo crítico.
    
    Args:
        campo_nombre: Nombre del campo modificado
        valor_anterior: Valor antes del cambio
        valor_nuevo: Valor después del cambio
        modelo_instancia: Instancia del modelo modificado
        request: HttpRequest object
        modulo: Módulo donde ocurrió el cambio
        accion: Acción realizada (UPDATE, CREATE, DELETE)
    """
    try:
        registrar_trazabilidad(
            tipo_operacion='CAMPO_MODIFICADO',
            modulo=modulo,
            referencia_id=modelo_instancia.id,
            referencia_tipo=modelo_instancia.__class__.__name__,
            accion=accion,
            descripcion=f'Campo {campo_nombre} modificado',
            usuario=request.user,
            empresa=getattr(request.user, 'empresa', None),
            datos_anteriores={campo_nombre: valor_anterior},
            datos_nuevos={campo_nombre: valor_nuevo},
            request=request,
        )
    except Exception as e:
        # Log error pero no bloquear la operación
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error al registrar auditoría de campo {campo_nombre}: {e}')


def calcular_delta_porcentaje(valor_actual, valor_anterior):
    """
    REGLA 3: Sistema de Delta-Check
    Calcula el porcentaje de cambio entre dos valores.
    
    Args:
        valor_actual: Valor actual (float)
        valor_anterior: Valor anterior (float)
    
    Returns:
        dict: {
            'delta': diferencia absoluta,
            'porcentaje': porcentaje de cambio,
            'categoria': 'MENOR_10', 'ENTRE_10_20', 'MAYOR_20', 'MAYOR_30'
        }
    """
    if not valor_anterior or valor_anterior == 0:
        return {
            'delta': None,
            'porcentaje': None,
            'categoria': 'SIN_REFERENCIA'
        }
    
    try:
        valor_actual_float = float(valor_actual)
        valor_anterior_float = float(valor_anterior)
        
        delta = valor_actual_float - valor_anterior_float
        # Evitar división por cero cuando el valor anterior es 0
        porcentaje = ((delta / valor_anterior_float) * 100) if valor_anterior_float != 0 else 0.0
        
        if abs(porcentaje) > 30:
            categoria = 'MAYOR_30'
        elif abs(porcentaje) > 20:
            categoria = 'MAYOR_20'
        elif abs(porcentaje) > 10:
            categoria = 'ENTRE_10_20'
        else:
            categoria = 'MENOR_10'
        
        return {
            'delta': delta,
            'porcentaje': round(porcentaje, 1),
            'categoria': categoria
        }
    except (ValueError, TypeError, ZeroDivisionError):
        return {
            'delta': None,
            'porcentaje': None,
            'categoria': 'ERROR_CALCULO'
        }


def validar_rango_valor(valor, ref_min, ref_max):
    """
    REGLA 5: Integración de Jarvis (PRIS)
    Valida si un valor está dentro del rango de referencia.
    
    Args:
        valor: Valor a validar (float)
        ref_min: Valor mínimo de referencia (float o None)
        ref_max: Valor máximo de referencia (float o None)
    
    Returns:
        dict: {
            'dentro_rango': bool,
            'mensaje': str,
            'severidad': 'NORMAL', 'ADVERTENCIA', 'CRITICO'
        }
    """
    try:
        valor_float = float(valor)
        
        if ref_min is not None and ref_max is not None:
            if valor_float < ref_min or valor_float > ref_max:
                return {
                    'dentro_rango': False,
                    'mensaje': f'Valor fuera de rango ({ref_min}-{ref_max})',
                    'severidad': 'CRITICO'
                }
        elif ref_min is not None and valor_float < ref_min:
            return {
                'dentro_rango': False,
                'mensaje': f'Valor por debajo del mínimo ({ref_min})',
                'severidad': 'ADVERTENCIA'
            }
        elif ref_max is not None and valor_float > ref_max:
            return {
                'dentro_rango': False,
                'mensaje': f'Valor por encima del máximo ({ref_max})',
                'severidad': 'ADVERTENCIA'
            }
        
        return {
            'dentro_rango': True,
            'mensaje': 'Valor dentro de rango',
            'severidad': 'NORMAL'
        }
    except (ValueError, TypeError):
        return {
            'dentro_rango': False,
            'mensaje': 'Valor inválido',
            'severidad': 'CRITICO'
        }
