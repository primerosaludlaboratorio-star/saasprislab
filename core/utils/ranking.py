"""
Utilidades para calcular el ranking de desempeño de empleados.
"""
import logging

from django.utils import timezone
from django.db.models import Count, Avg, Q, Sum
from datetime import datetime, timedelta
from decimal import Decimal
from core.models import Usuario, Venta, OrdenDeServicio, IncidenciaOperativa, BuzonQuejas

logger = logging.getLogger(__name__)


def calcular_score_empleado(user_id, periodo_mes=None, periodo_anio=None):
    """
    Calcula el score de desempeño de un empleado basado en:
    - Velocidad: (Volumen de órdenes atendidas / Tiempo promedio)
    - Integridad: (Total acciones - Incidencias registradas)
    - Satisfacción: (Promedio de estrellas en el Buzón de Calidad)
    
    Args:
        user_id: ID del usuario/empleado
        periodo_mes: Mes a evaluar (1-12), None para mes actual
        periodo_anio: Año a evaluar, None para año actual
    
    Returns:
        dict con:
            - score_total: Puntaje total (0-100)
            - velocidad: Score de velocidad (0-100)
            - integridad: Score de integridad (0-100)
            - satisfaccion: Score de satisfacción (0-100)
            - volumen_ordenes: Número de órdenes/ventas atendidas
            - tiempo_promedio: Tiempo promedio por orden (minutos)
            - total_acciones: Total de acciones realizadas
            - incidencias: Número de incidencias registradas
            - fortalezas: Lista de fortalezas detectadas
    """
    try:
        usuario = Usuario.objects.get(id=user_id)
        empresa = usuario.empresa
        
        # Determinar periodo
        if periodo_mes is None or periodo_anio is None:
            hoy = timezone.now().date()
            periodo_mes = hoy.month
            periodo_anio = hoy.year
        
        inicio_mes = timezone.make_aware(datetime(periodo_anio, periodo_mes, 1))
        if periodo_mes == 12:
            fin_mes = timezone.make_aware(datetime(periodo_anio + 1, 1, 1))
        else:
            fin_mes = timezone.make_aware(datetime(periodo_anio, periodo_mes + 1, 1))
        
        # ======================================================================
        # 1. VELOCIDAD: Volumen de órdenes atendidas / Tiempo promedio
        # ======================================================================
        # Ventas de farmacia
        ventas = Venta.objects.filter(
            empresa=empresa,
            usuario=usuario,
            fecha__range=(inicio_mes, fin_mes),
            estado='COMPLETADA'
        )
        volumen_ventas = ventas.count()
        
        # Órdenes de laboratorio
        ordenes = OrdenDeServicio.objects.filter(
            empresa=empresa,
            responsable_ingreso=usuario,
            fecha_creacion__range=(inicio_mes, fin_mes)
        ).exclude(estado='CANCELADO')
        volumen_ordenes = ordenes.count()
        
        volumen_total = volumen_ventas + volumen_ordenes
        
        # Calcular tiempo promedio (simplificado: asumir 5 min por venta, 10 min por orden)
        # En producción, esto se calcularía con timestamps reales
        tiempo_total_estimado = (volumen_ventas * 5) + (volumen_ordenes * 10)
        tiempo_promedio = tiempo_total_estimado / volumen_total if volumen_total > 0 else 0
        
        # Score de velocidad (más volumen y menos tiempo = mejor)
        # Normalizar: 0-100 puntos
        # Base: 50 puntos por volumen, 50 puntos por eficiencia
        velocidad_score = 0
        if volumen_total > 0:
            # Puntos por volumen (máximo 50 puntos)
            volumen_score = min(50, (volumen_total / 100) * 50)  # 100 órdenes = 50 puntos
            
            # Puntos por eficiencia (máximo 50 puntos)
            # Menos tiempo promedio = más puntos
            if tiempo_promedio > 0:
                eficiencia_score = max(0, 50 - (tiempo_promedio / 20) * 50)  # 20 min = 0 puntos, 0 min = 50 puntos
            else:
                eficiencia_score = 50
            
            velocidad_score = volumen_score + eficiencia_score
        
        # ======================================================================
        # 2. INTEGRIDAD: Total acciones - Incidencias registradas
        # ======================================================================
        total_acciones = volumen_total
        
        incidencias = IncidenciaOperativa.objects.filter(
            empresa=empresa,
            usuario_responsable=usuario,
            fecha_hora__range=(inicio_mes, fin_mes)
        ).count()
        
        # Score de integridad: menos incidencias = mejor
        # Base: 100 puntos, -10 puntos por incidencia
        integridad_score = max(0, 100 - (incidencias * 10))
        
        # ======================================================================
        # 3. SATISFACCIÓN: Promedio de estrellas en el Buzón de Calidad
        # ======================================================================
        # Nota: El modelo BuzonQuejas no tiene campo de estrellas actualmente
        # Por ahora, usaremos felicitaciones como proxy de satisfacción
        felicitaciones = BuzonQuejas.objects.filter(
            empresa=empresa,
            tipo='FELICITACION',
            fecha_creacion__range=(inicio_mes, fin_mes)
        ).count()
        
        quejas = BuzonQuejas.objects.filter(
            empresa=empresa,
            tipo='QUEJA',
            fecha_creacion__range=(inicio_mes, fin_mes)
        ).count()
        
        # Score de satisfacción basado en ratio felicitaciones/quejas
        # Si hay felicitaciones y no hay quejas: 100 puntos
        # Si hay quejas: penalización
        if felicitaciones > 0 and quejas == 0:
            satisfaccion_score = 100
        elif felicitaciones > quejas:
            satisfaccion_score = 80
        elif felicitaciones == quejas:
            satisfaccion_score = 50
        elif quejas > 0:
            satisfaccion_score = max(0, 50 - (quejas * 10))
        else:
            satisfaccion_score = 50  # Neutral si no hay feedback
        
        # ======================================================================
        # SCORE TOTAL: Promedio ponderado
        # ======================================================================
        # Ponderación: Velocidad 40%, Integridad 40%, Satisfacción 20%
        score_total = (
            velocidad_score * 0.40 +
            integridad_score * 0.40 +
            satisfaccion_score * 0.20
        )
        
        # ======================================================================
        # FORTALEZAS: Detectar fortalezas del empleado
        # ======================================================================
        fortalezas = []
        
        if volumen_total >= 50:
            fortalezas.append('El más productivo')
        if tiempo_promedio < 5 and volumen_total > 0:
            fortalezas.append('El más rápido')
        if incidencias == 0 and total_acciones > 0:
            fortalezas.append('Cero errores')
        if felicitaciones > quejas * 2:
            fortalezas.append('Excelente servicio')
        if integridad_score >= 90:
            fortalezas.append('Alta integridad')
        
        if not fortalezas:
            fortalezas.append('Desempeño estándar')
        
        return {
            'score_total': round(score_total, 2),
            'velocidad': round(velocidad_score, 2),
            'integridad': round(integridad_score, 2),
            'satisfaccion': round(satisfaccion_score, 2),
            'volumen_ordenes': volumen_total,
            'tiempo_promedio': round(tiempo_promedio, 2),
            'total_acciones': total_acciones,
            'incidencias': incidencias,
            'felicitaciones': felicitaciones,
            'quejas': quejas,
            'fortalezas': fortalezas,
            'volumen_ventas': volumen_ventas,
            'volumen_ordenes_lab': volumen_ordenes,
        }
        
    except Usuario.DoesNotExist:
        return {
            'score_total': 0,
            'velocidad': 0,
            'integridad': 0,
            'satisfaccion': 0,
            'volumen_ordenes': 0,
            'tiempo_promedio': 0,
            'total_acciones': 0,
            'incidencias': 0,
            'felicitaciones': 0,
            'quejas': 0,
            'fortalezas': ['Sin datos'],
            'volumen_ventas': 0,
            'volumen_ordenes_lab': 0,
        }
    except Exception as e:
        logger.error('Error al calcular score para usuario %s: %s', user_id, e, exc_info=True)
        return {
            'score_total': 0,
            'velocidad': 0,
            'integridad': 0,
            'satisfaccion': 0,
            'volumen_ordenes': 0,
            'tiempo_promedio': 0,
            'total_acciones': 0,
            'incidencias': 0,
            'felicitaciones': 0,
            'quejas': 0,
            'fortalezas': ['Error en cálculo'],
            'volumen_ventas': 0,
            'volumen_ordenes_lab': 0,
        }


def calcular_tendencia(score_actual, score_mes_anterior):
    """
    Calcula la tendencia comparando el score actual con el del mes pasado.
    
    Returns:
        dict con:
            - tendencia: 'subio', 'bajo', 'igual'
            - diferencia: Diferencia numérica
            - porcentaje: Porcentaje de cambio
    """
    if score_mes_anterior == 0:
        return {
            'tendencia': 'nuevo',
            'diferencia': score_actual,
            'porcentaje': 0
        }
    
    diferencia = score_actual - score_mes_anterior
    porcentaje = (diferencia / score_mes_anterior) * 100 if score_mes_anterior > 0 else 0
    
    if diferencia > 2:  # Umbral de 2 puntos para considerar cambio significativo
        tendencia = 'subio'
    elif diferencia < -2:
        tendencia = 'bajo'
    else:
        tendencia = 'igual'
    
    return {
        'tendencia': tendencia,
        'diferencia': round(diferencia, 2),
        'porcentaje': round(porcentaje, 2)
    }
