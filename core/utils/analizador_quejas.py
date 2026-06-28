"""
Analizador Virtual de Quejas - IA para análisis automático de feedback.
Simula análisis inteligente y prepara estructura para conexión con Gemini/OpenAI.
"""
import re
from django.utils import timezone


def analizar_queja(mensaje, tipo='QUEJA'):
    """
    Analiza una queja/sugerencia y genera:
    - Sentimiento (Positivo, Neutro, Negativo, Crítico)
    - Categoría (Tiempos, Trato, Precios, Instalaciones, Limpieza)
    - Resumen de causa
    - Plan de acción sugerido
    
    Por ahora usa análisis por palabras clave, pero está preparado para IA real.
    """
    mensaje_lower = mensaje.lower()
    
    # ==============================================================================
    # ANÁLISIS DE SENTIMIENTO
    # ==============================================================================
    palabras_positivas = ['excelente', 'bueno', 'gracias', 'feliz', 'contento', 'satisfecho', 'bien', 'perfecto']
    palabras_negativas = ['mal', 'pésimo', 'horrible', 'terrible', 'decepcionado', 'molesto', 'furioso', 'enojado']
    palabras_criticas = ['demanda', 'demandar', 'abogado', 'procuraduría', 'profeco', 'queja formal', 'no regreso', 'nunca más']
    
    sentimiento = 'NEUTRO'
    contador_positivo = sum(1 for palabra in palabras_positivas if palabra in mensaje_lower)
    contador_negativo = sum(1 for palabra in palabras_negativas if palabra in mensaje_lower)
    contador_critico = sum(1 for palabra in palabras_criticas if palabra in mensaje_lower)
    
    if tipo == 'FELICITACION':
        sentimiento = 'POSITIVO'
    elif contador_critico > 0:
        sentimiento = 'CRITICO'
    elif contador_negativo > contador_positivo:
        sentimiento = 'NEGATIVO'
    elif contador_positivo > contador_negativo:
        sentimiento = 'POSITIVO'
    
    # ==============================================================================
    # ANÁLISIS DE CATEGORÍA
    # ==============================================================================
    categoria = 'OTRO'
    plan_accion = []
    resumen_causa = ""
    
    # Tiempos
    if any(palabra in mensaje_lower for palabra in ['tarda', 'tardan', 'espera', 'esperar', 'hora', 'horas', 'demora', 'lento', 'retraso']):
        categoria = 'TIEMPOS'
        resumen_causa = "El cliente reporta problemas con tiempos de espera o demoras en el servicio."
        plan_accion = [
            "Revisar flujo de recepción y tiempos promedio de atención",
            "Analizar cuellos de botella en el proceso",
            "Considerar aumentar personal en horas pico",
            "Implementar sistema de citas si no existe",
            "Comunicar tiempos estimados realistas a los pacientes"
        ]
    
    # Limpieza
    elif any(palabra in mensaje_lower for palabra in ['sucia', 'sucio', 'basura', 'baño', 'baños', 'limpio', 'limpia', 'higiene', 'mugre', 'polvo']):
        categoria = 'LIMPIEZA'
        resumen_causa = "El cliente identifica problemas de limpieza e higiene en las instalaciones."
        plan_accion = [
            "Verificar checklist de intendencia",
            "Auditoría de limpieza de baños y áreas comunes",
            "Revisar frecuencia de limpieza vs flujo de pacientes",
            "Capacitar a personal de limpieza",
            "Implementar inspecciones aleatorias"
        ]
    
    # Precios
    elif any(palabra in mensaje_lower for palabra in ['caro', 'cara', 'precio', 'precios', 'costoso', 'barato', 'competencia', 'otros lugares']):
        categoria = 'PRECIOS'
        resumen_causa = "El cliente tiene preocupaciones sobre los precios en comparación con la competencia."
        plan_accion = [
            "Realizar benchmarking de precios con competencia local",
            "Revisar estructura de costos y márgenes",
            "Evaluar ofertas promocionales o paquetes",
            "Comunicar valor agregado del servicio",
            "Considerar descuentos para casos especiales"
        ]
    
    # Trato
    elif any(palabra in mensaje_lower for palabra in ['grosero', 'maltrato', 'falta respeto', 'maleducado', 'brusco', 'rudeza', 'atención', 'trato']):
        categoria = 'TRATO'
        resumen_causa = "El cliente reporta problemas con el trato del personal hacia los pacientes."
        plan_accion = [
            "Revisar protocolos de atención al cliente",
            "Capacitar a personal en servicio al cliente",
            "Identificar al personal involucrado (si no es anónimo)",
            "Implementar evaluación de satisfacción continua",
            "Establecer consecuencia para mal trato"
        ]
    
    # Instalaciones
    elif any(palabra in mensaje_lower for palabra in ['instalaciones', 'equipo', 'maquinaria', 'aparato', 'sala', 'consultorio', 'comodidad', 'aire', 'temperatura']):
        categoria = 'INSTALACIONES'
        resumen_causa = "El cliente identifica problemas con las instalaciones físicas o equipos."
        plan_accion = [
            "Inspección física de las áreas mencionadas",
            "Revisar mantenimiento preventivo de equipos",
            "Evaluar comodidad y ambiente del espacio",
            "Presupuestar mejoras necesarias",
            "Implementar mantenimiento preventivo regular"
        ]
    
    # Proceso
    elif any(palabra in mensaje_lower for palabra in ['proceso', 'procedimiento', 'pasos', 'complicado', 'difícil', 'confuso', 'burocracia']):
        categoria = 'PROCESO'
        resumen_causa = "El cliente encuentra problemas con los procesos o procedimientos."
        plan_accion = [
            "Mapear proceso actual end-to-end",
            "Identificar pasos innecesarios o redundantes",
            "Simplificar procesos donde sea posible",
            "Capacitar a personal en procesos optimizados",
            "Comunicar cambios a los pacientes"
        ]
    
    # Categoría por defecto si no coincide
    if categoria == 'OTRO':
        resumen_causa = "El cliente reporta un problema que requiere revisión detallada."
        plan_accion = [
            "Revisar mensaje completo para identificar el problema específico",
            "Contactar al cliente si proporcionó contacto",
            "Documentar el caso para referencia futura",
            "Establecer seguimiento personalizado"
        ]
    
    # Ajustar sentimiento basado en tipo si no se detectó claramente
    if tipo == 'QUEJA' and sentimiento == 'NEUTRO':
        sentimiento = 'NEGATIVO'
    elif tipo == 'SUGERENCIA' and sentimiento == 'NEUTRO':
        sentimiento = 'NEUTRO'
    elif tipo == 'FELICITACION':
        sentimiento = 'POSITIVO'
    
    return {
        'sentimiento_ia': sentimiento,
        'categoria_ia': categoria,
        'resumen_causa': resumen_causa,
        'plan_accion_sugerido': '\n'.join([f"{i+1}. {accion}" for i, accion in enumerate(plan_accion)]),
        'analizado_ia': True,
        'fecha_analisis': timezone.now()
    }
