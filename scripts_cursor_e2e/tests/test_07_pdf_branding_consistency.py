"""Enfoque 7 — PDF resultados: texto legible (paciente / examen) sin error de generación."""
from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from pypdf import PdfReader

from core.models import DetalleOrden, Empresa, OrdenDeServicio, Paciente
from core.services.motor_reportes_lab import generar_reporte_pdf
from lims.models import Analito

User = get_user_model()


class PdfBrandingConsistencyTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa PDF Brand UX', rfc='PDF123456AAA')
        self.user = User.objects.create_user(
            username='pdf_brand_user',
            password='pdf-pass-88',
            empresa=self.empresa,
            rol='QUIMICO',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente Marca PDF',
            nombres='Paciente',
            apellido_paterno='Marca',
            fecha_nacimiento=date(1985, 6, 15),
            sexo='M',
        )
        self.analito = Analito.objects.create(
            empresa=self.empresa,
            codigo='PDF-NA',
            abreviatura='NA',
            nombre='Sodio PDF',
            departamento='Química',
            tipo_resultado='NUMERICO',
            unidades='mmol/L',
            es_calculado=False,
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('80.00'),
            anticipo=Decimal('80.00'),
            estado='EN_PROCESO',
            estado_pago='PAGADO',
            responsable_ingreso=self.user,
        )
        DetalleOrden.objects.create(
            orden=self.orden,
            analito=self.analito,
            precio_momento=Decimal('80.00'),
        )

    def test_pdf_contiene_identidad_paciente_y_tabla(self):
        pdf_bytes = generar_reporte_pdf(self.orden, request=None)
        self.assertGreater(len(pdf_bytes), 400)
        reader = PdfReader(BytesIO(pdf_bytes))
        text = ''.join((p.extract_text() or '') for p in reader.pages)
        upper = text.upper()
        self.assertIn('PACIENTE', upper)
        self.assertIn('MARCA', upper)
        self.assertIn('EXAMEN', upper)
