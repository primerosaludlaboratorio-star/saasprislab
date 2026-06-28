"""
Test de Estructura de Carpetas Drive (Pre-Stress Test)
======================================================
Genera 10 archivos de prueba (Laboratorio, Recetas, Audios) para validar
la jerarquía EMPRESA/AÑO/MES/DIA en Google Drive.

Empresas: laboratorio-del-valle, prislab-v5

Ejecutar: python manage.py test_estructura_drive
"""
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone

from core.models import (
    Empresa, Sucursal, Paciente, Medico, OrdenDeServicio,
    Receta, ConsultaMedica, AudioConsulta,
)
from core.models import get_google_drive_storage


# PNG 1x1 mínimo (imagen válida)
PNG_MINIMO = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
    0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
    0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
    0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
    0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
    0x44, 0xAE, 0x42, 0x60, 0x82
])

# WAV mínimo (44 bytes header + silencio)
WAV_MINIMO = (
    b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00'
    b'\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
)


def _generar_pdf_simple(folio: str, empresa: str) -> bytes:
    """PDF mínimo para prueba de estructura."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)
    p.drawString(100, 700, f"TEST ESTRUCTURA - {empresa}")
    p.drawString(100, 680, f"Folio: {folio}")
    p.drawString(100, 660, datetime.now().strftime("%Y-%m-%d %H:%M"))
    p.showPage()
    p.save()
    buf.seek(0)
    return buf.getvalue()


class Command(BaseCommand):
    help = 'Genera 10 archivos de prueba para validar estructura EMPRESA/AÑO/MES/DIA en Drive'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('\n=== TEST ESTRUCTURA DRIVE (10 archivos) ===\n'))

        if not getattr(__import__('django.conf', fromlist=['settings']).settings, 'GOOGLE_DRIVE_CREDENTIALS', None):
            self.stdout.write(self.style.ERROR('Drive no configurado. Configure OAuth2.'))
            return

        # 1. Empresas
        emp_valle, _ = Empresa.objects.get_or_create(
            nombre='Laboratorio del Valle',
            defaults={'rfc': 'LVL001', 'activa': True}
        )
        emp_prislab, _ = Empresa.objects.get_or_create(
            nombre='prislab-v5',
            defaults={'rfc': 'PRV501', 'activa': True}
        )

        # 2. Sucursales
        suc_valle, _ = Sucursal.objects.get_or_create(
            empresa=emp_valle,
            codigo_sucursal='LV-SUC-01',
            defaults={'nombre': 'Sucursal Valle'}
        )
        suc_prislab, _ = Sucursal.objects.get_or_create(
            empresa=emp_prislab,
            codigo_sucursal='PR-SUC-01',
            defaults={'nombre': 'Sucursal PRISLAB'}
        )

        # 3. Médico (compartido)
        medico = Medico.objects.filter(activo=True).first()
        if not medico:
            medico = Medico.objects.create(
                nombre_completo='Dr. Test Estructura',
                cedula_profesional=f'TEST-EST-{datetime.now().strftime("%Y%m%d%H%M")}',
                especialidad='Medicina General',
                activo=True
            )

        rutas_creadas = []

        # --- LABORATORIO: 3 PDFs (2 Valle, 1 PRISLAB) ---
        for i, (emp, suc) in enumerate([(emp_valle, suc_valle), (emp_valle, suc_valle), (emp_prislab, suc_prislab)]):
            pac = Paciente.objects.filter(empresa=emp).first()
            if not pac:
                pac = Paciente.objects.create(
                    empresa=emp,
                    nombre_completo=f'Paciente Test {emp.nombre[:10]} {i}',
                    fecha_nacimiento=datetime(1990, 1, 15).date(),
                    sexo='M'
                )
            orden = OrdenDeServicio.objects.create(
                empresa=emp,
                sucursal=suc,
                paciente=pac,
                total=Decimal('100.00'),
                anticipo=Decimal('100.00'),
                estado='ENTREGADO',
                folio_orden=f'TEST-EST-{emp.pk}-{datetime.now().strftime("%Y%m%d%H%M%S")}-{i+1:03d}',
            )
            pdf_bytes = _generar_pdf_simple(orden.folio_orden, emp.nombre)
            orden.archivo_resultado.save('test.pdf', ContentFile(pdf_bytes), save=True)
            rutas_creadas.append(('LAB', emp.nombre, orden.archivo_resultado.name))
            self.stdout.write(self.style.SUCCESS(f'  [OK] Lab PDF: {orden.archivo_resultado.name}'))

        # --- RECETAS: 3 firmas (2 PRISLAB, 1 Valle) ---
        for i, (emp, suc) in enumerate([(emp_prislab, suc_prislab), (emp_prislab, suc_prislab), (emp_valle, suc_valle)]):
            pac = Paciente.objects.filter(empresa=emp).first()
            if not pac:
                pac = Paciente.objects.create(
                    empresa=emp,
                    nombre_completo=f'Paciente Receta {emp.nombre[:10]} {i}',
                    fecha_nacimiento=datetime(1985, 5, 20).date(),
                    sexo='F'
                )
            receta = Receta.objects.create(
                empresa=emp,
                sucursal=suc,
                paciente=pac,
                medico=medico,
                medico_nombre_completo=medico.nombre_completo,
                medico_cedula=medico.cedula_profesional,
                diagnostico_principal='Test estructura',
                indicaciones='Paracetamol 500mg',
                folio_receta=f'REC-TEST-{emp.pk}-{datetime.now().strftime("%Y%m%d%H%M%S")}-{i+1:03d}',
            )
            receta.medico_firma_digital.save('firma_test.png', ContentFile(PNG_MINIMO), save=True)
            rutas_creadas.append(('RECETA', emp.nombre, receta.medico_firma_digital.name))
            self.stdout.write(self.style.SUCCESS(f'  [OK] Receta firma: {receta.medico_firma_digital.name}'))

        # --- AUDIOS: 4 (2 Valle, 2 PRISLAB) ---
        for i, (emp, suc) in enumerate([
            (emp_valle, suc_valle), (emp_valle, suc_valle),
            (emp_prislab, suc_prislab), (emp_prislab, suc_prislab)
        ]):
            pac = Paciente.objects.filter(empresa=emp).first()
            if not pac:
                pac = Paciente.objects.create(
                    empresa=emp,
                    nombre_completo=f'Paciente Audio {emp.nombre[:10]} {i}',
                    fecha_nacimiento=datetime(1978, 8, 10).date(),
                    sexo='M'
                )
            consulta = ConsultaMedica.objects.create(
                empresa=emp,
                sucursal=suc,
                paciente=pac,
                medico=medico,
                motivo_consulta='Test estructura Drive',
                padecimiento_actual='Control',
                exploracion_fisica='Normal',
                diagnostico_principal='Control',
                plan_tratamiento='Seguimiento',
                fecha_consulta=timezone.now(),
            )
            audio = AudioConsulta.objects.create(
                consulta=consulta,
                duracion_segundos=10,
                formato='wav',
                tamano_bytes=len(WAV_MINIMO),
                hash_sha256=f'TEST{emp.pk}{i}{datetime.now().strftime("%Y%m%d%H%M%S")}{i}',
                timestamp_inicio=timezone.now(),
                timestamp_fin=timezone.now(),
            )
            audio.audio_archivo.save('test.wav', ContentFile(WAV_MINIMO), save=True)
            rutas_creadas.append(('AUDIO', emp.nombre, audio.audio_archivo.name))
            self.stdout.write(self.style.SUCCESS(f'  [OK] Audio: {audio.audio_archivo.name}'))

        # Resumen
        self.stdout.write(self.style.SUCCESS('\n=== 10 ARCHIVOS CREADOS ===\n'))
        self.stdout.write('Verifica en Google Drive (PRISLAB_Media):\n')
        self.stdout.write('  - prislab-v5/2026/02/28/...\n')
        self.stdout.write('  - laboratorio-del-valle/2026/02/28/...\n')
        self.stdout.write('\nRutas generadas:')
        for tipo, emp, ruta in rutas_creadas:
            self.stdout.write(f'  [{tipo}] {ruta}')
