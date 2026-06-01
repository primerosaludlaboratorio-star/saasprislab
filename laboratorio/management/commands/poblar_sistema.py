"""
Management command para poblar el sistema con datos de prueba.
Crea 50 pacientes con órdenes y estudios para pruebas de carga y estrés.
"""
import random
import sys
import io
import time
from datetime import datetime, timedelta
from decimal import Decimal

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import IntegrityError
from django.utils import timezone
from django.contrib.auth import get_user_model

from laboratorio.models import Estudio, Medico, CategoriaExamen
from core.models import Paciente, OrdenDeServicio, DetalleOrden as CoreDetalleOrden

User = get_user_model()

# Listas de nombres realistas en español
NOMBRES_MASCULINOS = [
    'Juan', 'Carlos', 'Luis', 'Miguel', 'José', 'Francisco', 'Antonio', 'Manuel',
    'Pedro', 'Roberto', 'Fernando', 'Ricardo', 'Javier', 'Daniel', 'Alejandro',
    'Eduardo', 'Rafael', 'Sergio', 'Alberto', 'Mario', 'Jorge', 'Raúl', 'Óscar',
    'Andrés', 'Diego', 'Gabriel', 'Mauricio', 'Rodrigo', 'Gustavo', 'Héctor'
]

NOMBRES_FEMENINOS = [
    'María', 'Ana', 'Laura', 'Carmen', 'Patricia', 'Guadalupe', 'Rosa', 'Martha',
    'Sofía', 'Isabel', 'Lucía', 'Elena', 'Andrea', 'Diana', 'Claudia', 'Monica',
    'Alejandra', 'Verónica', 'Gabriela', 'Adriana', 'Silvia', 'Beatriz', 'Natalia',
    'Valeria', 'Paola', 'Karina', 'Daniela', 'Fernanda', 'Mariana', 'Cecilia'
]

APELLIDOS = [
    'García', 'Rodríguez', 'López', 'Martínez', 'González', 'Pérez', 'Sánchez',
    'Ramírez', 'Torres', 'Flores', 'Rivera', 'Gómez', 'Díaz', 'Cruz', 'Morales',
    'Ortiz', 'Gutiérrez', 'Chávez', 'Ramos', 'Ruiz', 'Herrera', 'Jiménez',
    'Mendoza', 'Vargas', 'Castro', 'Romero', 'Álvarez', 'Moreno', 'Méndez', 'Guerrero',
    'Hernández', 'Fernández', 'Vásquez', 'Medina', 'Soto', 'Delgado', 'Reyes',
    'Vega', 'Campos', 'Silva', 'Rojas', 'Navarro', 'Aguilar', 'Molina', 'Ortega'
]


class Command(BaseCommand):
    help = 'Pobla el sistema con 50 pacientes y órdenes de prueba para pruebas de carga'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pacientes',
            type=int,
            default=50,
            help='Número de pacientes a crear (default: 50)'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Saltar pacientes que ya existen (por código)'
        )

    def handle(self, *args, **options):
        inicio = time.time()
        num_pacientes = options['pacientes']
        skip_existing = options['skip_existing']

        self.stdout.write(self.style.SUCCESS('[INICIANDO] Poblado masivo del sistema...'))
        self.stdout.write(f'[INFO] Se crearan {num_pacientes} pacientes con ordenes y estudios\n')

        # Verificar que existan estudios en el sistema
        estudios = list(Estudio.objects.all())
        if not estudios:
            self.stdout.write(self.style.ERROR('[ERROR] No hay estudios en el sistema.'))
            self.stdout.write(self.style.WARNING('   Ejecuta primero: python manage.py importar_tarifas_lab'))
            return

        # Verificar que exista al menos un usuario
        usuarios = User.objects.all()
        if not usuarios.exists():
            self.stdout.write(self.style.ERROR('[ERROR] No hay usuarios en el sistema.'))
            self.stdout.write(self.style.WARNING('   Crea un usuario primero: python manage.py createsuperuser'))
            return

        usuario_creador = usuarios.first()
        self.stdout.write(f'[USUARIO] Usuario creador: {usuario_creador.username}')
        empresa = getattr(usuario_creador, 'empresa', None)
        if not empresa:
            self.stdout.write(self.style.ERROR('[ERROR] El usuario creador no tiene empresa asignada (requerido para ODS).'))
            return

        # Obtener médicos o crear uno por defecto
        medicos = list(Medico.objects.all())
        if not medicos:
            medico_default = Medico.objects.create(
                nombre='Dr. Medico de Prueba',
                especialidad='Medicina General'
            )
            medicos = [medico_default]
            self.stdout.write(self.style.WARNING('[AVISO] Se creo un medico por defecto'))

        # Estadísticas
        pacientes_creados = 0
        pacientes_omitidos = 0
        ordenes_creadas = 0
        detalles_creados = 0
        errores = []

        try:
            with transaction.atomic():
                for i in range(num_pacientes):
                    try:
                        # Generar datos del paciente
                        sexo = random.choice(['M', 'F'])
                        nombres_lista = NOMBRES_MASCULINOS if sexo == 'M' else NOMBRES_FEMENINOS
                        
                        nombre = random.choice(nombres_lista)
                        apellido_p = random.choice(APELLIDOS)
                        apellido_m = random.choice(APELLIDOS)
                        
                        nombres = f"{nombre} {random.choice(nombres_lista) if random.random() > 0.5 else ''}".strip()
                        apellidos = f"{apellido_p} {apellido_m}"

                        # Fecha de nacimiento aleatoria (entre 18 y 80 años)
                        años_atras = random.randint(18, 80)
                        fecha_nacimiento = timezone.now().date() - timedelta(days=años_atras * 365 + random.randint(0, 365))

                        # Teléfono aleatorio (70% de probabilidad)
                        telefono = None
                        if random.random() < 0.7:
                            telefono = f"229{random.randint(1000000, 9999999)}"

                        # Email aleatorio (50% de probabilidad)
                        email = None
                        if random.random() < 0.5:
                            email = f"{nombre.lower()}.{apellido_p.lower()}@ejemplo.com"

                        if skip_existing and telefono and Paciente.objects.filter(
                            empresa=empresa, telefono=telefono, nombres=nombres
                        ).exists():
                            pacientes_omitidos += 1
                            continue

                        paciente = Paciente.objects.create(
                            empresa=empresa,
                            sucursal=getattr(usuario_creador, 'sucursal', None),
                            nombres=nombres,
                            apellido_paterno=apellido_p,
                            apellido_materno=apellido_m,
                            fecha_nacimiento=fecha_nacimiento,
                            sexo=sexo,
                            telefono=telefono,
                            email=email,
                            tipo='GENERAL',
                        )
                        pacientes_creados += 1

                        # Crear 1 o 2 órdenes por paciente
                        num_ordenes = random.randint(1, 2)
                        
                        for j in range(num_ordenes):
                            # Fecha de creación aleatoria (últimos 7 días)
                            dias_atras = random.randint(0, 7)
                            fecha_creacion = timezone.now() - timedelta(days=dias_atras, hours=random.randint(0, 23))

                            rand = random.random()
                            if rand < 0.6:
                                estado_ods = 'PAGADO'
                                estado_pago = 'PAGADO'
                            elif rand < 0.8:
                                estado_ods = 'EN_PROCESO'
                                estado_pago = 'PAGADO'
                            else:
                                estado_ods = 'EN_PROCESO'
                                estado_pago = 'PAGADO'

                            core_paciente = paciente
                            num_estudios = random.randint(1, 5)
                            estudios_seleccionados = random.sample(estudios, min(num_estudios, len(estudios)))
                            total_orden = sum((e.precio_base or Decimal('0')) for e in estudios_seleccionados)

                            orden = OrdenDeServicio.objects.create(
                                empresa=empresa,
                                sucursal=getattr(usuario_creador, 'sucursal', None),
                                paciente=core_paciente,
                                responsable_ingreso=usuario_creador,
                                total=total_orden,
                                anticipo=Decimal('0'),
                                estado=estado_ods,
                                estado_pago=estado_pago,
                                estado_clinico='PENDIENTE_TOMA',
                            )
                            OrdenDeServicio.objects.filter(pk=orden.pk).update(fecha_creacion=fecha_creacion)
                            orden.refresh_from_db()

                            ordenes_creadas += 1

                            for estudio in estudios_seleccionados:
                                CoreDetalleOrden.objects.create(
                                    orden=orden,
                                    descripcion_linea=(estudio.nombre or '')[:300],
                                    precio_momento=estudio.precio_base or Decimal('0'),
                                )
                                detalles_creados += 1

                        # Progreso cada 10 pacientes
                        if (i + 1) % 10 == 0:
                            self.stdout.write(f'   [PROGRESO] Procesados {i + 1}/{num_pacientes} pacientes...')

                    except IntegrityError as e:
                        error_msg = f"Error de integridad en paciente {i+1}: {str(e)}"
                        errores.append(error_msg)
                        self.stdout.write(self.style.WARNING(f'   [AVISO] {error_msg}'))
                        continue
                    except Exception as e:
                        error_msg = f"Error inesperado en paciente {i+1}: {str(e)}"
                        errores.append(error_msg)
                        self.stdout.write(self.style.ERROR(f'   [ERROR] {error_msg}'))
                        continue

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[ERROR CRITICO] {str(e)}'))
            return

        # Calcular tiempo transcurrido
        tiempo_transcurrido = time.time() - inicio

        # Mostrar estadísticas finales
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('[RESUMEN] POBLADO COMPLETADO'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(f'[OK] Pacientes creados: {pacientes_creados}')
        if pacientes_omitidos > 0:
            self.stdout.write(f'[OMITIDOS] Pacientes omitidos: {pacientes_omitidos}')
        self.stdout.write(f'[OK] Ordenes creadas: {ordenes_creadas}')
        self.stdout.write(f'[OK] Detalles de orden creados: {detalles_creados}')
        self.stdout.write(f'[TIEMPO] Tiempo transcurrido: {tiempo_transcurrido:.2f} segundos')
        
        if errores:
            self.stdout.write(self.style.WARNING(f'\n[AVISO] Errores encontrados: {len(errores)}'))
            for error in errores[:5]:  # Mostrar solo los primeros 5
                self.stdout.write(self.style.WARNING(f'   - {error}'))
            if len(errores) > 5:
                self.stdout.write(self.style.WARNING(f'   ... y {len(errores) - 5} errores mas'))

        # Verificar distribución de estados
        self.stdout.write(self.style.SUCCESS('\n[ESTADISTICAS] DISTRIBUCION DE ESTADOS (ODS):'))
        total_ordenes = OrdenDeServicio.objects.filter(empresa=empresa).count()
        if total_ordenes > 0:
            pagado = OrdenDeServicio.objects.filter(empresa=empresa, estado='PAGADO').count()
            en_proceso = OrdenDeServicio.objects.filter(empresa=empresa, estado='EN_PROCESO').count()
            self.stdout.write(f'   PAGADO: {pagado} ({pagado/total_ordenes*100:.1f}%)')
            self.stdout.write(f'   EN_PROCESO: {en_proceso} ({en_proceso/total_ordenes*100:.1f}%)')

        self.stdout.write(self.style.SUCCESS('\n[COMPLETADO] Poblado exitoso!'))
        self.stdout.write(self.style.SUCCESS('   Los datos estan listos para pruebas de carga y estres.\n'))
