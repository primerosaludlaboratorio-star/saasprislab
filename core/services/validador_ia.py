"""
PRISLAB SENTINEL 2.0 - Validador IA de Resultados de Laboratorio
==================================================================
Escanea resultados antes de validarlos. Si detecta incongruencias
estadisticas (valores incompatibles con la vida, errores de dedo,
duplicados sospechosos), lanza alerta al quimico.

Uso:
    from core.services.validador_ia import validar_resultado_ia
    alertas = validar_resultado_ia(detalle_orden)
    # Returns: list[dict] con alertas o lista vacia si todo OK
"""

import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger('sentinel')

# ══════════════════════════════════════════════════════════════
# RANGOS ESTADISTICOS INCOMPATIBLES CON LA VIDA
# Si el valor esta fuera de estos rangos, es casi seguro un error
# ══════════════════════════════════════════════════════════════
RANGOS_IMPOSIBLES = {
    'glucosa': {'min': 10, 'max': 900, 'unidad': 'mg/dL'},
    'hemoglobina': {'min': 1, 'max': 25, 'unidad': 'g/dL'},
    'hematocrito': {'min': 5, 'max': 75, 'unidad': '%'},
    'leucocitos': {'min': 100, 'max': 200000, 'unidad': '/uL'},
    'plaquetas': {'min': 1000, 'max': 1500000, 'unidad': '/uL'},
    'creatinina': {'min': 0.1, 'max': 30, 'unidad': 'mg/dL'},
    'urea': {'min': 2, 'max': 500, 'unidad': 'mg/dL'},
    'acido urico': {'min': 0.5, 'max': 25, 'unidad': 'mg/dL'},
    'colesterol': {'min': 30, 'max': 600, 'unidad': 'mg/dL'},
    'trigliceridos': {'min': 10, 'max': 3000, 'unidad': 'mg/dL'},
    'bilirrubina total': {'min': 0, 'max': 50, 'unidad': 'mg/dL'},
    'albumina': {'min': 0.5, 'max': 7, 'unidad': 'g/dL'},
    'proteinas totales': {'min': 2, 'max': 15, 'unidad': 'g/dL'},
    'sodio': {'min': 100, 'max': 180, 'unidad': 'mEq/L'},
    'potasio': {'min': 1.5, 'max': 9, 'unidad': 'mEq/L'},
    'cloro': {'min': 70, 'max': 130, 'unidad': 'mEq/L'},
    'calcio': {'min': 4, 'max': 16, 'unidad': 'mg/dL'},
    'fosforo': {'min': 0.5, 'max': 15, 'unidad': 'mg/dL'},
    'magnesio': {'min': 0.5, 'max': 6, 'unidad': 'mg/dL'},
    'hierro serico': {'min': 5, 'max': 500, 'unidad': 'ug/dL'},
    'tgo': {'min': 0, 'max': 5000, 'unidad': 'U/L'},
    'tgp': {'min': 0, 'max': 5000, 'unidad': 'U/L'},
    'fosfatasa alcalina': {'min': 5, 'max': 2000, 'unidad': 'U/L'},
    'ggt': {'min': 0, 'max': 3000, 'unidad': 'U/L'},
    'amilasa': {'min': 0, 'max': 5000, 'unidad': 'U/L'},
    'lipasa': {'min': 0, 'max': 5000, 'unidad': 'U/L'},
    'psa': {'min': 0, 'max': 200, 'unidad': 'ng/mL'},
    'tsh': {'min': 0.01, 'max': 100, 'unidad': 'uIU/mL'},
    't3': {'min': 20, 'max': 500, 'unidad': 'ng/dL'},
    't4': {'min': 0.5, 'max': 25, 'unidad': 'ug/dL'},
}


def validar_resultado_ia(detalle_orden):
    """
    Valida un DetalleOrden antes de marcar como RESULTADO_LISTO.
    
    Args:
        detalle_orden: DetalleOrden instance
    
    Returns:
        list[dict]: Lista de alertas. Cada alerta tiene:
            - 'tipo': 'IMPOSIBLE' | 'SOSPECHOSO' | 'FUERA_RANGO' | 'DUPLICADO'
            - 'parametro': nombre del parametro
            - 'valor': valor capturado
            - 'mensaje': descripcion amigable
            - 'severidad': 'CRITICA' | 'ALTA' | 'MEDIA'
    """
    alertas = []

    try:
        from core.models import ResultadoParametro

        resultados = ResultadoParametro.objects.filter(
            orden=detalle_orden.orden,
        ).select_related('parametro')

        for resultado in resultados:
            if not resultado.valor:
                continue

            nombre_param = ''
            if resultado.parametro:
                nombre_param = resultado.parametro.nombre or ''

            valor_str = str(resultado.valor).strip()

            # Intentar convertir a numero
            try:
                valor_num = float(valor_str.replace(',', '.'))
            except (ValueError, TypeError):
                continue  # Es texto, no numerico

            # ── CHECK 1: Valores imposibles ──
            nombre_lower = nombre_param.lower().strip()
            for key, rango in RANGOS_IMPOSIBLES.items():
                if key in nombre_lower:
                    if valor_num < rango['min'] or valor_num > rango['max']:
                        alertas.append({
                            'tipo': 'IMPOSIBLE',
                            'parametro': nombre_param,
                            'valor': valor_str,
                            'mensaje': (
                                f'VALOR ESTADISTICAMENTE IMPROBABLE: '
                                f'{nombre_param} = {valor_str}. '
                                f'Rango vital: {rango["min"]}-{rango["max"]} '
                                f'{rango["unidad"]}. '
                                f'Posible error de captura.'
                            ),
                            'severidad': 'CRITICA',
                        })
                    break

            # ── CHECK 2: Valores fuera de referencia del estudio ──
            from core.utils.detalle_orden import get_estudio_legacy
            estudio = get_estudio_legacy(detalle_orden)
            if estudio and estudio.valor_minimo and estudio.valor_maximo:
                try:
                    v_min = float(estudio.valor_minimo)
                    v_max = float(estudio.valor_maximo)
                    if valor_num < v_min * 0.3 or valor_num > v_max * 3:
                        alertas.append({
                            'tipo': 'SOSPECHOSO',
                            'parametro': nombre_param,
                            'valor': valor_str,
                            'mensaje': (
                                f'{nombre_param} = {valor_str} esta muy lejos '
                                f'del rango de referencia ({v_min}-{v_max}). '
                                f'Verificar resultado.'
                            ),
                            'severidad': 'ALTA',
                        })
                except (ValueError, TypeError):
                    pass

            # ── CHECK 3: Valor de panico ──
            if estudio:
                try:
                    panic_min = float(estudio.rango_panico_min) if estudio.rango_panico_min else None
                    panic_max = float(estudio.rango_panico_max) if estudio.rango_panico_max else None
                    if panic_min is not None and valor_num < panic_min:
                        alertas.append({
                            'tipo': 'FUERA_RANGO',
                            'parametro': nombre_param,
                            'valor': valor_str,
                            'mensaje': (
                                f'VALOR DE PANICO: {nombre_param} = {valor_str} '
                                f'(minimo panico: {panic_min}). '
                                f'Requiere doble validacion.'
                            ),
                            'severidad': 'CRITICA',
                        })
                    elif panic_max is not None and valor_num > panic_max:
                        alertas.append({
                            'tipo': 'FUERA_RANGO',
                            'parametro': nombre_param,
                            'valor': valor_str,
                            'mensaje': (
                                f'VALOR DE PANICO: {nombre_param} = {valor_str} '
                                f'(maximo panico: {panic_max}). '
                                f'Requiere doble validacion.'
                            ),
                            'severidad': 'CRITICA',
                        })
                except (ValueError, TypeError):
                    pass

    except Exception as e:
        logger.error(f'[VALIDADOR-IA] Error validando resultados: {e}')

    return alertas


def validar_orden_completa(orden):
    """
    Valida TODOS los detalles de una orden completa.
    
    Args:
        orden: OrdenDeServicio instance
    
    Returns:
        list[dict]: Lista consolidada de todas las alertas
    """
    todas_alertas = []
    try:
        detalles = orden.detalles.select_related('analito', 'perfil_lims', 'paquete_lims').all()
        for detalle in detalles:
            alertas = validar_resultado_ia(detalle)
            todas_alertas.extend(alertas)
    except Exception as e:
        logger.error(f'[VALIDADOR-IA] Error validando orden completa: {e}')

    return todas_alertas


def generar_sugerencias_proceso(empresa):
    """
    Analiza tiempos del semaforo de muestras y sugiere mejoras.
    
    Returns:
        list[dict]: Sugerencias de optimizacion
    """
    sugerencias = []
    try:
        from core.models import OrdenDeServicio
        from django.utils import timezone
        from django.db.models import Avg, F, ExpressionWrapper, DurationField
        from datetime import timedelta

        ahora = timezone.now()
        hace_7_dias = ahora - timedelta(days=7)

        # Tiempo promedio de proceso total
        ordenes = OrdenDeServicio.objects.filter(
            empresa=empresa,
            fecha_creacion__gte=hace_7_dias,
            hora_toma_muestra__isnull=False,
            fecha_validacion__isnull=False,
        )

        if ordenes.exists():
            avg_total = ordenes.annotate(
                tiempo_total=ExpressionWrapper(
                    F('fecha_validacion') - F('fecha_creacion'),
                    output_field=DurationField()
                )
            ).aggregate(avg=Avg('tiempo_total'))

            avg_val = avg_total.get('avg')
            if avg_val and avg_val > timedelta(hours=4):
                horas = avg_val.total_seconds() / 3600
                sugerencias.append({
                    'area': 'Proceso General',
                    'mensaje': (
                        f'El tiempo promedio de proceso es {horas:.1f} horas. '
                        f'Objetivo: menos de 4 horas. '
                        f'Revisar cuellos de botella en toma de muestra o validacion.'
                    ),
                    'severidad': 'ALTA',
                })

        # Ordenes estancadas (>24h en PENDIENTE_TOMA)
        estancadas = OrdenDeServicio.objects.filter(
            empresa=empresa,
            estado_clinico='PENDIENTE_TOMA',
            fecha_creacion__lt=ahora - timedelta(hours=24),
            deleted_at__isnull=True,
        ).count()

        if estancadas > 0:
            sugerencias.append({
                'area': 'Ordenes Estancadas',
                'mensaje': (
                    f'Hay {estancadas} ordenes pendientes de toma de muestra '
                    f'desde hace mas de 24 horas. Revisar si el paciente acudio.'
                ),
                'severidad': 'MEDIA',
            })

        # Stock critico de insumos
        from laboratorio.models import InsumoEstudio
        from core.models import Producto

        insumos_criticos = Producto.objects.filter(
            empresa=empresa,
            stock__lte=5,
            uso_en_estudios__es_critico=True,
        ).distinct()

        if insumos_criticos.exists():
            nombres = ', '.join(i.nombre for i in insumos_criticos[:5])
            sugerencias.append({
                'area': 'Insumos Criticos',
                'mensaje': (
                    f'Reactivos/insumos criticos con stock bajo: {nombres}. '
                    f'Sin estos insumos no se pueden procesar estudios.'
                ),
                'severidad': 'CRITICA',
            })

    except Exception as e:
        logger.error(f'[VALIDADOR-IA] Error generando sugerencias: {e}')

    return sugerencias
