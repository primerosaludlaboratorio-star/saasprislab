#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comando GÉNESIS: Setup Completo para Demostración
Pobla el sistema con datos reales y lo deja listo para usar.

EJECUTAR: python manage.py setup_demo_total
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta, date, datetime
from decimal import Decimal
import random

from core.models import (
    Empresa, Sucursal, Usuario, Empleado, Paciente,
    OrdenDeServicio, DetalleOrden, Producto, Venta, DetalleVenta, Pago,
    PreOrdenLaboratorio, DetallePreOrden, EvaluacionDesempeno,
    DetalleEvaluacion, Competencia, PlanDesarrollo
)
from consultorio.models import ConsultaMedica
import logging

# CursoAcademy puede no existir aún, lo manejamos opcionalmente
try:
    from marketing.models import CursoAcademy
except ImportError:
    CursoAcademy = None

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup completo del sistema para demostración'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Borrar todos los datos antes de crear nuevos',
        )
    
    @transaction.atomic
    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy (core.Estudio / categorías). "
            "Para LIMS v7.5 use: python manage.py importar_catalogo_lims "
            "(pipeline: python manage.py ensamblar_lims_v75)."
        )
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write(self.style.SUCCESS('GENESIS - SETUP COMPLETO PARA DEMOSTRACION'))
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write('')
        
        if options['flush']:
            self.stdout.write(self.style.WARNING('LIMPIEZA DE DATOS...'))
            self._limpiar_datos()
        
        # PASO 1: INFRAESTRUCTURA
        self.stdout.write(self.style.WARNING('\nPASO 1: CREANDO INFRAESTRUCTURA'))
        empresa, sucursal = self._crear_infraestructura()
        
        # PASO 2: USUARIOS
        self.stdout.write(self.style.WARNING('\nPASO 2: CREANDO USUARIOS'))
        usuarios = self._crear_usuarios(empresa)
        
        # PASO 3: CATALOGOS
        self.stdout.write(self.style.WARNING('\nPASO 3: CREANDO CATALOGOS'))
        estudios = self._crear_estudios(empresa)
        productos = self._crear_productos(empresa)
        competencias = self._crear_competencias()
        cursos = self._crear_cursos(empresa)
        
        # PASO 4: PACIENTES Y FLUJOS
        self.stdout.write(self.style.WARNING('\nPASO 4: CREANDO PACIENTES Y FLUJOS'))
        self._crear_caso_a_normal(empresa, usuarios, estudios)  # Caso A: Normal
        self._crear_caso_b_panico(empresa, usuarios, estudios)  # Caso B: Panico
        self._crear_caso_c_consultorio(empresa, usuarios, estudios)  # Caso C: Consultorio
        self._crear_caso_d_rh(empresa, sucursal, usuarios, competencias, cursos)  # Caso D: RH
        
        # PASO 5: FINANZAS
        self.stdout.write(self.style.WARNING('\nPASO 5: CREANDO DATOS FINANCIEROS'))
        self._crear_ventas_farmacia(empresa, usuarios, productos)
        self._crear_cortes_caja(empresa, usuarios)
        
        # REPORTE FINAL
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('SISTEMA LISTO PARA DEMOSTRACION'))
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('CREDENCIALES:'))
        self.stdout.write(self.style.SUCCESS('   Usuario: admin'))
        self.stdout.write(self.style.SUCCESS('   Password: admin'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('ESCENARIOS CARGADOS:'))
        self.stdout.write(self.style.SUCCESS('   [OK] Caso A: Paciente Normal (Resultados normales, validada)'))
        self.stdout.write(self.style.SUCCESS('   [OK] Caso B: Paciente Grave (Valor de panico en Glucosa)'))
        self.stdout.write(self.style.SUCCESS('   [OK] Caso C: Consultorio (Pre-Orden generada por medico)'))
        self.stdout.write(self.style.SUCCESS('   [OK] Caso D: RH (Evaluacion con desempeno bajo, PDI automatico)'))
        self.stdout.write(self.style.SUCCESS('   [OK] Farmacia: Ventas y cortes de caja'))
        self.stdout.write('')
    
    def _limpiar_datos(self):
        """Limpia todos los datos del sistema usando SQL directo para evitar signals."""
        from django.db import connection
        
        try:
            cursor = connection.cursor()
            
            # Desactivar foreign key checks temporalmente (SQLite)
            if 'sqlite' in connection.settings_dict['ENGINE']:
                cursor.execute('PRAGMA foreign_keys = OFF;')
            
            # Eliminar en orden usando SQL directo para evitar signals
            tables = [
                'core_salesreturn',
                'core_detallepreorden',
                'core_preordenlaboratorio',
                'core_detalleorden',
                'core_ordendeservicio',
                'core_detalleventa',
                'core_pago',
                'core_venta',
                'core_paciente',
                'core_producto',
                'core_detalleevaluacion',
                'core_plandesarrollo',
                'core_evaluaciondesempeno',
                'core_competencia',
            ]
            
            for table in tables:
                try:
                    cursor.execute(f'DELETE FROM {table};')
                except Exception:
                    logging.getLogger(__name__).exception("Error inesperado en _limpiar_datos (setup_demo_total.py)")
                    pass  # Ignorar si la tabla no existe
            
            # Eliminar usuarios no superuser usando ORM (necesita signals para otros objetos relacionados)
            Usuario.objects.filter(is_superuser=False).delete()
            
            # Reactivar foreign key checks
            if 'sqlite' in connection.settings_dict['ENGINE']:
                cursor.execute('PRAGMA foreign_keys = ON;')
            
            self.stdout.write('   [OK] Datos limpiados')
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _limpiar_datos (setup_demo_total.py)")
            self.stdout.write(self.style.WARNING(f'   [ADVERTENCIA] Error parcial al limpiar: {str(e)}'))
            self.stdout.write('   Continuando con la creacion de datos...')
    
    def _crear_infraestructura(self):
        """Crea la empresa y sucursal base."""
        empresa, created = Empresa.objects.get_or_create(
            nombre='PRIS-VALLE',
            defaults={
                'rfc': 'PRV123456ABC',
                'direccion': 'Calle Principal 123, Acayucan, Ver.',
                'telefono': '9241234567',
            }
        )
        self.stdout.write(f'   [OK] Empresa: {empresa.nombre}')
        
        sucursal, created = Sucursal.objects.get_or_create(
            empresa=empresa,
            codigo_sucursal='ACA001',
            defaults={
                'nombre': 'Acayucan',
                'direccion': 'Calle Principal 123',
                'telefono': '9241234567',
                'responsable': 'Dr. Administrador',
                'activa': True,
            }
        )
        self.stdout.write(f'   [OK] Sucursal: {sucursal.nombre}')
        
        return empresa, sucursal
    
    def _crear_usuarios(self, empresa):
        """Crea los usuarios del sistema."""
        usuarios = {}
        
        # Admin (Superuser)
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'Administrador',
                'last_name': 'Sistema',
                'email': 'admin@prisvalle.com',
                'empresa': empresa,
                'rol': 'ADMIN',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True,
            }
        )
        if created:
            admin.set_password('admin')
            admin.save()
        usuarios['admin'] = admin
        self.stdout.write(f'   [OK] Admin: admin / admin')
        
        # Químico
        quimico, created = User.objects.get_or_create(
            username='quimico1',
            defaults={
                'first_name': 'Químico',
                'last_name': 'Principal',
                'email': 'quimico@prisvalle.com',
                'empresa': empresa,
                'rol': 'QUIMICO',
                'is_staff': True,
                'is_active': True,
            }
        )
        if created:
            quimico.set_password('quimico123')
            quimico.save()
        usuarios['quimico'] = quimico
        self.stdout.write(f'   [OK] Quimico: quimico1 / quimico123')
        
        # Recepción
        recepcion, created = User.objects.get_or_create(
            username='recepcion1',
            defaults={
                'first_name': 'Recepcionista',
                'last_name': 'Principal',
                'email': 'recepcion@prisvalle.com',
                'empresa': empresa,
                'rol': 'RECEPCION',
                'is_staff': True,
                'is_active': True,
            }
        )
        if created:
            recepcion.set_password('recepcion123')
            recepcion.save()
        usuarios['recepcion'] = recepcion
        self.stdout.write(f'   [OK] Recepcion: recepcion1 / recepcion123')
        
        # Médico
        medico, created = User.objects.get_or_create(
            username='medico1',
            defaults={
                'first_name': 'Dr. Médico',
                'last_name': 'Principal',
                'email': 'medico@prisvalle.com',
                'empresa': empresa,
                'rol': 'MEDICO',
                'is_staff': True,
                'is_active': True,
            }
        )
        if created:
            medico.set_password('medico123')
            medico.save()
        usuarios['medico'] = medico
        self.stdout.write(f'   [OK] Medico: medico1 / medico123')
        
        # Empleado para RH (Juan Vago)
        empleado_rh_user, created = User.objects.get_or_create(
            username='juanvago',
            defaults={
                'first_name': 'Juan',
                'last_name': 'Vago',
                'email': 'juan@prisvalle.com',
                'empresa': empresa,
                'rol': 'CAJERO',
                'is_active': True,
            }
        )
        if created:
            empleado_rh_user.set_password('juan123')
            empleado_rh_user.save()
        usuarios['empleado_rh'] = empleado_rh_user
        self.stdout.write(f'   [OK] Empleado RH: juanvago / juan123')
        
        return usuarios
    
    def _crear_estudios(self, empresa):
        """Crea 10 estudios de laboratorio."""
        categoria, _ = CategoriaEstudio.objects.get_or_create(
            nombre='Quimica Clinica'
        )
        
        estudios_data = [
            {'codigo': 'GLU', 'nombre': 'Glucosa', 'precio': 50.00, 'valor_min': 70, 'valor_max': 100, 'panico_min': 40, 'panico_max': 400, 'unidad': 'mg/dL'},
            {'codigo': 'BH', 'nombre': 'Biometría Hemática Completa', 'precio': 120.00, 'valor_min': None, 'valor_max': None, 'panico_min': None, 'panico_max': None, 'unidad': ''},
            {'codigo': 'EGO', 'nombre': 'Examen General de Orina', 'precio': 80.00, 'valor_min': None, 'valor_max': None, 'panico_min': None, 'panico_max': None, 'unidad': ''},
            {'codigo': 'TGP', 'nombre': 'Transaminasa GPT/ALT', 'precio': 60.00, 'valor_min': 7, 'valor_max': 56, 'panico_min': 3, 'panico_max': 200, 'unidad': 'U/L'},
            {'codigo': 'TGO', 'nombre': 'Transaminasa GOT/AST', 'precio': 60.00, 'valor_min': 10, 'valor_max': 40, 'panico_min': 5, 'panico_max': 150, 'unidad': 'U/L'},
            {'codigo': 'CREA', 'nombre': 'Creatinina', 'precio': 55.00, 'valor_min': 0.6, 'valor_max': 1.2, 'panico_min': 0.3, 'panico_max': 3.0, 'unidad': 'mg/dL'},
            {'codigo': 'UREA', 'nombre': 'Urea', 'precio': 55.00, 'valor_min': 7, 'valor_max': 20, 'panico_min': 3, 'panico_max': 50, 'unidad': 'mg/dL'},
            {'codigo': 'COL', 'nombre': 'Colesterol Total', 'precio': 70.00, 'valor_min': 0, 'valor_max': 200, 'panico_min': 0, 'panico_max': 300, 'unidad': 'mg/dL'},
            {'codigo': 'TRIG', 'nombre': 'Triglicéridos', 'precio': 70.00, 'valor_min': 0, 'valor_max': 150, 'panico_min': 0, 'panico_max': 500, 'unidad': 'mg/dL'},
            {'codigo': 'PERF_LIP', 'nombre': 'Perfil Lipídico', 'precio': 250.00, 'valor_min': None, 'valor_max': None, 'panico_min': None, 'panico_max': None, 'unidad': ''},
        ]
        
        estudios = {}
        for est_data in estudios_data:
            estudio, created = Estudio.objects.get_or_create(
                codigo=est_data['codigo'],
                defaults={
                    'nombre': est_data['nombre'],
                    'categoria': categoria,
                    'precio': Decimal(str(est_data['precio'])),
                    'valor_minimo': Decimal(str(est_data['valor_min'])) if est_data['valor_min'] else None,
                    'valor_maximo': Decimal(str(est_data['valor_max'])) if est_data['valor_max'] else None,
                    'rango_panico_min': Decimal(str(est_data['panico_min'])) if est_data['panico_min'] else None,
                    'rango_panico_max': Decimal(str(est_data['panico_max'])) if est_data['panico_max'] else None,
                    'unidad': est_data['unidad'],
                    'activo': True,
                }
            )
            estudios[est_data['codigo']] = estudio
        
        self.stdout.write(f'   [OK] {len(estudios)} estudios creados')
        return estudios
    
    def _crear_productos(self, empresa):
        """Crea 20 productos de farmacia."""
        productos_data = [
            {'codigo': '7501234567890', 'nombre': 'Paracetamol 500mg', 'precio': 25.00, 'stock': 100},
            {'codigo': '7501234567891', 'nombre': 'Alcohol 500ml', 'precio': 30.00, 'stock': 50},
            {'codigo': '7501234567892', 'nombre': 'Gasas Estériles', 'precio': 15.00, 'stock': 200},
            {'codigo': '7501234567893', 'nombre': 'Jeringas 5ml', 'precio': 10.00, 'stock': 300},
            {'codigo': '7501234567894', 'nombre': 'Ibuprofeno 400mg', 'precio': 35.00, 'stock': 80},
            {'codigo': '7501234567895', 'nombre': 'Amoxicilina 500mg', 'precio': 45.00, 'stock': 60},
            {'codigo': '7501234567896', 'nombre': 'Vendas Elásticas', 'precio': 20.00, 'stock': 150},
            {'codigo': '7501234567897', 'nombre': 'Algodón', 'precio': 12.00, 'stock': 250},
            {'codigo': '7501234567898', 'nombre': 'Guantes Nitrilo', 'precio': 18.00, 'stock': 400},
            {'codigo': '7501234567899', 'nombre': 'Termómetro Digital', 'precio': 80.00, 'stock': 30},
            {'codigo': '7501234567900', 'nombre': 'Mascarillas N95', 'precio': 50.00, 'stock': 200},
            {'codigo': '7501234567901', 'nombre': 'Cubrebocas Desechable', 'precio': 5.00, 'stock': 1000},
            {'codigo': '7501234567902', 'nombre': 'Loperamida 2mg', 'precio': 28.00, 'stock': 90},
            {'codigo': '7501234567903', 'nombre': 'Omeprazol 20mg', 'precio': 40.00, 'stock': 70},
            {'codigo': '7501234567904', 'nombre': 'Suero Oral', 'precio': 15.00, 'stock': 180},
            {'codigo': '7501234567905', 'nombre': 'Tiras Reactivas Glucosa', 'precio': 120.00, 'stock': 50},
            {'codigo': '7501234567906', 'nombre': 'Agua Destilada', 'precio': 8.00, 'stock': 500},
            {'codigo': '7501234567907', 'nombre': 'Apósitos', 'precio': 22.00, 'stock': 120},
            {'codigo': '7501234567908', 'nombre': 'Esparadrapo', 'precio': 10.00, 'stock': 300},
            {'codigo': '7501234567909', 'nombre': 'Lancetas', 'precio': 35.00, 'stock': 250},
        ]
        
        productos = {}
        for prod_data in productos_data:
            producto, created = Producto.objects.get_or_create(
                codigo_barras=prod_data['codigo'],
                empresa=empresa,
                defaults={
                    'nombre': prod_data['nombre'],
                    'precio_publico': Decimal(str(prod_data['precio'])),
                    'stock': prod_data['stock'],
                }
            )
            productos[prod_data['nombre']] = producto
        
        self.stdout.write(f'   [OK] {len(productos)} productos creados')
        return productos
    
    def _crear_competencias(self):
        """Crea competencias para evaluaciones."""
        competencias_data = [
            {'nombre': 'Comunicación Efectiva', 'tipo': 'BLANDA', 'descripcion': 'Habilidad para transmitir ideas claramente.'},
            {'nombre': 'Trabajo en Equipo', 'tipo': 'BLANDA', 'descripcion': 'Colaboración y cooperación con colegas.'},
            {'nombre': 'Atención al Cliente', 'tipo': 'BLANDA', 'descripcion': 'Interacción positiva y efectiva con clientes.'},
            {'nombre': 'Puntualidad', 'tipo': 'BLANDA', 'descripcion': 'Llegada a tiempo y cumplimiento de horarios.'},
            {'nombre': 'Toma de Muestra', 'tipo': 'TECNICA', 'descripcion': 'Habilidad en procedimientos de flebotomía.'},
            {'nombre': 'Manejo de Equipos Lab', 'tipo': 'TECNICA', 'descripcion': 'Operación y mantenimiento de instrumentación.'},
            {'nombre': 'Análisis de Resultados', 'tipo': 'TECNICA', 'descripcion': 'Interpretación crítica de datos de laboratorio.'},
            {'nombre': 'Control de Calidad', 'tipo': 'TECNICA', 'descripcion': 'Aplicación de protocolos de calidad.'},
        ]
        
        competencias = {}
        for comp_data in competencias_data:
            comp, created = Competencia.objects.get_or_create(
                nombre=comp_data['nombre'],
                defaults={
                    'tipo': comp_data['tipo'],
                    'descripcion': comp_data['descripcion'],
                }
            )
            competencias[comp_data['nombre']] = comp
        
        self.stdout.write(f'   [OK] {len(competencias)} competencias creadas')
        return competencias
    
    def _crear_cursos(self, empresa):
        """Crea cursos de Academy."""
        if CursoAcademy is None:
            self.stdout.write('   [WARN] CursoAcademy no esta disponible, se omite la creacion de cursos')
            return {}
        
        cursos_data = [
            {'nombre': 'Protocolo Disney', 'descripcion': 'Atención al cliente estilo Disney'},
            {'nombre': 'Técnicas de Flebotomía Avanzada', 'descripcion': 'Mejora en técnicas de toma de muestra'},
            {'nombre': 'Control de Calidad en Laboratorio', 'descripcion': 'Protocolos de calidad y buenas prácticas'},
        ]
        
        cursos = {}
        for curso_data in cursos_data:
            curso, created = CursoAcademy.objects.get_or_create(
                nombre=curso_data['nombre'],
                defaults={
                    'descripcion': curso_data['descripcion'],
                    'activo': True,
                }
            )
            cursos[curso_data['nombre']] = curso
        
        self.stdout.write(f'   [OK] {len(cursos)} cursos creados')
        return cursos
    
    def _crear_caso_a_normal(self, empresa, usuarios, estudios):
        """Caso A: Paciente Normal - Orden pagada, resultados normales, validada."""
        paciente, _ = Paciente.objects.get_or_create(
            nombre_completo='Maria Bien',
            empresa=empresa,
            defaults={
                'fecha_nacimiento': date(1990, 5, 15),
                'sexo': 'F',
                'telefono': '9241234567',
            }
        )
        
        orden = OrdenDeServicio.objects.create(
            empresa=empresa,
            paciente=paciente,
            total=Decimal('130.00'),
            anticipo=Decimal('130.00'),
            estado='RESULTADOS_LISTOS',
            responsable_ingreso=usuarios['recepcion'],
            folio_orden=f'LAB-{timezone.now().strftime("%Y%m%d")}-001'
        )
        
        # GLU con resultado normal
        detalle_glu = DetalleOrden.objects.create(
            orden=orden,
            estudio=estudios['GLU'],
            precio_momento=estudios['GLU'].precio,
            resultado='85',
            estado_procesamiento='RESULTADO_LISTO',
            validado_por=usuarios['quimico'],
            fecha_validacion=timezone.now() - timedelta(hours=2),
        )
        
        # BH con resultado normal
        DetalleOrden.objects.create(
            orden=orden,
            estudio=estudios['BH'],
            precio_momento=estudios['BH'].precio,
            resultado='Dentro de rangos normales',
            estado_procesamiento='RESULTADO_LISTO',
            validado_por=usuarios['quimico'],
            fecha_validacion=timezone.now() - timedelta(hours=2),
        )
        
        self.stdout.write('   [OK] Caso A: Maria Bien (Normal) creado')
    
    def _crear_caso_b_panico(self, empresa, usuarios, estudios):
        """Caso B: Paciente Grave - Glucosa en 600 mg/dL (Valor de Pánico)."""
        paciente, _ = Paciente.objects.get_or_create(
            nombre_completo='Pedro Grave',
            empresa=empresa,
            defaults={
                'fecha_nacimiento': date(1975, 8, 20),
                'sexo': 'M',
                'telefono': '9241234568',
            }
        )
        
        orden = OrdenDeServicio.objects.create(
            empresa=empresa,
            paciente=paciente,
            total=Decimal('50.00'),
            anticipo=Decimal('50.00'),
            estado='RESULTADOS_LISTOS',
            responsable_ingreso=usuarios['recepcion'],
            folio_orden=f'LAB-{timezone.now().strftime("%Y%m%d")}-002'
        )
        
        # GLU con valor de pánico (600 mg/dL)
        detalle_glu = DetalleOrden.objects.create(
            orden=orden,
            estudio=estudios['GLU'],
            precio_momento=estudios['GLU'].precio,
            resultado='600',
            estado_procesamiento='RESULTADO_LISTO',
            valor_critico_confirmado=True,  # Ya confirmado
            validado_por=usuarios['quimico'],
            fecha_validacion=timezone.now() - timedelta(hours=1),
            observaciones='VALOR DE PÁNICO CONFIRMADO. Paciente notificado al médico.'
        )
        
        self.stdout.write('   [OK] Caso B: Pedro Grave (Panico) creado')
    
    def _crear_caso_c_consultorio(self, empresa, usuarios, estudios):
        """Caso C: Consultorio - Pre-Orden generada por médico."""
        paciente, _ = Paciente.objects.get_or_create(
            nombre_completo='Ana Consulta',
            empresa=empresa,
            defaults={
                'fecha_nacimiento': date(1985, 3, 10),
                'sexo': 'F',
                'telefono': '9241234569',
            }
        )
        
        # Crear consulta médica
        consulta, _ = ConsultaMedica.objects.get_or_create(
            empresa=empresa,
            paciente=paciente,
            medico=usuarios['medico'],
            defaults={
                'motivo': 'Consulta médica de rutina',
            }
        )
        
        # Crear Pre-Orden
        preorden = PreOrdenLaboratorio.objects.create(
            empresa=empresa,
            paciente=paciente,
            medico_solicitante=usuarios['medico'],
            consulta_medica=consulta,
            estado='PENDIENTE',
            observaciones='Estudios solicitados en consulta médica'
        )
        
        # Agregar estudios a la pre-orden
        DetallePreOrden.objects.create(
            preorden=preorden,
            estudio=estudios['GLU']
        )
        DetallePreOrden.objects.create(
            preorden=preorden,
            estudio=estudios['BH']
        )
        
        self.stdout.write('   [OK] Caso C: Ana Consulta (Pre-Orden) creado')
    
    def _crear_caso_d_rh(self, empresa, sucursal, usuarios, competencias, cursos):
        """Caso D: RH - Evaluación con desempeño bajo, genera PDI automático."""
        from core.utils.rh_utils import generar_pdi_automatico
        
        usuario_rh = usuarios['empleado_rh']
        
        # Crear registro de Empleado (requerido para EvaluacionDesempeno)
        empleado_rh, created = Empleado.objects.get_or_create(
            usuario=usuario_rh,
            empresa=empresa,
            defaults={
                'puesto': 'Cajero',
                'fecha_ingreso': date.today() - timedelta(days=90),
                'activo': True,
                'rol_permisos': 'CAJERO',
                'sucursal': sucursal,
            }
        )
        
        # Crear evaluación con desempeño bajo (1/5 promedio)
        evaluacion = EvaluacionDesempeno.objects.create(
            empleado=empleado_rh,
            evaluador=usuarios['admin'],
            periodo='Q1 2026',
            promedio_competencias=1.0,
            cumplimiento_kpis=30.0,
            cuadrante_9box='BAJO_RENDIMIENTO'
        )
        
        # Agregar detalles de evaluación con calificaciones bajas
        for comp_nombre, competencia in competencias.items():
            calificacion = 1 if 'Atención' in comp_nombre or 'Puntualidad' in comp_nombre else 2
            DetalleEvaluacion.objects.create(
                evaluacion=evaluacion,
                competencia=competencia,
                calificacion=calificacion,
                observacion='Requiere mejora significativa'
            )
        
        # Generar PDI automático
        generar_pdi_automatico(evaluacion.id)
        
        self.stdout.write('   [OK] Caso D: Juan Vago (RH, PDI automatico) creado')
    
    def _crear_ventas_farmacia(self, empresa, usuarios, productos):
        """Crea ventas de farmacia."""
        hoy = timezone.now().date()
        ayer = hoy - timedelta(days=1)
        
        # Venta de hoy
        venta_hoy = Venta.objects.create(
            empresa=empresa,
            usuario=usuarios['recepcion'],
            paciente_nombre='Cliente Demo',
            total=Decimal('75.00'),
            folio_operacion=f'FAR-{hoy.strftime("%Y%m%d")}-001',
            estado='COMPLETADA',
            fecha=timezone.now()
        )
        
        DetalleVenta.objects.create(
            venta=venta_hoy,
            producto=productos['Paracetamol 500mg'],
            cantidad=3,
            precio_unitario=productos['Paracetamol 500mg'].precio_publico,
            subtotal=Decimal('75.00')
        )
        
        Pago.objects.create(
            venta=venta_hoy,
            metodo='EFECTIVO',
            monto=Decimal('75.00')
        )
        
        # Venta de ayer
        venta_ayer = Venta.objects.create(
            empresa=empresa,
            usuario=usuarios['recepcion'],
            paciente_nombre='Cliente Ayer',
            total=Decimal('105.00'),
            folio_operacion=f'FAR-{ayer.strftime("%Y%m%d")}-001',
            estado='COMPLETADA',
            fecha=timezone.make_aware(datetime.combine(ayer, datetime.min.time()))
        )
        
        DetalleVenta.objects.create(
            venta=venta_ayer,
            producto=productos['Ibuprofeno 400mg'],
            cantidad=3,
            precio_unitario=productos['Ibuprofeno 400mg'].precio_publico,
            subtotal=Decimal('105.00')
        )
        
        Pago.objects.create(
            venta=venta_ayer,
            metodo='TARJETA',
            monto=Decimal('105.00')
        )
        
        self.stdout.write('   [OK] Ventas de farmacia creadas')
    
    def _crear_cortes_caja(self, empresa, usuarios):
        """Crea cortes de caja."""
        from core.models import GastoCaja
        
        hoy = timezone.now().date()
        ayer = hoy - timedelta(days=1)
        
        # Gastos de ayer
        GastoCaja.objects.create(
            empresa=empresa,
            usuario=usuarios['recepcion'],
            concepto='Garrafón de agua',
            monto=Decimal('50.00'),
            fecha=timezone.make_aware(datetime.combine(ayer, datetime.min.time()))
        )
        
        # Gastos de hoy
        GastoCaja.objects.create(
            empresa=empresa,
            usuario=usuarios['recepcion'],
            concepto='Limpieza',
            monto=Decimal('100.00'),
            fecha=timezone.now()
        )
        
        self.stdout.write('   [OK] Cortes de caja creados')