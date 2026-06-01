"""
Comando para cargar datos de prueba del módulo de Recursos Humanos.
Crea competencias, cursos dummy y evaluaciones de ejemplo.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random

from core.models import (
    Empresa, Usuario, Empleado, Competencia, EvaluacionDesempeno, 
    DetalleEvaluacion, PlanDesarrollo
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Carga datos de prueba para el módulo de Evaluación de Desempeño y Desarrollo de Talento'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa',
            type=str,
            help='ID o nombre de la empresa para cargar datos',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== CARGA DE DATOS RH - MÓDULO DE TALENTO ===\n'))
        
        # Obtener empresa (sin fallback implícito)
        empresa_id = options.get('empresa')
        if not empresa_id:
            self.stdout.write(
                self.style.ERROR(
                    '❌ Indique --empresa con ID numérico o nombre (multi-tenant: sin empresa implícita).'
                )
            )
            return
        try:
            empresa = Empresa.objects.get(id=int(empresa_id))
        except (ValueError, Empresa.DoesNotExist):
            empresa = Empresa.objects.filter(nombre__icontains=str(empresa_id).strip()).first()
        if not empresa:
            self.stdout.write(self.style.ERROR('❌ No se encontró empresa con ese ID o nombre.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'✓ Empresa: {empresa.nombre}'))
        
        # 1. CREAR COMPETENCIAS
        self.stdout.write(self.style.SUCCESS('\n1. Creando Competencias...'))
        
        competencias_data = [
            # Soft Skills
            {'nombre': 'Liderazgo', 'tipo': 'BLANDA', 'descripcion': 'Capacidad para guiar y motivar equipos'},
            {'nombre': 'Atención al Cliente', 'tipo': 'BLANDA', 'descripcion': 'Habilidad para brindar excelente servicio'},
            {'nombre': 'Comunicación', 'tipo': 'BLANDA', 'descripcion': 'Habilidad para comunicarse efectivamente'},
            {'nombre': 'Trabajo en Equipo', 'tipo': 'BLANDA', 'descripcion': 'Capacidad para colaborar con otros'},
            {'nombre': 'Puntualidad', 'tipo': 'BLANDA', 'descripcion': 'Asistencia y puntualidad'},
            
            # Hard Skills
            {'nombre': 'Toma de Muestra', 'tipo': 'TECNICA', 'descripcion': 'Técnicas de flebotomía y toma de muestras'},
            {'nombre': 'Pipeteo', 'tipo': 'TECNICA', 'descripcion': 'Precisión en el manejo de pipetas'},
            {'nombre': 'Ventas', 'tipo': 'TECNICA', 'descripcion': 'Habilidad para cerrar ventas'},
            {'nombre': 'Manejo de Equipos', 'tipo': 'TECNICA', 'descripcion': 'Conocimiento técnico de equipos de laboratorio'},
            {'nombre': 'Control de Calidad', 'tipo': 'TECNICA', 'descripcion': 'Implementación de controles de calidad'},
        ]
        
        competencias_creadas = []
        for comp_data in competencias_data:
            competencia, created = Competencia.objects.get_or_create(
                nombre=comp_data['nombre'],
                defaults={
                    'tipo': comp_data['tipo'],
                    'descripcion': comp_data['descripcion'],
                    'activa': True
                }
            )
            competencias_creadas.append(competencia)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creada: {competencia.nombre} ({competencia.get_tipo_display()})'))
            else:
                self.stdout.write(self.style.WARNING(f'  ○ Ya existía: {competencia.nombre}'))
        
        # 2. CREAR EMPLEADOS DE PRUEBA (si no existen)
        self.stdout.write(self.style.SUCCESS('\n2. Verificando Empleados de Prueba...'))
        
        empleados_prueba = [
            {'username': 'nancy.lopez', 'first_name': 'Nancy', 'last_name': 'López', 'puesto': 'Química Senior'},
            {'username': 'carlos.mendez', 'first_name': 'Carlos', 'last_name': 'Méndez', 'puesto': 'Cajero'},
            {'username': 'maria.gonzalez', 'first_name': 'María', 'last_name': 'González', 'puesto': 'Recepcionista'},
        ]
        
        empleados_creados = []
        for emp_data in empleados_prueba:
            usuario, user_created = User.objects.get_or_create(
                username=emp_data['username'],
                defaults={
                    'first_name': emp_data['first_name'],
                    'last_name': emp_data['last_name'],
                    'email': f"{emp_data['username']}@prislab.com",
                    'empresa': empresa,
                    'rol': 'CAJERO' if 'Cajero' in emp_data['puesto'] else 'QUIMICO',
                    'password': 'pbkdf2_sha256$600000$test$test=',  # Password por defecto: test123
                }
            )
            
            if user_created:
                usuario.set_password('test123')
                usuario.save()
            
            empleado, emp_created = Empleado.objects.get_or_create(
                usuario=usuario,
                defaults={
                    'empresa': empresa,
                    'puesto': emp_data['puesto'],
                    'fecha_ingreso': timezone.now().date() - timedelta(days=365),
                    'activo': True,
                    'rol_permisos': 'CAJERO' if 'Cajero' in emp_data['puesto'] else 'QUIMICO'
                }
            )
            
            empleados_creados.append(empleado)
            if emp_created or user_created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creado: {empleado.usuario.get_full_name()} - {empleado.puesto}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ○ Ya existía: {empleado.usuario.get_full_name()}'))
        
        # 3. CREAR EVALUACIONES DE PRUEBA
        self.stdout.write(self.style.SUCCESS('\n3. Creando Evaluaciones de Prueba...'))
        
        # Obtener un evaluador (superusuario o admin)
        evaluador = User.objects.filter(is_superuser=True).first() or User.objects.filter(empresa=empresa).first()
        
        periodos = ['Q1 2026', 'Q4 2025', 'Q3 2025']
        cuadrantes_ejemplo = [
            {'empleado_idx': 0, 'desempeno': 85, 'potencial': 90, 'cuadrante': 'FUTURO_LIDER'},  # Nancy - Estrella
            {'empleado_idx': 1, 'desempeno': 55, 'potencial': 70, 'cuadrante': 'ENIGMA'},  # Carlos - Enigma
            {'empleado_idx': 2, 'desempeno': 70, 'potencial': 65, 'cuadrante': 'SOLIDO'},  # María - Sólido
        ]
        
        evaluaciones_creadas = []
        for idx, periodo in enumerate(periodos):
            for cuad_ejemplo in cuadrantes_ejemplo:
                if cuad_ejemplo['empleado_idx'] >= len(empleados_creados):
                    continue
                
                empleado = empleados_creados[cuad_ejemplo['empleado_idx']]
                
                # Verificar si ya existe evaluación para este periodo
                eval_existente = EvaluacionDesempeno.objects.filter(
                    empleado=empleado,
                    periodo=periodo
                ).first()
                
                if eval_existente:
                    self.stdout.write(self.style.WARNING(f'  ○ Ya existe evaluación: {empleado.usuario.get_full_name()} - {periodo}'))
                    continue
                
                desempeno = cuad_ejemplo['desempeno']
                potencial = cuad_ejemplo['potencial']
                
                # Crear evaluación
                evaluacion = EvaluacionDesempeno.objects.create(
                    empleado=empleado,
                    evaluador=evaluador,
                    periodo=periodo,
                    desempeno_score=desempeno,
                    potencial_score=potencial,
                    promedio_competencias=desempeno - random.randint(5, 15),
                    cumplimiento_kpis=desempeno + random.randint(-10, 10),
                    cuadrante_9box=cuad_ejemplo['cuadrante'],
                    estado='COMPLETADA',
                    feedback_ia=f"Evaluación de {empleado.usuario.get_full_name()} para el periodo {periodo}. "
                               f"Cuadrante: {EvaluacionDesempeno.CUADRANTE_9BOX_CHOICES[dict(EvaluacionDesempeno.CUADRANTE_9BOX_CHOICES)[cuad_ejemplo['cuadrante']]]}"
                )
                
                # Crear detalles de evaluación (calificaciones por competencia)
                for competencia in competencias_creadas:
                    # Generar calificación según el tipo de competencia
                    if competencia.tipo == 'BLANDA':
                        # Para soft skills, variar según el desempeño general
                        base_score = desempeno / 20  # Convertir 0-100 a escala 1-5
                        calificacion = max(1, min(5, int(base_score + random.uniform(-0.5, 0.5))))
                    else:
                        # Para hard skills, variar más
                        base_score = potencial / 20
                        calificacion = max(1, min(5, int(base_score + random.uniform(-1, 1))))
                    
                    DetalleEvaluacion.objects.create(
                        evaluacion=evaluacion,
                        competencia=competencia,
                        calificacion=calificacion,
                        observacion=f"Calificación {calificacion}/5 en {competencia.nombre}"
                    )
                
                evaluaciones_creadas.append(evaluacion)
                self.stdout.write(self.style.SUCCESS(f'  ✓ Creada: {empleado.usuario.get_full_name()} - {periodo} ({evaluacion.get_cuadrante_9box_display()})'))
                
                # Generar PDI automático
                try:
                    from core.utils.rh_utils import generar_pdi_automatico
                    plan = generar_pdi_automatico(evaluacion.id)
                    self.stdout.write(self.style.SUCCESS(f'    → PDI generado: {plan.id}'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    ⚠ Error generando PDI: {str(e)}'))
        
        # RESUMEN FINAL
        self.stdout.write(self.style.SUCCESS('\n=== CARGA COMPLETADA ==='))
        self.stdout.write(self.style.SUCCESS(f'✓ Competencias: {len(competencias_creadas)}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Empleados: {len(empleados_creados)}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Evaluaciones: {len(evaluaciones_creadas)}'))
        self.stdout.write(self.style.SUCCESS('\n🎉 El módulo de Talento está listo para usar!'))
        self.stdout.write(self.style.SUCCESS('   Accede a /rh/desempeno/nueva/ para crear evaluaciones'))
        self.stdout.write(self.style.SUCCESS('   Accede a /rh/matriz-talento/ para ver la matriz 9-Box'))
