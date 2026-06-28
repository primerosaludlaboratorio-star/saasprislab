"""
Utilidades para Recursos Humanos: Auto-asignación de Planes de Desarrollo.
Inspirado en Buk: Evaluación -> Diagnóstico -> Cura (Academy).
"""
from datetime import timedelta
from django.utils import timezone
from django.db import transaction

from core.models import (
    EvaluacionDesempeno, PlanDesarrollo, DetalleEvaluacion, 
    Competencia, Empleado
)


def generar_pdi_automatico(evaluacion_id):
    """
    Genera automáticamente un Plan de Desarrollo Individual (PDI) basado en la evaluación.
    
    La función analiza las competencias evaluadas y asigna cursos/capacitaciones
    automáticamente según las áreas de mejora detectadas.
    
    Args:
        evaluacion_id: ID de la EvaluacionDesempeno
        
    Returns:
        PlanDesarrollo: El plan de desarrollo creado
    """
    evaluacion = EvaluacionDesempeno.objects.select_related(
        'empleado', 'empleado__usuario'
    ).prefetch_related(
        'detalles__competencia'
    ).get(id=evaluacion_id)
    
    # Mapeo de competencias a cursos (esto debería venir de Academy en el futuro)
    MAPEO_COMPETENCIAS_CURSOS = {
        'Atención al Cliente': {
            'curso': 'Protocolo Disney - Atención al Cliente',
            'codigo_curso': 'AC-001',
            'dias_limite': 30
        },
        'Toma de Muestra': {
            'curso': 'Técnicas de Flebotomía Avanzada',
            'codigo_curso': 'TM-001',
            'dias_limite': 45
        },
        'Liderazgo': {
            'curso': 'Liderazgo 101 - Fundamentos de Gestión de Equipo',
            'codigo_curso': 'LH-001',
            'dias_limite': 60
        },
        'Ventas': {
            'curso': 'Ventas Efectivas - Cierre y Persuasión',
            'codigo_curso': 'VE-001',
            'dias_limite': 30
        },
        'Comunicación': {
            'curso': 'Comunicación Efectiva en el Entorno Laboral',
            'codigo_curso': 'CE-001',
            'dias_limite': 30
        },
        'Pipeteo': {
            'curso': 'Técnicas de Pipeteo y Manejo de Muestras',
            'codigo_curso': 'PP-001',
            'dias_limite': 45
        },
    }
    
    with transaction.atomic():
        # Crear el Plan de Desarrollo
        fecha_limite = timezone.now().date() + timedelta(days=60)  # Default 60 días
        plan = PlanDesarrollo.objects.create(
            empleado=evaluacion.empleado,
            evaluacion_origen=evaluacion,
            fecha_limite=fecha_limite,
            estado='PENDIENTE',
            observaciones=f"Plan generado automáticamente desde evaluación {evaluacion.periodo}"
        )
        
        # Analizar detalles de evaluación y asignar cursos
        cursos_asignados = []
        detalles_bajos = evaluacion.detalles.filter(calificacion__lt=3)
        
        for detalle in detalles_bajos:
            competencia_nombre = detalle.competencia.nombre
            if competencia_nombre in MAPEO_COMPETENCIAS_CURSOS:
                curso_info = MAPEO_COMPETENCIAS_CURSOS[competencia_nombre]
                
                # Calcular fecha límite específica para este curso
                fecha_limite_curso = timezone.now().date() + timedelta(days=curso_info['dias_limite'])
                
                # Actualizar fecha límite del plan si este curso requiere más tiempo
                if fecha_limite_curso > plan.fecha_limite:
                    plan.fecha_limite = fecha_limite_curso
                
                cursos_asignados.append({
                    'nombre': curso_info['curso'],
                    'codigo': curso_info['codigo_curso'],
                    'competencia': competencia_nombre,
                    'calificacion': detalle.calificacion,
                    'fecha_limite': fecha_limite_curso
                })
                
                # Asignación de curso desde Academy pendiente cuando se active MARKETING_ACADEMY_ENABLED.
                # if hasattr(settings, 'MARKETING_ACADEMY_ENABLED'):
                #     from marketing.models import CursoAcademy
                #     curso = CursoAcademy.objects.get_or_create(
                #         codigo=curso_info['codigo_curso'],
                #         defaults={'nombre': curso_info['curso']}
                #     )[0]
                #     plan.cursos_asignados.add(curso)
        
        # Guardar observaciones con los cursos asignados
        if cursos_asignados:
            observaciones = plan.observaciones or ''
            observaciones += f"\n\nCursos asignados automáticamente:\n"
            for curso in cursos_asignados:
                observaciones += f"- {curso['nombre']} (Límite: {curso['fecha_limite'].strftime('%d/%m/%Y')})\n"
                observaciones += f"  Razón: Competencia '{curso['competencia']}' calificada con {curso['calificacion']}/5\n"
            plan.observaciones = observaciones
        else:
            plan.observaciones = (plan.observaciones or '') + "\n\nNo se detectaron áreas de mejora críticas. Continuar con desarrollo general."
        
        plan.save()
        
        # Calcular cuadrante 9-Box y actualizar evaluación
        cuadrante = evaluacion.calcular_cuadrante_9box()
        evaluacion.cuadrante_9box = cuadrante
        evaluacion.save(update_fields=['cuadrante_9box'])
        
        # Generar feedback de IA
        generar_feedback_ia(evaluacion, plan)
        
        return plan


def generar_feedback_ia(evaluacion, plan):
    """
    Genera feedback automático basado en los resultados de la evaluación.
    
    Args:
        evaluacion: EvaluacionDesempeno
        plan: PlanDesarrollo
    """
    detalles = evaluacion.detalles.all()
    
    # Calcular promedio de competencias
    if detalles.exists():
        promedio = sum(d.calificacion for d in detalles) / detalles.count()
        evaluacion.promedio_competencias = promedio * 20  # Convertir de 1-5 a 0-100
    else:
        promedio = 0
    
    # Generar feedback basado en el cuadrante
    cuadrante = evaluacion.cuadrante_9box
    feedback = ""
    
    if cuadrante == 'FUTURO_LIDER':
        feedback = f"🌟 {evaluacion.empleado.usuario.get_full_name()} es un FUTURO LÍDER.\n\n"
        feedback += f"Desempeño: {evaluacion.desempeno_score:.1f}/100\n"
        feedback += f"Potencial: {evaluacion.potencial_score:.1f}/100\n\n"
        feedback += "Recomendación: Considerar ascenso o asignación de proyectos estratégicos. Mantener desarrollo continuo en liderazgo."
    
    elif cuadrante == 'ESTRELLA':
        feedback = f"⭐ {evaluacion.empleado.usuario.get_full_name()} es una ESTRELLA.\n\n"
        feedback += f"Promedio de competencias: {evaluacion.promedio_competencias:.1f}/100\n"
        feedback += "Recomendación: Reconocer su excelente desempeño. Asignar como mentor de nuevos empleados."
    
    elif cuadrante == 'ENIGMA':
        feedback = f"❓ {evaluacion.empleado.usuario.get_full_name()} es un ENIGMA.\n\n"
        feedback += f"Tiene alto potencial ({evaluacion.potencial_score:.1f}/100) pero bajo desempeño ({evaluacion.desempeno_score:.1f}/100).\n\n"
        feedback += "Análisis: Posible problema de motivación, falta de claridad en objetivos, o necesidad de capacitación específica.\n\n"
        feedback += "Acción: Revisar objetivos, proporcionar feedback constante y asignar plan de desarrollo enfocado."
    
    elif cuadrante == 'BAJO_RENDIMIENTO':
        feedback = f"⚠️ {evaluacion.empleado.usuario.get_full_name()} tiene BAJO RENDIMIENTO.\n\n"
        feedback += f"Desempeño: {evaluacion.desempeno_score:.1f}/100\n"
        feedback += f"Potencial: {evaluacion.potencial_score:.1f}/100\n\n"
        feedback += "Recomendación: Plan de mejora urgente con seguimiento semanal. Si no hay mejora en 30 días, considerar cambio de rol o terminación."
    
    else:
        feedback = f"📊 Evaluación de {evaluacion.empleado.usuario.get_full_name()} - Periodo {evaluacion.periodo}\n\n"
        feedback += f"Cuadrante: {evaluacion.get_cuadrante_9box_display()}\n"
        feedback += f"Promedio Competencias: {evaluacion.promedio_competencias:.1f}/100\n"
        feedback += f"Cumplimiento KPIs: {evaluacion.cumplimiento_kpis:.1f}/100\n\n"
        
        if plan and plan.cursos_asignados.exists():
            feedback += "Plan de Desarrollo asignado con cursos específicos según áreas de mejora."
        else:
            feedback += "Mantener desarrollo continuo y seguimiento regular."
    
    evaluacion.feedback_ia = feedback
    evaluacion.save(update_fields=['feedback_ia'])
