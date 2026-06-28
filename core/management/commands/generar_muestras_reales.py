"""
Genera 3 resultados de laboratorio y 3 recetas de consultorio
exactamente como los genera el personal en producción.

Usa los motores reales: generar_reporte_pdf y generar_receta_pdf.
Guarda en Drive (o media local) con la estructura EMPRESA/AÑO/MES/DIA.

Ejecutar: python manage.py generar_muestras_reales
"""
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify
from django.core.files.base import ContentFile
from django.conf import settings

from core.models import (
    Empresa, Sucursal, Usuario, Paciente, Medico,
    OrdenDeServicio, DetalleOrden, ResultadoParametro,
    Receta, RecetaItem, ConsultaMedica,
)
from core.models.base import get_google_drive_storage
from core.services.motor_recetas import generar_receta_pdf
from core.services.motor_reportes_lab import generar_reporte_pdf, guardar_reporte_en_storage

BIOMETRIA_PARAMETROS = [
    ('Eritrocitos', 'x10^6/uL', 4.2, 5.9), ('Hemoglobina', 'g/dL', 12.0, 17.5), ('Hematocrito', '%', 36.0, 52.0),
    ('VCM', 'fL', 80.0, 100.0), ('HCM', 'pg', 27.0, 33.0), ('CHCM', 'g/dL', 32.0, 36.0),
    ('RDW', '%', 11.5, 14.5), ('Leucocitos', 'x10^3/uL', 4.0, 11.0),
    ('Neutrófilos %', '%', 40.0, 70.0), ('Linfocitos %', '%', 20.0, 45.0),
    ('Plaquetas', 'x10^3/uL', 150.0, 450.0),
]


class Command(BaseCommand):
    help = 'Genera 3 PDFs de laboratorio y 3 de consultorio como en producción'

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        self.stdout.write(self.style.SUCCESS('\n=== GENERACIÓN DE MUESTRAS REALES ===\n'))

        empresa = Empresa.objects.filter(activa=True).first()
        if not empresa:
            self.stdout.write(self.style.ERROR('No hay empresa activa.'))
            return

        sucursal = Sucursal.objects.filter(empresa=empresa).first()
        usuario = Usuario.objects.filter(empresa=empresa).first() or Usuario.objects.first()
        medico = Medico.objects.filter(empresa=empresa).first()
        if not medico:
            medico = Medico.objects.create(
                empresa=empresa,
                nombre_completo='Dra. Brizia',
                cedula_profesional='11852035',
                especialidad='Médico General',
            )

        estudio = self._obtener_estudio_hematologia()
        rutas_lab = []
        rutas_consulta = []

        # --- 3 RESULTADOS DE LABORATORIO ---
        self.stdout.write(self.style.WARNING('\n[1/2] Generando 3 resultados de laboratorio...'))
        for i in range(3):
            paciente = Paciente.objects.create(
                empresa=empresa,
                sucursal=sucursal,
                nombre_completo=f'Juan Pérez García {i+1}',
                fecha_nacimiento=timezone.now().date() - timedelta(days=35*365),
                sexo='M',
                telefono=f'555123456{i}',
            )
            orden = OrdenDeServicio.objects.create(
                empresa=empresa,
                sucursal=sucursal,
                paciente=paciente,
                total=Decimal('180.00'),
                anticipo=Decimal('180.00'),
                responsable_ingreso=usuario,
                estado='RESULTADOS_LISTOS',
                estado_clinico='COMPLETO',
            )
            DetalleOrden.objects.create(
                orden=orden,
                estudio=estudio,
                precio_momento=Decimal('180.00'),
                estado_procesamiento='RESULTADO_LISTO',
            )
            for idx, param in enumerate(estudio.parametros.order_by('orden_impresion')):
                _, _, ref_min, ref_max = BIOMETRIA_PARAMETROS[idx % len(BIOMETRIA_PARAMETROS)]
                valor = ref_min + (ref_max - ref_min) * 0.5
                ResultadoParametro.objects.create(
                    orden=orden,
                    parametro=param,
                    valor=f'{valor:.2f}',
                    capturado_por=usuario,
                    validado=True,
                )

            pdf_bytes = generar_reporte_pdf(orden, request=None)
            url = guardar_reporte_en_storage(orden, pdf_bytes)
            ruta = orden.archivo_resultado.name if orden.archivo_resultado else ''
            rutas_lab.append((orden.folio_orden, ruta, url))
            self.stdout.write(self.style.SUCCESS(f'  [OK] Lab {i+1}: {orden.folio_orden}'))

        # --- 3 RECETAS DE CONSULTORIO ---
        self.stdout.write(self.style.WARNING('\n[2/2] Generando 3 recetas de consultorio...'))
        storage = get_google_drive_storage()
        ahora = timezone.now()

        for i in range(3):
            paciente = Paciente.objects.create(
                empresa=empresa,
                sucursal=sucursal,
                nombre_completo=f'María López Hernández {i+1}',
                fecha_nacimiento=timezone.now().date() - timedelta(days=28*365),
                sexo='F',
                telefono=f'555987654{i}',
            )
            receta = Receta.objects.create(
                medico=medico,
                paciente=paciente,
                empresa=empresa,
                sucursal=sucursal,
                diagnostico_principal='Infección de vías respiratorias superiores',
                indicaciones='Reposo. Tomar con alimentos. Control en 7 días.',
                medico_nombre_completo=medico.nombre_completo,
                medico_cedula=medico.cedula_profesional,
                presion_arterial_sistolica=118,
                presion_arterial_diastolica=76,
                frecuencia_cardiaca=72,
                peso=Decimal('62.5'),
                talla=Decimal('1.62'),
            )
            RecetaItem.objects.create(
                receta=receta,
                texto_libre='Paracetamol 500mg | 1 tableta cada 8 horas por 7 días',
                cantidad=21,
                estado='SUGERIDO',
            )
            RecetaItem.objects.create(
                receta=receta,
                texto_libre='Amoxicilina 500mg | 1 cápsula cada 8 horas por 10 días',
                cantidad=30,
                estado='SUGERIDO',
            )
            consulta = ConsultaMedica.objects.create(
                empresa=empresa,
                sucursal=sucursal,
                paciente=paciente,
                medico=medico,
                receta=receta,
                motivo_consulta='Cuadro agudo de 3 días de evolución',
                padecimiento_actual='Tos, rinorrea, dolor de garganta.',
                exploracion_fisica='Buen estado general. Orofaringe congestiva.',
                diagnostico_principal='Infección de vías respiratorias superiores',
                diagnostico_cie10='J06.9',
                plan_tratamiento='Tratamiento farmacológico indicado.',
                estado='FINALIZADA',
            )

            pdf_bytes = generar_receta_pdf(consulta)
            emp_slug = slugify(empresa.nombre) or f'empresa-{empresa.pk}'
            ruta = f"{emp_slug}/{ahora.year}/{ahora.month:02d}/{ahora.day:02d}/receta-{receta.folio_receta}.pdf"
            storage.save(ruta, ContentFile(pdf_bytes))
            receta.url_drive_backup = storage.url(ruta) if hasattr(storage, 'url') else ''
            receta.drive_status = 'SINCRONIZADO'
            receta.save(update_fields=['url_drive_backup', 'drive_status'])

            rutas_consulta.append((receta.folio_receta, ruta))
            self.stdout.write(self.style.SUCCESS(f'  [OK] Receta {i+1}: {receta.folio_receta}'))

        # --- RESUMEN Y CARPETA ---
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('ARCHIVOS GENERADOS - UBICACIÓN'))
        self.stdout.write('=' * 60)

        es_drive = 'GoogleDriveStorage' in str(type(get_google_drive_storage()))
        if es_drive:
            carpeta_base = 'Google Drive > PRISLAB_Media'
            self.stdout.write(f'\nCarpeta base: {carpeta_base}')
        else:
            media_root = getattr(settings, 'MEDIA_ROOT', 'media')
            carpeta_base = str(media_root)
            self.stdout.write(f'\nCarpeta base (local): {carpeta_base}')

        self.stdout.write('\n--- LABORATORIO (3 PDFs) ---')
        for folio, ruta, url in rutas_lab:
            self.stdout.write(f'  {folio}: {ruta}')
            if url:
                self.stdout.write(f'    URL: {url}')

        self.stdout.write('\n--- CONSULTORIO (3 recetas) ---')
        for folio, ruta in rutas_consulta:
            self.stdout.write(f'  {folio}: {ruta}')

        # Carpeta exacta para revisar (EMPRESA/AÑO/MES/DIA)
        emp_slug = slugify(empresa.nombre) or f'empresa-{empresa.pk}'
        carpeta_exacta = f'{carpeta_base}/{emp_slug}/{ahora.year}/{ahora.month:02d}/{ahora.day:02d}/'
        self.stdout.write(self.style.SUCCESS('\n[CARPETA PARA REVISAR] (EMPRESA/ANO/MES/DIA):'))
        self.stdout.write(self.style.SUCCESS(f'   {carpeta_exacta}'))
        self.stdout.write(self.style.SUCCESS('\n[OK] Revisa los archivos en la carpeta indicada arriba.'))

    def _obtener_estudio_hematologia(self):
        seccion, _ = SeccionLaboratorio.objects.get_or_create(
            nombre='Hematología', defaults={'orden': 1}
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
