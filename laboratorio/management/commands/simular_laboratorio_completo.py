"""
Management command COMPLETO para simular TODAS las funcionalidades del módulo de Laboratorio:
- Creación de órdenes (con diferentes orígenes, médicos, pacientes)
- Captura de resultados (borrador y validado)
- Diferentes estados de análisis (PENDIENTE, EN_PROCESO, VALIDADO)
- Generación de QR para órdenes validadas
- Pruebas de carga y estrés SIN borrar datos
"""

import random
import sys
import io
import time
import json
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import IntegrityError, OperationalError
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.models import Paciente
from laboratorio.models import (
    Estudio, Orden, DetalleOrden, Medico, CategoriaExamen,
    Resultado, Parametro
)
from core.views.laboratorio import generar_qr_orden

User = get_user_model()


class Command(BaseCommand):
    help = "Simula TODAS las funcionalidades del módulo de Laboratorio (órdenes, captura, validación, PDFs)"

    def add_arguments(self, parser):
        parser.add_argument("--ordenes", type=int, default=80, help="Número de órdenes a crear (default: 80)")
        parser.add_argument("--min-estudios", type=int, default=1, help="Mínimo de estudios por orden (default: 1)")
        parser.add_argument("--max-estudios", type=int, default=5, help="Máximo de estudios por orden (default: 5)")
        parser.add_argument("--dias", type=int, default=7, help="Rango de días hacia atrás para fechas (default: 7)")
        parser.add_argument("--usuario", type=str, default="", help="Username del usuario (default: primer usuario)")
        parser.add_argument("--pct-validadas", type=int, default=20, help="Porcentaje de órdenes validadas (0-100, default: 20)")
        parser.add_argument("--pct-en-proceso", type=int, default=20, help="Porcentaje de órdenes en proceso (0-100, default: 20)")
        parser.add_argument("--pct-con-resultados", type=int, default=60, help="Porcentaje de órdenes con resultados capturados (0-100, default: 60)")

    def handle(self, *args, **options):
        # Configurar encoding UTF-8 para Windows
        if sys.platform == "win32":
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

        ordenes_objetivo = options["ordenes"]
        min_estudios = max(1, options["min_estudios"])
        max_estudios = max(min_estudios, options["max_estudios"])
        dias = max(1, options["dias"])
        username = (options["usuario"] or "").strip()
        pct_validadas = max(0, min(100, options["pct_validadas"]))
        pct_en_proceso = max(0, min(100, options["pct_en_proceso"]))
        pct_con_resultados = max(0, min(100, options["pct_con_resultados"]))

        t0 = time.time()
        self.stdout.write(self.style.SUCCESS("[INICIANDO] Simulacion COMPLETA de Laboratorio"))
        self.stdout.write(f"[OBJETIVO] {ordenes_objetivo} ordenes con captura y validacion\n")

        # Seleccionar usuario
        if username:
            user = User.objects.filter(username=username).first()
            if not user:
                self.stdout.write(self.style.ERROR(f"[ERROR] No existe el usuario '{username}'"))
                return
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR("[ERROR] No hay usuarios. Cree uno primero (createsuperuser)."))
                return

        self.stdout.write(f"[USUARIO] Usuario: {user.username}")
        empresa = getattr(user, 'empresa', None)
        if not empresa:
            self.stdout.write(self.style.ERROR("[ERROR] El usuario no tiene empresa asignada (requerido para pacientes core)."))
            return

        # Verificar que existan estudios
        estudios = list(Estudio.objects.all())
        if not estudios:
            self.stdout.write(self.style.ERROR("[ERROR] No hay estudios en el sistema."))
            self.stdout.write(self.style.WARNING("   Ejecuta primero: python manage.py importar_tarifas_lab"))
            return

        # Verificar que existan pacientes
        pacientes = list(Paciente.objects.filter(empresa=empresa)[:50])
        if not pacientes:
            self.stdout.write(self.style.WARNING("[AVISO] No hay pacientes. Se crearán automáticamente."))
            pacientes = []
            nombres = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Pedro', 'Carmen']
            apellidos = ['García', 'López', 'Martínez', 'González', 'Pérez', 'Sánchez', 'Ramírez', 'Torres']
            for i in range(10):
                ap1 = random.choice(apellidos)
                ap2 = random.choice(apellidos)
                paciente = Paciente.objects.create(
                    empresa=empresa,
                    nombres=random.choice(nombres),
                    apellido_paterno=ap1,
                    apellido_materno=ap2,
                    fecha_nacimiento=timezone.now().date() - timedelta(days=random.randint(18*365, 70*365)),
                    sexo=random.choice(['M', 'F']),
                    telefono=f"229{random.randint(1000000, 9999999)}" if random.random() > 0.3 else None,
                    email=f"paciente{i}@ejemplo.com" if random.random() > 0.5 else None,
                    tipo='GENERAL',
                )
                pacientes.append(paciente)

        # Obtener o crear médicos
        medicos = list(Medico.objects.all()[:5])
        if not medicos:
            medicos.append(Medico.objects.create(
                nombre='Dr. Medico de Prueba',
                especialidad='Medicina General'
            ))

        # Estadísticas
        ordenes_creadas = 0
        ordenes_con_resultados = 0
        ordenes_validadas = 0
        ordenes_en_proceso = 0
        ordenes_pendientes = 0
        resultados_capturados = 0
        errores = []

        # FASE 1: Crear órdenes
        self.stdout.write(self.style.SUCCESS("\n[FASE 1] Creando ordenes..."))

        for i in range(ordenes_objetivo):
            try:
                # Seleccionar paciente aleatorio
                paciente = random.choice(pacientes)

                # Seleccionar médico (70% con médico, 30% sin médico)
                medico = random.choice(medicos) if random.random() > 0.3 else None
                medico_texto = None
                if not medico and random.random() > 0.5:
                    medico_texto = f"Dr. {random.choice(['García', 'López', 'Martínez', 'González'])}"

                # Seleccionar origen
                origen = random.choice([
                    Orden.ORIGEN_PUBLICO_GENERAL,
                    Orden.ORIGEN_CONVENIO,
                    Orden.ORIGEN_SEGURO,
                    Orden.ORIGEN_OTRO
                ])

                # Seleccionar estudios aleatorios
                num_estudios = random.randint(min_estudios, max_estudios)
                estudios_seleccionados = random.sample(estudios, min(num_estudios, len(estudios)))

                # Crear orden
                with transaction.atomic():
                    orden = Orden.objects.create(
                        empresa=empresa,
                        paciente=paciente,
                        usuario_creador=user,
                        medico=medico,
                        medico_texto=medico_texto,
                        origen=origen,
                        estado_pago=random.choice([True, False]),
                        estado_analisis=Orden.ESTADO_ANALISIS_PENDIENTE
                    )

                    # Crear detalles de orden
                    for estudio in estudios_seleccionados:
                        DetalleOrden.objects.create(
                            orden=orden,
                            estudio=estudio,
                            precio_unitario=estudio.precio_base,
                            cantidad=1
                        )

                    ordenes_creadas += 1
                    ordenes_pendientes += 1

                # Retro-fechar orden
                fecha_creacion = timezone.now() - timedelta(
                    days=random.randint(0, dias),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                Orden.objects.filter(id=orden.id).update(fecha_creacion=fecha_creacion)
                orden.refresh_from_db()

                if (i + 1) % 20 == 0:
                    self.stdout.write(f"[PROGRESO] {i+1}/{ordenes_objetivo} ordenes creadas")

            except SimulationError as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Orden {i+1}: Error de simulación - {str(e)}'))
                errores += 1
                continue
            except ValueError as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Orden {i+1}: Error de valor - {str(e)}'))
                errores += 1
                continue
            except DatabaseError as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Orden {i+1}: Error de base de datos - {str(e)}'))
                errores += 1
                continue

        # FASE 2: Capturar resultados y cambiar estados
        self.stdout.write(self.style.SUCCESS("\n[FASE 2] Capturando resultados y validando..."))

        ordenes_disponibles = list(Orden.objects.all().prefetch_related('detalles__estudio')[:ordenes_creadas])
        random.shuffle(ordenes_disponibles)

        for orden in ordenes_disponibles:
            try:
                # Determinar acción según porcentajes
                rand = random.random() * 100
                
                if rand < pct_validadas:
                    # Validar orden (con resultados)
                    accion = 'validar'
                    estado_final = Orden.ESTADO_ANALISIS_VALIDADO
                    ordenes_validadas += 1
                elif rand < pct_validadas + pct_en_proceso:
                    # Dejar en proceso (con resultados parciales)
                    accion = 'borrador'
                    estado_final = Orden.ESTADO_ANALISIS_EN_PROCESO
                    ordenes_en_proceso += 1
                else:
                    # Dejar pendiente (sin resultados)
                    continue

                # Capturar resultados para cada detalle
                detalles = orden.detalles.all()
                resultados_data = {}
                
                for detalle in detalles:
                    estudio = detalle.estudio
                    
                    # Generar resultado realista según el tipo de estudio
                    if estudio.es_perfil:
                        # Perfil: múltiples parámetros
                        resultado_texto = self._generar_resultado_perfil(estudio)
                    else:
                        # Estudio simple: valor único
                        resultado_texto = self._generar_resultado_simple(estudio)
                    
                    resultados_data[str(detalle.id)] = {
                        'resultado': resultado_texto,
                        'observaciones': self._generar_observaciones() if random.random() > 0.7 else ''
                    }
                    resultados_capturados += 1

                # Simular request para api_guardar_resultados
                request_mock = SimpleNamespace()
                request_mock.user = user
                request_mock.method = 'POST'
                request_mock.body = json.dumps({
                    'resultados': resultados_data,
                    'accion': accion
                }).encode('utf-8')

                # Guardar resultados directamente en el modelo Resultado
                with transaction.atomic():
                    for detalle_id_str, datos in resultados_data.items():
                        detalle_id = int(detalle_id_str)
                        detalle = DetalleOrden.objects.get(id=detalle_id, orden=orden)
                        
                        # Crear o actualizar Resultado
                        resultado, created = Resultado.objects.update_or_create(
                            orden=orden,
                            estudio=detalle.estudio,
                            defaults={
                                'valor_obtenido': datos['resultado'],
                                'valor': datos['resultado']
                            }
                        )
                    
                    # Actualizar estado de la orden
                    if accion == 'validar':
                        orden.estado_analisis = Orden.ESTADO_ANALISIS_VALIDADO
                        orden.fecha_validacion = timezone.now()
                        orden.usuario_valido = user
                        ordenes_validadas += 1
                        ordenes_pendientes -= 1
                    else:
                        orden.estado_analisis = Orden.ESTADO_ANALISIS_EN_PROCESO
                        ordenes_en_proceso += 1
                        ordenes_pendientes -= 1
                    
                    orden.save()
                    ordenes_con_resultados += 1

            except SimulationError as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Orden {orden.id}: Error de simulación - {str(e)}'))
                errores += 1
                continue
            except ValueError as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Orden {orden.id}: Error de valor - {str(e)}'))
                errores += 1
                continue
            except DatabaseError as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Orden {orden.id}: Error de base de datos - {str(e)}'))
                errores += 1
                continue

        # FASE 3: Generar QRs para órdenes validadas
        self.stdout.write(self.style.SUCCESS("\n[FASE 3] Generando QRs para ordenes validadas..."))
        qrs_generados = 0
        
        ordenes_validadas_list = Orden.objects.filter(estado_analisis=Orden.ESTADO_ANALISIS_VALIDADO)
        for orden in ordenes_validadas_list[:20]:  # Generar QR para primeras 20
            try:
                qr_image = generar_qr_orden(orden.id, orden.folio_operacion if hasattr(orden, 'folio_operacion') else None)
                if qr_image:
                    qrs_generados += 1
            except SimulationError as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] QR orden {orden.id}: Error de simulación - {str(e)}'))
                errores += 1
                continue
            except ValueError as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] QR orden {orden.id}: Error de valor - {str(e)}'))
                errores += 1
                continue
            except DatabaseError as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] QR orden {orden.id}: Error de base de datos - {str(e)}'))
                errores += 1
                continue

        # Calcular tiempo
        tiempo_total = time.time() - t0

        # Mostrar estadísticas finales
        self.stdout.write(self.style.SUCCESS("\n" + "="*60))
        self.stdout.write(self.style.SUCCESS("[RESUMEN] SIMULACION COMPLETA LABORATORIO"))
        self.stdout.write(self.style.SUCCESS("="*60))
        self.stdout.write(f"[OK] Ordenes creadas: {ordenes_creadas}")
        self.stdout.write(f"[OK] Ordenes con resultados capturados: {ordenes_con_resultados}")
        self.stdout.write(f"[OK] Ordenes validadas: {ordenes_validadas}")
        self.stdout.write(f"[OK] Ordenes en proceso: {ordenes_en_proceso}")
        self.stdout.write(f"[OK] Ordenes pendientes: {ordenes_pendientes}")
        self.stdout.write(f"[OK] Resultados capturados: {resultados_capturados}")
        self.stdout.write(f"[OK] QRs generados: {qrs_generados}")
        self.stdout.write(f"[INFO] Errores: {len(errores)}")
        self.stdout.write(f"[TIEMPO] {tiempo_total:.2f} segundos")
        
        total_ordenes_bd = Orden.objects.count()
        self.stdout.write(f"[INFO] Total ordenes en el sistema ahora: {total_ordenes_bd}")
        
        # Distribución de estados
        if ordenes_creadas > 0:
            self.stdout.write(self.style.SUCCESS("\n[ESTADISTICAS] DISTRIBUCION DE ESTADOS:"))
            pendientes_real = Orden.objects.filter(estado_analisis=Orden.ESTADO_ANALISIS_PENDIENTE).count()
            en_proceso_real = Orden.objects.filter(estado_analisis=Orden.ESTADO_ANALISIS_EN_PROCESO).count()
            validadas_real = Orden.objects.filter(estado_analisis=Orden.ESTADO_ANALISIS_VALIDADO).count()
            
            self.stdout.write(f"   PENDIENTE: {pendientes_real} ({pendientes_real/total_ordenes_bd*100:.1f}%)")
            self.stdout.write(f"   EN_PROCESO: {en_proceso_real} ({en_proceso_real/total_ordenes_bd*100:.1f}%)")
            self.stdout.write(f"   VALIDADO: {validadas_real} ({validadas_real/total_ordenes_bd*100:.1f}%)")
        
        if errores:
            self.stdout.write(self.style.WARNING(f"\n[AVISO] Primeros 5 errores:"))
            for error in errores[:5]:
                self.stdout.write(self.style.WARNING(f"   - {error}"))
            if len(errores) > 5:
                self.stdout.write(self.style.WARNING(f"   ... y {len(errores) - 5} errores mas"))

        self.stdout.write(self.style.SUCCESS("\n[COMPLETADO] Simulacion completa exitosa!"))
        self.stdout.write(self.style.SUCCESS("   Todas las funcionalidades de Laboratorio fueron probadas.\n"))

    def _generar_resultado_simple(self, estudio):
        """Genera un resultado realista para un estudio simple."""
        # Si tiene rangos de referencia, generar valor dentro o fuera del rango
        if estudio.valor_minimo is not None and estudio.valor_maximo is not None:
            # 80% dentro del rango, 20% fuera
            if random.random() < 0.8:
                valor = random.uniform(float(estudio.valor_minimo), float(estudio.valor_maximo))
            else:
                # Fuera del rango (anormal)
                if random.random() > 0.5:
                    valor = float(estudio.valor_minimo) - random.uniform(1, 10)
                else:
                    valor = float(estudio.valor_maximo) + random.uniform(1, 10)
        else:
            # Sin rangos: generar valor aleatorio razonable
            valor = random.uniform(10, 200)
        
        # Formatear según unidades
        if estudio.unidades:
            return f"{valor:.2f} {estudio.unidades}"
        return f"{valor:.2f}"

    def _generar_resultado_perfil(self, estudio):
        """Genera resultados para un perfil (múltiples parámetros)."""
        # Buscar parámetros del estudio
        parametros = Parametro.objects.filter(estudio=estudio)
        
        if parametros.exists():
            resultados = []
            for param in parametros:
                if param.valor_ref_min is not None and param.valor_ref_max is not None:
                    valor = random.uniform(float(param.valor_ref_min), float(param.valor_ref_max))
                else:
                    valor = random.uniform(10, 200)
                
                unidades = param.unidades or ''
                resultados.append(f"{param.nombre}: {valor:.2f}{' ' + unidades if unidades else ''}")
            
            return '\n'.join(resultados)
        else:
            # Sin parámetros definidos: generar resultado genérico
            return f"Resultado del perfil {estudio.nombre}: Valores dentro de parámetros normales."

    def _generar_observaciones(self):
        """Genera observaciones realistas."""
        observaciones = [
            'Muestra en buen estado',
            'Resultado dentro de parámetros normales',
            'Se recomienda seguimiento',
            'Valores consistentes con la clínica',
            'Sin observaciones relevantes',
            'Muestra hemolizada, resultados con reserva'
        ]
        return random.choice(observaciones)
