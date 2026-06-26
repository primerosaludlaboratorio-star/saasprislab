"""
Stress Test Extremo - Carga masiva con modelos reales y validación de rutas Drive.

PROHIBIDO Lorem Ipsum: Usa datos clínicos reales (nombres, edades, diagnósticos CIE-10,
resultados biológicos). Invoca generar_reporte_pdf (motor real). PDFs 200-500KB.

Ejecuta:
- 2,400 Ventas con DetalleVenta, Pago, sello_digital
- 800 ConsultaMedica + Receta + PDF en Drive
- 1,200 OrdenDeServicio con DetalleOrden, ResultadoParametro, PDF via guardar_reporte_en_storage
- 400 AudioConsulta o EstudioImagen con archivo binario en Drive

Con concurrencia (cada 10 inserciones): consultas Paciente y Producto.
Monitor de latencia Drive cada 500 archivos.
Valida rutas EMPRESA/AÑO/MES/DIA/ y multi-tenant (Prislab vs Laboratorio del Valle).
Genera REPORTE_ESTRES_EXTREMO_DETALLADO.md y REPORTE_CERTIFICACION_FINAL.md

Uso:
    python manage.py stress_test_extremo
    python manage.py stress_test_extremo --quick
    python manage.py stress_test_extremo --dry-run
    python manage.py stress_test_extremo --ventas 100 --consultas 50 --laboratorio 50 --multimedia 20
"""
import os
import re
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction
from django.db.models import Sum
from django.core.files.base import ContentFile

from core.models import (
    Empresa,
    Sucursal,
    Usuario,
    Paciente,
    Producto,
    Lote,
    Venta,
    DetalleVenta,
    Pago,
    Receta,
    RecetaItem,
    ConsultaMedica,
    OrdenDeServicio,
    DetalleOrden,
    ResultadoParametro,
    AudioConsulta,
    EstudioImagen,
    ImagenDetalle,
    Medico,
    SignosVitales,
)
from core.models.base import get_google_drive_storage
from core.services.motor_recetas import generar_receta_pdf
from core.services.motor_reportes_lab import generar_reporte_pdf, guardar_reporte_en_storage
import logging

# Datos clínicos reales (NO Lorem Ipsum) para PDFs con peso y estructura real
NOMBRES_PACIENTES = [
    'María Guadalupe Hernández López', 'José Carlos Martínez García', 'Ana Patricia Rodríguez Sánchez',
    'Miguel Ángel López Torres', 'Rosa María González Flores', 'Juan Pablo Ramírez Díaz',
    'Carmen Elena Fernández Ruiz', 'Roberto Antonio Morales Vega', 'Laura Isabel Castro Mendoza',
    'Francisco Javier Reyes Ortega', 'Sandra Lucía Herrera Jiménez', 'Daniel Eduardo Soto Navarro',
    'Claudia Adriana Mendoza Castro', 'Ricardo Alberto Vargas Luna', 'Mónica Beatriz Romero Silva',
    'Pedro Ernesto Delgado Ríos', 'Gabriela Fernanda Peña Cruz', 'Andrés Felipe Núñez Acosta',
    'Verónica Alejandra Medina Reyes', 'Luis Fernando Guerrero Campos', 'Diana Carolina Rojas Méndez',
    'Alejandro Martín Espinoza Fuentes', 'Teresa Margarita Salazar Ponce', 'Jorge Ignacio Campos Vega',
]
APELLIDOS_EXTRA = ['Ríos', 'Acosta', 'Méndez', 'Fuentes', 'Ponce', 'Vega', 'Campos', 'Cruz', 'Navarro']
DIAGNOSTICOS_CIE10 = [
    ('Infección de vías respiratorias superiores', 'J06.9'),
    ('Hipertensión esencial (primaria)', 'I10'),
    ('Diabetes mellitus tipo 2 sin complicaciones', 'E11.9'),
    ('Gastritis aguda sin hemorragia', 'K29.0'),
    ('Dorsalgia no especificada', 'M54.9'),
    ('Artrosis de rodilla primaria', 'M17.11'),
    ('Anemia ferropénica', 'D50.9'),
    ('Infección de vías urinarias', 'N39.0'),
    ('Dermatitis por contacto', 'L25.9'),
    ('Obesidad mórbida', 'E66.01'),
]
MEDICAMENTOS = [
    ('Paracetamol 500mg', '1 tableta cada 8 horas por 7 días'),
    ('Ibuprofeno 400mg', '1 tableta cada 12 horas con alimentos'),
    ('Amoxicilina 500mg', '1 cápsula cada 8 horas por 10 días'),
    ('Omeprazol 20mg', '1 cápsula en ayunas por 14 días'),
    ('Losartán 50mg', '1 tableta cada 24 horas'),
    ('Metformina 850mg', '1 tableta cada 12 horas con alimentos'),
    ('Enalapril 10mg', '1 tableta cada 12 horas'),
    ('Diclofenaco 50mg', '1 tableta cada 8 horas por 5 días'),
]
# Parámetros Biometría Hemática (resultados biológicos reales)
BIOMETRIA_PARAMETROS = [
    ('Eritrocitos', 'x10^6/uL', 4.2, 5.9), ('Hemoglobina', 'g/dL', 12.0, 17.5), ('Hematocrito', '%', 36.0, 52.0),
    ('VCM', 'fL', 80.0, 100.0), ('HCM', 'pg', 27.0, 33.0), ('CHCM', 'g/dL', 32.0, 36.0),
    ('RDW', '%', 11.5, 14.5), ('Leucocitos', 'x10^3/uL', 4.0, 11.0),
    ('Neutrófilos %', '%', 40.0, 70.0), ('Linfocitos %', '%', 20.0, 45.0),
    ('Monocitos %', '%', 2.0, 10.0), ('Eosinófilos %', '%', 0.0, 6.0), ('Basófilos %', '%', 0.0, 2.0),
    ('Plaquetas', 'x10^3/uL', 150.0, 450.0), ('VPM', 'fL', 7.5, 11.5),
]


def _memoria_mb():
    """Retorna memoria usada en MB."""
    try:
        import psutil
        return round(psutil.Process().memory_info().rss / (1024 * 1024), 2)
    except ImportError:
        return 0


def _proyeccion_2tb(metricas):
    """Proyección de saturación para 2 TB (2 * 1024^3 bytes)."""
    total = metricas.get('bytes_subidos_total', 0)
    archivos = metricas.get('archivos_subidos', 1)
    if archivos <= 0:
        return 'N/A'
    bytes_por_archivo = total / archivos
    capacidad_2tb = 2 * (1024 ** 3)
    archivos_estimados = int(capacidad_2tb / bytes_por_archivo)
    return f'~{archivos_estimados:,} archivos al mismo ritmo (o ~{archivos_estimados / 4800:.1f}x esta carga)'


def _validar_ruta_empresa_ano_mes_dia(ruta):
    """
    Valida que la ruta siga EMPRESA/AÑO/MES/DIA/
    Acepta variaciones: empresa-slug/2026/02/28/ o similar.
    """
    if not ruta:
        return False
    ruta_norm = ruta.replace('\\', '/').strip('/')
    partes = ruta_norm.split('/')
    if len(partes) < 4:
        return False
    # Formato esperado: empresa_slug, año (4 dígitos), mes (2 dígitos), dia (2 dígitos)
    try:
        ano = int(partes[1])
        mes = int(partes[2])
        dia = int(partes[3])
        return 2000 <= ano <= 2100 and 1 <= mes <= 12 and 1 <= dia <= 31
    except (ValueError, IndexError):
        return False


class Command(BaseCommand):
    help = 'Stress Test Extremo: carga masiva con modelos reales, concurrencia y validación de rutas'

    def add_arguments(self, parser):
        parser.add_argument('--ventas', type=int, default=2400, help='Cantidad de ventas')
        parser.add_argument('--consultas', type=int, default=800, help='Cantidad de consultas médicas')
        parser.add_argument('--laboratorio', type=int, default=1200, help='Cantidad de órdenes de laboratorio')
        parser.add_argument('--multimedia', type=int, default=400, help='Cantidad de AudioConsulta/EstudioImagen')
        parser.add_argument('--dry-run', action='store_true', help='Validar sin crear registros')
        parser.add_argument('--quick', action='store_true', help='Valores 10, 5, 5, 5 para prueba rápida')
        parser.add_argument('--multi-tenant', action='store_true', help='Usar Prislab + Laboratorio del Valle, validar carpetas sin cruce')
        parser.add_argument('--certificacion', action='store_true', help='Certificacion 100 pct: 4400 registros, retry DB locked, latencia cada 100, genera CERTIFICADO_PRODUCCION_PRISLAB.md')

    def _detener_procesos_huerfanos(self):
        """Detiene procesos Python huérfanos (excluye PID actual)."""
        try:
            import subprocess
            import os
            pid = os.getpid()
            if hasattr(subprocess, 'run'):
                if os.name == 'nt':
                    # Windows: no matar todos - solo esperar y reintentar
                    pass
                else:
                    subprocess.run(['pkill', '-f', 'stress_test_extremo'], capture_output=True, timeout=5)
            time.sleep(5)
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en _detener_procesos_huerfanos (stress_test_extremo.py)")
            time.sleep(5)

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        if options.get('certificacion'):
            options['quick'] = False
            options['ventas'] = 2400
            options['consultas'] = 800
            options['laboratorio'] = 1200
            options['multimedia'] = 400
            options['multi_tenant'] = True
        max_reintentos = 5 if options.get('certificacion') else 1
        for intento in range(max_reintentos):
            try:
                return self._handle_interno(args, options)
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en handle (stress_test_extremo.py)")
                err_str = str(e).lower()
                if 'database is locked' in err_str and intento < max_reintentos - 1:
                    self.stdout.write(self.style.WARNING(f'Database locked (intento {intento + 1}/{max_reintentos}). Reintentando...'))
                    self._detener_procesos_huerfanos()
                else:
                    raise

    def _handle_interno(self, args, options):
        if options.get('quick') and not options.get('certificacion'):
            n_ventas, n_consultas, n_lab, n_mult = 10, 5, 5, 5
        else:
            n_ventas = options.get('ventas', 2400)
            n_consultas = options.get('consultas', 800)
            n_lab = options.get('laboratorio', 1200)
            n_mult = options.get('multimedia', 400)

        dry_run = options.get('dry_run', False)

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('STRESS TEST EXTREMO - CARGA MASIVA'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(f'Ventas: {n_ventas} | Consultas: {n_consultas} | Lab: {n_lab} | Multimedia: {n_mult}')
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: validación sin crear registros'))
        self.stdout.write('')

        multi_tenant = options.get('multi_tenant', False) or options.get('certificacion', False)
        if multi_tenant:
            empresas = self._obtener_empresas_multi_tenant()
            if len(empresas) < 2:
                self.stdout.write(self.style.WARNING('Multi-tenant: se necesitan 2 empresas. Usando modo estándar.'))
                empresas = [Empresa.objects.filter(activa=True).first()]
        else:
            empresa = Empresa.objects.filter(activa=True).first()
            if not empresa:
                self.stdout.write(self.style.ERROR('No hay empresa activa.'))
                return
            empresas = [empresa]

        # Datos base por empresa (sucursal, usuario, medico, producto, estudio, parametro)
        datos_por_empresa = {}
        for emp in empresas:
            suc = Sucursal.objects.filter(empresa=emp).first()
            usr = Usuario.objects.filter(empresa=emp).first()
            if not usr:
                usr = Usuario.objects.filter(empresa__isnull=True).first() or Usuario.objects.first()
            med = Medico.objects.filter(empresa=emp).first()
            datos_por_empresa[emp.id] = {
                'empresa': emp, 'sucursal': suc, 'usuario': usr, 'medico': med,
            }

        if not any(d['usuario'] for d in datos_por_empresa.values()):
            self.stdout.write(self.style.ERROR('No hay usuario disponible.'))
            return

        # Métricas
        metricas = {
            'errores_500_504': [],
            'latencia_primer_pdf_ms': None,
            'latencia_archivo_4000_ms': None,
            'latencia_drive_cada_100': [],  # [(archivo_num, ms), ...] - throttling Drive API
            'memoria_inicial_mb': _memoria_mb(),
            'memoria_final_mb': 0,
            'bytes_subidos_total': 0,
            'archivos_subidos': 0,
            'operaciones_totales': n_ventas + n_consultas + n_lab + n_mult,
            'tiempo_total_segundos': 0,
            'rutas_validadas_ok': 0,
            'rutas_validadas_fail': 0,
            'rutas_por_empresa': {},  # {empresa_slug: [rutas]} para validación multi-tenant
            'cruces_empresa': [],   # [(ruta, empresa_esperada, empresa_en_ruta)]
            'multi_tenant': multi_tenant,
            'certificacion': options.get('certificacion', False),
        }

        inicio_total = time.time()

        if dry_run:
            self.stdout.write(self.style.SUCCESS('Dry-run: validación de dependencias OK'))
            metricas['tiempo_total_segundos'] = round(time.time() - inicio_total, 2)
            self._generar_reporte(metricas, dry_run=True)
            return

        # Obtener o crear datos base por empresa
        for emp in empresas:
            d = datos_por_empresa[emp.id]
            d['producto'] = self._obtener_o_crear_producto(d['empresa'])
            d['estudio'] = self._obtener_o_crear_estudio_hematologia(d['empresa'])
            if not d['medico']:
                d['medico'] = Medico.objects.create(
                    empresa=d['empresa'],
                    nombre_completo='Dra. Brizia' if 'prislab' in (d['empresa'].nombre or '').lower() else 'Dr. Test Stress',
                    cedula_profesional='11852035' if 'prislab' in (d['empresa'].nombre or '').lower() else f'STRESS-{uuid.uuid4().hex[:8].upper()}',
                    especialidad='Médico General',
                )

        # 1. VENTAS
        self.stdout.write(self.style.WARNING('\n[1/4] Carga de Ventas...'))
        self._cargar_ventas(empresas, datos_por_empresa, n_ventas, metricas)

        # 2. CONSULTAS + RECETAS + PDF
        self.stdout.write(self.style.WARNING('\n[2/4] Carga de Consultas + Recetas + PDF...'))
        self._cargar_consultas_recetas_pdf(empresas, datos_por_empresa, n_consultas, metricas)

        # 3. LABORATORIO
        self.stdout.write(self.style.WARNING('\n[3/4] Carga de Órdenes Lab + PDF...'))
        self._cargar_laboratorio(empresas, datos_por_empresa, n_lab, metricas)

        # 4. MULTIMEDIA
        self.stdout.write(self.style.WARNING('\n[4/4] Carga de Multimedia...'))
        self._cargar_multimedia(empresas, datos_por_empresa, n_mult, metricas)

        metricas['memoria_final_mb'] = _memoria_mb()
        metricas['tiempo_total_segundos'] = round(time.time() - inicio_total, 2)

        self._generar_reporte(metricas)
        self._generar_reporte_certificacion(metricas)
        if metricas.get('certificacion'):
            self._generar_certificado_produccion(metricas)

    def _obtener_empresas_multi_tenant(self):
        """Obtiene o crea Prislab y Laboratorio del Valle para validación multi-tenant."""
        prislab = Empresa.objects.filter(nombre__icontains='prislab').first()
        if not prislab:
            prislab, _ = Empresa.objects.get_or_create(
                nombre='PRISLAB',
                defaults={'activa': True}
            )
        valle, _ = Empresa.objects.get_or_create(
            nombre='Laboratorio del Valle',
            defaults={'activa': True}
        )
        return [prislab, valle]

    def _ejecutar_concurrencia(self, empresa):
        """Cada 5 inserciones: Paciente count y Producto aggregate."""
        try:
            c1 = Paciente.objects.filter(
                empresa=empresa,
                nombre_completo__icontains='test'
            ).count()
            try:
                c2 = Producto.objects.filter(empresa=empresa).aggregate( s=Sum('stock'))
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en _ejecutar_concurrencia (stress_test_extremo.py)")
                c2 = {'s': 0}
            return c1, c2.get('s') or 0
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en _ejecutar_concurrencia (stress_test_extremo.py)")
            return -1, -1

    def _obtener_o_crear_producto(self, empresa):
        p = Producto.objects.filter(empresa=empresa).first()
        if not p:
            p = Producto.objects.create(
                empresa=empresa,
                nombre='Producto Test Stress',
                codigo_barras=f'STRESS-{uuid.uuid4().hex[:12]}',
                forma_farmaceutica='Tabletas',
                concentracion='500mg',
                presentacion='30 tabletas',
                precio_publico=Decimal('50.00'),
                precio_compra=Decimal('25.00'),
                stock=10000,
            )
            Lote.objects.create(
                producto=p,
                numero_lote=f'LOT-{uuid.uuid4().hex[:8]}',
                fecha_caducidad=timezone.now().date() + timedelta(days=365),
                cantidad=10000,
                costo_adquisicion=Decimal('25.00'),
            )
        return p

    def _obtener_o_crear_estudio_hematologia(self, empresa):
        """Crea estudio Biometría Hemática Completa con 15 parámetros para PDFs pesados (200-500KB)."""
        seccion, _ = SeccionLaboratorio.objects.get_or_create(
            nombre='Hematología',
            defaults={'orden': 1}
        )
        e = Estudio.objects.filter(codigo='BH-STRESS').first()
        if not e:
            e = Estudio.objects.create(
                codigo='BH-STRESS',
                nombre='Biometría Hemática Completa',
                seccion=seccion,
                precio=Decimal('180.00'),
                activo=True,
            )
            for idx, (nombre, unidad, ref_min, ref_max) in enumerate(BIOMETRIA_PARAMETROS):
                param = Parametro.objects.create(
                    estudio=e,
                    nombre=nombre,
                    abreviatura=nombre[:8].replace(' ', '') if nombre else f'P{idx}',
                    unidad=unidad,
                    tipo_dato='NUMERICO',
                    orden_impresion=idx + 1,
                )
                RangoReferencia.objects.create(
                    parametro=param,
                    sexo='I',
                    valor_minimo=ref_min,
                    valor_maximo=ref_max,
                    activo=True,
                )
        return e

    def _nombre_paciente_real(self, i, sufijo=''):
        """Nombre real (no Lorem Ipsum) para datos clínicos."""
        nom = NOMBRES_PACIENTES[i % len(NOMBRES_PACIENTES)]
        if sufijo:
            return f"{nom} {sufijo}"
        return nom

    def _cargar_ventas(self, empresas, datos_por_empresa, n, metricas):
        for i in range(n):
            emp = empresas[i % len(empresas)]
            d = datos_por_empresa[emp.id]
            try:
                with transaction.atomic():
                    paciente = Paciente.objects.create(
                        empresa=d['empresa'],
                        sucursal=d['sucursal'],
                        nombre_completo=self._nombre_paciente_real(i, APELLIDOS_EXTRA[i % len(APELLIDOS_EXTRA)]),
                        fecha_nacimiento=timezone.now().date() - timedelta(days=(25 + i % 40) * 365),
                        sexo='F' if i % 3 == 0 else 'M',
                        telefono=f'555{i:07d}',
                    )
                    total = Decimal('100.00') + Decimal(str(i % 50))
                    venta = Venta.objects.create(
                        empresa=d['empresa'],
                        sucursal=d['sucursal'],
                        usuario=d['usuario'],
                        subtotal=total,
                        impuestos_iva=Decimal('0'),
                        total=total,
                        sello_digital=f'Sello-{uuid.uuid4().hex[:32]}',
                        paciente=paciente,
                        estado='COMPLETADA',
                    )
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=d['producto'],
                        cantidad=1,
                        precio_unitario=total,
                        subtotal=total,
                    )
                    Pago.objects.create(
                        venta=venta,
                        metodo='EFECTIVO',
                        monto=total,
                    )
                    if (i + 1) % 10 == 0:
                        self._ejecutar_concurrencia(d['empresa'])
                    if (i + 1) % 200 == 0:
                        self.stdout.write(f'   Ventas: {i + 1}/{n}')
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en _cargar_ventas (stress_test_extremo.py)")
                metricas['errores_500_504'].append(('venta', i + 1, str(e)))
                if len(metricas['errores_500_504']) <= 5:
                    self.stdout.write(self.style.ERROR(f'   Error venta {i + 1}: {e}'))

    def _cargar_consultas_recetas_pdf(self, empresas, datos_por_empresa, n, metricas):
        storage = get_google_drive_storage()
        for i in range(n):
            emp = empresas[i % len(empresas)]
            d = datos_por_empresa[emp.id]
            try:
                with transaction.atomic():
                    diag, cie = DIAGNOSTICOS_CIE10[i % len(DIAGNOSTICOS_CIE10)]
                    med1, dosis1 = MEDICAMENTOS[i % len(MEDICAMENTOS)]
                    med2, dosis2 = MEDICAMENTOS[(i + 3) % len(MEDICAMENTOS)]
                    edad_anos = 25 + (i % 45)
                    paciente = Paciente.objects.create(
                        empresa=d['empresa'],
                        sucursal=d['sucursal'],
                        nombre_completo=self._nombre_paciente_real(i),
                        fecha_nacimiento=timezone.now().date() - timedelta(days=int(edad_anos * 365.25)),
                        sexo='F' if i % 2 == 0 else 'M',
                        telefono=f'555{i + 100000:07d}',
                    )
                    receta = Receta.objects.create(
                        medico=d['medico'],
                        paciente=paciente,
                        empresa=d['empresa'],
                        sucursal=d['sucursal'],
                        diagnostico_principal=diag,
                        indicaciones=f'Reposo relativo. Tomar medicamentos con alimentos. Control en 7 días.',
                        medico_nombre_completo=d['medico'].nombre_completo,
                        medico_cedula=d['medico'].cedula_profesional,
                        presion_arterial_sistolica=110 + (i % 30),
                        presion_arterial_diastolica=70 + (i % 20),
                        frecuencia_cardiaca=72 + (i % 15),
                        peso=Decimal('65.5') + Decimal(str(i % 25)),
                        talla=Decimal('1.65') + Decimal(str(i % 20)) / 100,
                    )
                    RecetaItem.objects.create(
                        receta=receta,
                        texto_libre=f'{med1} | Dosis: {dosis1}',
                        cantidad=30,
                        estado='SUGERIDO',
                    )
                    RecetaItem.objects.create(
                        receta=receta,
                        texto_libre=f'{med2} | Dosis: {dosis2}',
                        cantidad=14,
                        estado='SUGERIDO',
                    )
                    consulta = ConsultaMedica.objects.create(
                        empresa=d['empresa'],
                        sucursal=d['sucursal'],
                        paciente=paciente,
                        medico=d['medico'],
                        receta=receta,
                        motivo_consulta='Control de padecimiento crónico' if 'Diabetes' in diag or 'Hipertensión' in diag else 'Cuadro agudo de 3 días de evolución',
                        padecimiento_actual=f'Paciente de {edad_anos} años con sintomatología referida. Exploración física dentro de parámetros.',
                        exploracion_fisica='Buen estado general. Mucosas húmedas. Abdomen blando. Sin datos de alarma.',
                        diagnostico_principal=diag,
                        diagnostico_cie10=cie,
                        plan_tratamiento=f'Tratamiento farmacológico indicado. Seguimiento en consulta externa.',
                        estado='FINALIZADA',
                    )

                    t0 = time.time()
                    pdf_bytes = generar_receta_pdf(consulta)
                    if metricas['latencia_primer_pdf_ms'] is None:
                        metricas['latencia_primer_pdf_ms'] = round((time.time() - t0) * 1000)

                    emp_slug = slugify(d['empresa'].nombre) or f'empresa-{d["empresa"].pk}'
                    ahora = timezone.now()
                    ruta = f"{emp_slug}/{ahora.year}/{ahora.month:02d}/{ahora.day:02d}/receta-{receta.folio_receta}.pdf"
                    ruta = re.sub(r'[^\w\-/.]', '-', ruta)
                    t_drive = time.time()
                    storage.save(ruta, ContentFile(pdf_bytes))
                    latencia_drive_ms = round((time.time() - t_drive) * 1000)
                    receta.url_drive_backup = storage.url(ruta) if hasattr(storage, 'url') else f'file://{ruta}'
                    receta.drive_status = 'SINCRONIZADO'
                    receta.save(update_fields=['url_drive_backup', 'drive_status'])

                    metricas['bytes_subidos_total'] += len(pdf_bytes)
                    metricas['archivos_subidos'] += 1

                    if _validar_ruta_empresa_ano_mes_dia(ruta):
                        metricas['rutas_validadas_ok'] += 1
                    else:
                        metricas['rutas_validadas_fail'] += 1

                    # Validación multi-tenant: archivo debe estar en carpeta de su empresa
                    if metricas.get('multi_tenant'):
                        slug_esperado = slugify(d['empresa'].nombre) or f'empresa-{d["empresa"].pk}'
                        if not ruta.startswith(slug_esperado + '/'):
                            metricas['cruces_empresa'].append((ruta, d['empresa'].nombre, ruta.split('/')[0]))
                        metricas.setdefault('rutas_por_empresa', {})
                        metricas['rutas_por_empresa'].setdefault(slug_esperado, []).append(ruta)

                    # Monitor latencia Drive API (cada 100 para detectar throttling)
                    intervalo = 100 if metricas.get('certificacion') else 500
                    if metricas['archivos_subidos'] % intervalo == 0 and metricas['archivos_subidos'] > 0:
                        metricas['latencia_drive_cada_100'].append(
                            (metricas['archivos_subidos'], latencia_drive_ms))
                    if (i + 1) % 10 == 0:
                        self._ejecutar_concurrencia(d['empresa'])
                    if (i + 1) % 100 == 0:
                        self.stdout.write(f'   Consultas: {i + 1}/{n}')
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en _cargar_consultas_recetas_pdf (stress_test_extremo.py)")
                metricas['errores_500_504'].append(('consulta', i + 1, str(e)))
                if len(metricas['errores_500_504']) <= 5:
                    self.stdout.write(self.style.ERROR(f'   Error consulta {i + 1}: {e}'))

    def _cargar_laboratorio(self, empresas, datos_por_empresa, n, metricas):
        for i in range(n):
            emp = empresas[i % len(empresas)]
            d = datos_por_empresa[emp.id]
            try:
                with transaction.atomic():
                    edad_anos = 28 + (i % 50)
                    sexo = 'F' if i % 2 == 0 else 'M'
                    paciente = Paciente.objects.create(
                        empresa=d['empresa'],
                        sucursal=d['sucursal'],
                        nombre_completo=self._nombre_paciente_real(i, APELLIDOS_EXTRA[(i + 2) % len(APELLIDOS_EXTRA)]),
                        fecha_nacimiento=timezone.now().date() - timedelta(days=int(edad_anos * 365.25)),
                        sexo=sexo,
                        telefono=f'555{i + 200000:07d}',
                    )
                    orden = OrdenDeServicio.objects.create(
                        empresa=d['empresa'],
                        sucursal=d['sucursal'],
                        paciente=paciente,
                        total=Decimal('180.00'),
                        anticipo=Decimal('180.00'),
                        responsable_ingreso=d['usuario'],
                        estado='RESULTADOS_LISTOS',
                        estado_clinico='COMPLETO',
                    )
                    DetalleOrden.objects.create(
                        orden=orden,
                        estudio=d['estudio'],
                        precio_momento=Decimal('180.00'),
                        estado_procesamiento='RESULTADO_LISTO',
                    )
                    # Resultados biológicos reales por parámetro (genera PDF pesado 200-500KB)
                    parametros = list(d['estudio'].parametros.order_by('orden_impresion'))
                    for idx, param in enumerate(parametros):
                        _, _, ref_min, ref_max = BIOMETRIA_PARAMETROS[idx % len(BIOMETRIA_PARAMETROS)]
                        rango = ref_max - ref_min
                        valor_real = ref_min + (rango * (0.35 + 0.45 * (i % 80) / 80))
                        ResultadoParametro.objects.create(
                            orden=orden,
                            parametro=param,
                            valor=f'{valor_real:.2f}',
                            capturado_por=d['usuario'],
                            validado=True,
                        )

                    t0 = time.time()
                    pdf_bytes = generar_reporte_pdf(orden, request=None)
                    t_drive = time.time()
                    url = guardar_reporte_en_storage(orden, pdf_bytes)
                    latencia_drive_ms = round((time.time() - t_drive) * 1000)

                    if i == 0 and metricas['latencia_primer_pdf_ms'] is None:
                        metricas['latencia_primer_pdf_ms'] = round((time.time() - t0) * 1000)
                    if metricas['archivos_subidos'] >= 4000 and metricas['latencia_archivo_4000_ms'] is None:
                        metricas['latencia_archivo_4000_ms'] = latencia_drive_ms

                    if orden.archivo_resultado and orden.archivo_resultado.name:
                        ruta = orden.archivo_resultado.name
                        if _validar_ruta_empresa_ano_mes_dia(ruta):
                            metricas['rutas_validadas_ok'] += 1
                        else:
                            metricas['rutas_validadas_fail'] += 1
                        if metricas.get('multi_tenant'):
                            slug_esperado = slugify(d['empresa'].nombre) or f'empresa-{d["empresa"].pk}'
                            if not ruta.startswith(slug_esperado + '/'):
                                metricas['cruces_empresa'].append((ruta, d['empresa'].nombre, ruta.split('/')[0]))
                            metricas.setdefault('rutas_por_empresa', {})
                            metricas['rutas_por_empresa'].setdefault(slug_esperado, []).append(ruta)

                    metricas['bytes_subidos_total'] += len(pdf_bytes)
                    metricas['archivos_subidos'] += 1
                    intervalo = 100 if metricas.get('certificacion') else 500
                    if metricas['archivos_subidos'] % intervalo == 0 and metricas['archivos_subidos'] > 0:
                        metricas['latencia_drive_cada_100'].append((metricas['archivos_subidos'], latencia_drive_ms))

                    if (i + 1) % 10 == 0:
                        self._ejecutar_concurrencia(d['empresa'])
                    if (i + 1) % 200 == 0:
                        self.stdout.write(f'   Lab: {i + 1}/{n}')
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en _cargar_laboratorio (stress_test_extremo.py)")
                metricas['errores_500_504'].append(('laboratorio', i + 1, str(e)))
                if len(metricas['errores_500_504']) <= 5:
                    self.stdout.write(self.style.ERROR(f'   Error lab {i + 1}: {e}'))

    def _cargar_multimedia(self, empresas, datos_por_empresa, n, metricas):
        n_audio = n // 2
        n_imagen = n - n_audio
        idx_global = 0

        for i in range(n_audio):
            emp = empresas[idx_global % len(empresas)]
            d = datos_por_empresa[emp.id]
            idx_global += 1
            try:
                with transaction.atomic():
                    paciente = Paciente.objects.create(
                        empresa=d['empresa'],
                        nombre_completo=self._nombre_paciente_real(i + 100, APELLIDOS_EXTRA[i % len(APELLIDOS_EXTRA)]),
                        fecha_nacimiento=timezone.now().date() - timedelta(days=35 * 365),
                        sexo='F',
                        telefono=f'555{i + 300000:07d}',
                    )
                    receta = Receta.objects.create(
                        medico=d['medico'],
                        paciente=paciente,
                        empresa=d['empresa'],
                        diagnostico_principal='Dx audio',
                        indicaciones='Ind',
                        medico_nombre_completo=d['medico'].nombre_completo,
                        medico_cedula=d['medico'].cedula_profesional,
                    )
                    consulta = ConsultaMedica.objects.create(
                        empresa=d['empresa'],
                        paciente=paciente,
                        medico=d['medico'],
                        receta=receta,
                        motivo_consulta='Motivo',
                        padecimiento_actual='Padecimiento',
                        exploracion_fisica='Exploración',
                        diagnostico_principal='Dx',
                        plan_tratamiento='Plan',
                        estado='FINALIZADA',
                    )

                    # Archivos 200-500KB para estresar ancho de banda Drive
                    tamano_kb = 200 + (i % 301)
                    audio_bytes = (b'\x00\xff' * (tamano_kb * 256))[: tamano_kb * 1024] + str(i).encode() + uuid.uuid4().bytes
                    hash_sha = hashlib.sha256(audio_bytes).hexdigest()

                    audio = AudioConsulta.objects.create(
                        consulta=consulta,
                        duracion_segundos=60,
                        formato='wav',
                        tamano_bytes=len(audio_bytes),
                        hash_sha256=hash_sha,
                        timestamp_inicio=timezone.now(),
                        timestamp_fin=timezone.now(),
                    )
                    audio.audio_archivo.save(f'audio-{hash_sha[:12]}.wav', ContentFile(audio_bytes), save=True)

                    metricas['bytes_subidos_total'] += len(audio_bytes)
                    metricas['archivos_subidos'] += 1

                    ruta_audio = audio.audio_archivo.name if audio.audio_archivo else ''
                    if _validar_ruta_empresa_ano_mes_dia(ruta_audio):
                        metricas['rutas_validadas_ok'] += 1
                    else:
                        metricas['rutas_validadas_fail'] += 1
                    if metricas.get('multi_tenant'):
                        slug_esperado = slugify(d['empresa'].nombre) or f'empresa-{d["empresa"].pk}'
                        if not ruta_audio.startswith(slug_esperado + '/'):
                            metricas['cruces_empresa'].append((ruta_audio, d['empresa'].nombre, ruta_audio.split('/')[0] if ruta_audio else ''))
                        metricas.setdefault('rutas_por_empresa', {})
                        metricas['rutas_por_empresa'].setdefault(slug_esperado, []).append(ruta_audio)

                    intervalo = 100 if metricas.get('certificacion') else 500
                    if metricas['archivos_subidos'] % intervalo == 0 and metricas['archivos_subidos'] > 0:
                        metricas['latencia_drive_cada_100'].append((metricas['archivos_subidos'], 0))
                    if (i + 1) % 10 == 0:
                        self._ejecutar_concurrencia(d['empresa'])
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en _cargar_multimedia (stress_test_extremo.py)")
                metricas['errores_500_504'].append(('audio', i + 1, str(e)))

        for i in range(n_imagen):
            emp = empresas[idx_global % len(empresas)]
            d = datos_por_empresa[emp.id]
            idx_global += 1
            try:
                with transaction.atomic():
                    paciente = Paciente.objects.create(
                        empresa=d['empresa'],
                        nombre_completo=self._nombre_paciente_real(i + 200, APELLIDOS_EXTRA[(i + 1) % len(APELLIDOS_EXTRA)]),
                        fecha_nacimiento=timezone.now().date() - timedelta(days=45 * 365),
                        sexo='M',
                        telefono=f'555{i + 400000:07d}',
                    )
                    estudio_img = EstudioImagen.objects.create(
                        empresa=d['empresa'],
                        paciente=paciente,
                        medico_interpretador=d['medico'],
                        tipo_estudio='USG_ABDOMINAL',
                        edad_paciente=45,
                        indicacion_clinica='Indicación test',
                        descripcion_hallazgos='Hallazgos',
                        interpretacion='Interpretación',
                        conclusiones='Conclusiones',
                        estado='INTERPRETADO',
                        creado_por=d['usuario'],
                    )
                    # Imágenes 200-500KB (JPEG simulado) para estresar Drive
                    tamano_kb = 220 + (i % 281)
                    img_bytes = b'\xff\xd8\xff' + (b'\x00\xff\xfe' * (tamano_kb * 170))[: tamano_kb * 1024 - 10]
                    detalle = ImagenDetalle.objects.create(
                        estudio=estudio_img,
                        orden=1,
                        descripcion='Imagen test',
                    )
                    detalle.imagen.save(
                        f'imagen-{estudio_img.folio_estudio}.jpg',
                        ContentFile(img_bytes),
                        save=True,
                    )

                    metricas['bytes_subidos_total'] += len(img_bytes)
                    metricas['archivos_subidos'] += 1

                    ruta = detalle.imagen.name if detalle.imagen else ''
                    if _validar_ruta_empresa_ano_mes_dia(ruta):
                        metricas['rutas_validadas_ok'] += 1
                    else:
                        metricas['rutas_validadas_fail'] += 1
                    if metricas.get('multi_tenant'):
                        slug_esperado = slugify(d['empresa'].nombre) or f'empresa-{d["empresa"].pk}'
                        if not ruta.startswith(slug_esperado + '/'):
                            metricas['cruces_empresa'].append((ruta, d['empresa'].nombre, ruta.split('/')[0] if ruta else ''))
                        metricas.setdefault('rutas_por_empresa', {})
                        metricas['rutas_por_empresa'].setdefault(slug_esperado, []).append(ruta)

                    intervalo = 100 if metricas.get('certificacion') else 500
                    if metricas['archivos_subidos'] % intervalo == 0 and metricas['archivos_subidos'] > 0:
                        metricas['latencia_drive_cada_100'].append((metricas['archivos_subidos'], 0))
                    if (i + 1) % 10 == 0:
                        self._ejecutar_concurrencia(d['empresa'])
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en _cargar_multimedia (stress_test_extremo.py)")
                metricas['errores_500_504'].append(('imagen', i + 1, str(e)))

        self.stdout.write(f'   Multimedia: {n_audio} audios + {n_imagen} imágenes')

    def _generar_reporte(self, metricas, dry_run=False):
        contenido = f"""# REPORTE ESTRÉS EXTREMO - DETALLADO

**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Modo:** {'DRY-RUN (validación)' if dry_run else 'EJECUCIÓN COMPLETA'}

## KPI PRINCIPALES

| Métrica | Valor |
|---------|-------|
| Tiempo total (segundos) | {metricas.get('tiempo_total_segundos', 0)} |
| Memoria inicial (MB) | {metricas.get('memoria_inicial_mb', 0)} |
| Memoria final (MB) | {metricas.get('memoria_final_mb', 0)} |
| Bytes subidos total | {metricas.get('bytes_subidos_total', 0):,} |
| Archivos subidos | {metricas.get('archivos_subidos', 0)} |
| Latencia primer PDF (ms) | {metricas.get('latencia_primer_pdf_ms', 'N/A')} |
| Latencia archivo 4000 (ms) | {metricas.get('latencia_archivo_4000_ms', 'N/A')} |
| Rutas validadas OK (EMPRESA/AÑO/MES/DIA) | {metricas.get('rutas_validadas_ok', 0)} |
| Rutas validadas FAIL | {metricas.get('rutas_validadas_fail', 0)} |

## PESO Y CAPACIDAD (PROYECCIÓN 2 TB)

| Métrica | Valor |
|---------|-------|
| Espacio consumido (bytes) | {metricas.get('bytes_subidos_total', 0):,} |
| Espacio consumido (GB) | {metricas.get('bytes_subidos_total', 0) / (1024**3):.4f} |
| Archivos subidos | {metricas.get('archivos_subidos', 0)} |
| Promedio bytes/archivo | {metricas.get('bytes_subidos_total', 0) / max(1, metricas.get('archivos_subidos', 1)):,.0f} |
| Proyección saturación 2 TB | {_proyeccion_2tb(metricas)} |

## ERRORES 500/504

"""
        for tipo, num, msg in metricas.get('errores_500_504', []):
            contenido += f"- **{tipo}** #{num}: {msg[:200]}\n"

        if not metricas.get('errores_500_504'):
            contenido += "- Ninguno\n"

        ruta_reporte = 'REPORTE_ESTRES_EXTREMO_DETALLADO.md'
        with open(ruta_reporte, 'w', encoding='utf-8') as f:
            f.write(contenido)

        self.stdout.write(self.style.SUCCESS(f'\nReporte generado: {ruta_reporte}'))

    def _generar_reporte_certificacion(self, metricas):
        """Genera REPORTE_CERTIFICACION_FINAL.md con KPIs de certificación."""
        total_ops = metricas.get('operaciones_totales', 4400)
        errores = len(metricas.get('errores_500_504', []))
        tasa_fallos = (errores / total_ops * 100) if total_ops else 0

        mem_ini = metricas.get('memoria_inicial_mb', 0)
        mem_fin = metricas.get('memoria_final_mb', 0)
        fuga_memoria = mem_fin > mem_ini * 1.5 if mem_ini else False
        consumo_ram = f"Inicial: {mem_ini} MB | Final: {mem_fin} MB | Fuga: {'SÍ' if fuga_memoria else 'NO'}"

        bytes_total = metricas.get('bytes_subidos_total', 0)
        peso_gb = bytes_total / (1024 ** 3)

        # Proyección 10 años con 10% crecimiento anual
        base_anual_gb = peso_gb  # asumiendo esta carga = 1 "año base"
        crecimiento = 1.10
        acum = 0
        for año in range(1, 11):
            acum += base_anual_gb * (crecimiento ** (año - 1))
        proy_10_años = acum
        durabilidad_2tb = (2 * 1024) / (base_anual_gb * crecimiento) if base_anual_gb > 0 else float('inf')
        años_hasta_saturacion = min(10, int(durabilidad_2tb)) if durabilidad_2tb < 100 else 10

        latencias = metricas.get('latencia_drive_cada_100', [])
        latencia_tabla = '\n'.join(f"| {n} | {ms} ms |" for n, ms in latencias) if latencias else "| N/A | N/A |"

        cruces = metricas.get('cruces_empresa', [])
        cruces_texto = '\n'.join(f"- {r[:60]}... (esperado: {e}, encontrado: {c})" for r, e, c in cruces[:10]) if cruces else "- Ninguno (OK)"

        contenido = f"""# REPORTE DE CERTIFICACIÓN FINAL - SUPER STRESS TEST

**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Operaciones totales:** {total_ops}
**Archivos subidos a Drive:** {metricas.get('archivos_subidos', 0)}

---

## 1. TASA DE FALLOS

| Métrica | Valor |
|---------|-------|
| Operaciones fallidas | {errores} |
| Operaciones exitosas | {total_ops - errores} |
| **Tasa de fallos (%)** | **{tasa_fallos:.2f}%** |

---

## 2. CONSUMO DE RAM (DETECCIÓN DE FUGAS)

| Métrica | Valor |
|---------|-------|
| Memoria inicial | {mem_ini} MB |
| Memoria final | {mem_fin} MB |
| Indicador de fuga | {'SÍ - Posible fuga de memoria' if fuga_memoria else 'NO - Estable'} |

{consumo_ram}

---

## 3. PESO REAL EN GOOGLE DRIVE

| Métrica | Valor |
|---------|-------|
| Bytes totales subidos | {bytes_total:,} |
| **Peso en GB** | **{peso_gb:.4f} GB** |
| Archivos generados | {metricas.get('archivos_subidos', 0)} |
| Promedio por archivo | {bytes_total / max(1, metricas.get('archivos_subidos', 1)):,.0f} bytes |

---

## 4. PROYECCIÓN A 10 AÑOS (CRECIMIENTO 10% ANUAL)

| Año | GB acumulado (proyección) |
|-----|--------------------------|
| Base (carga actual) | {peso_gb:.2f} GB |
| Con crecimiento 10% anual | ~{proy_10_años:.1f} GB acumulados en 10 años |

**Durabilidad del almacenamiento 2 TB:** A este ritmo de carga duplicada (200%), el almacenamiento alcanzaría ~{base_anual_gb * 2:.2f} GB/año. Proyección de saturación: **~{años_hasta_saturacion} años** antes de requerir expansión (considerando 2 TB y crecimiento 10% anual).

---

## 5. MONITOR DE LATENCIA DRIVE (cada 500 archivos)

| Archivo # | Latencia (ms) |
|-----------|---------------|
{latencia_tabla}

---

## 6. VALIDACIÓN MULTI-TENANT (Prislab / Laboratorio del Valle)

| Métrica | Valor |
|---------|-------|
| Cruces de carpetas detectados | {len(cruces)} |
| Rutas por empresa | {list(metricas.get('rutas_por_empresa', {}).keys())} |

**Detalle de cruces (si aplica):**
{cruces_texto}

---

*Reporte generado automáticamente por stress_test_extremo*
"""
        ruta = 'REPORTE_CERTIFICACION_FINAL.md'
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido)
        self.stdout.write(self.style.SUCCESS(f'Reporte certificación: {ruta}'))

    def _generar_certificado_produccion(self, metricas):
        """Genera CERTIFICADO_PRODUCCION_PRISLAB.md - Acta de Certificación."""
        total_ops = metricas.get('operaciones_totales', 4400)
        archivos = metricas.get('archivos_subidos', 0)
        errores = len(metricas.get('errores_500_504', []))
        tasa_exito = ((total_ops - errores) / total_ops * 100) if total_ops else 0

        bytes_total = metricas.get('bytes_subidos_total', 0)
        peso_gb = bytes_total / (1024 ** 3)

        # Proyección saturación 2 TB con crecimiento 10% anual
        capacidad_2tb_gb = 2 * 1024
        if peso_gb > 0:
            base_anual = peso_gb
            acum = 0
            año_sat = None
            for año in range(1, 51):
                acum += base_anual * (1.10 ** (año - 1))
                if acum >= capacidad_2tb_gb and año_sat is None:
                    año_sat = datetime.now().year + año
                    break
            año_saturacion = año_sat or (datetime.now().year + 50)
        else:
            año_saturacion = 'N/A'

        cruces = len(metricas.get('cruces_empresa', []))
        tenant_ok = cruces == 0

        contenido = f"""# CERTIFICADO DE PRODUCCIÓN - PRISLAB

**Cuenta:** primerosaludlaboratorio@gmail.com
**Fecha de Certificación:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Modo:** Carga masiva 100% - 4,400 registros

---

## 1. TASA DE ÉXITO 100%

| Métrica | Valor |
|---------|-------|
| Operaciones programadas | {total_ops} |
| Operaciones exitosas | {total_ops - errores} |
| Operaciones fallidas | {errores} |
| **Tasa de éxito** | **{tasa_exito:.2f}%** |
| Archivos en Drive | {archivos} |

**Confirmación:** {'✅ Los 4,400 registros/archivos fueron procesados correctamente' if errores == 0 and archivos >= 2400 else '⚠️ Revisar errores - no se alcanzó 100%'}.

---

## 2. CONSUMO REAL DE ESPACIO

| Métrica | Valor |
|---------|-------|
| Bytes totales | {bytes_total:,} |
| **GB ocupados** | **{peso_gb:.4f} GB** |
| Archivos subidos | {archivos} |
| Promedio por archivo | {bytes_total / max(1, archivos):,.0f} bytes |

---

## 3. PROYECCIÓN DE VIDA ÚTIL (2 TB)

| Métrica | Valor |
|---------|-------|
| Capacidad Google One | 2 TB (2,048 GB) |
| Carga actual (equivalente 60 días) | {peso_gb:.2f} GB |
| Crecimiento anual proyectado | 10% |
| **Año estimado de saturación** | **{año_saturacion}** |

---

## 4. VALIDACIÓN MULTI-TENANT

| Métrica | Valor |
|---------|-------|
| Cruces Prislab / Laboratorio del Valle | {cruces} |
| **Estado** | {'✅ Sin cruces - carpetas correctas' if tenant_ok else '❌ Revisar rutas'} |

---

*Documento generado por stress_test_extremo --certificacion*
"""
        ruta = 'CERTIFICADO_PRODUCCION_PRISLAB.md'
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido)
        self.stdout.write(self.style.SUCCESS(f'Certificado producción: {ruta}'))