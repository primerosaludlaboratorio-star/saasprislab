"""
v1.48 — Robot Chemist (heredado v1.46): regresión PDF, FEFO calculado, partial escudo IA.

Ubicación: ``scripts_cursor_e2e/`` para validación Cursor independiente de Cascade.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase

from core.models import Empresa, OrdenDeServicio, Paciente, ResultadoParametro
from core.services.motor_reportes_lab import generar_reporte_pdf
from inventario.models import (
    CatalogoReactivoLab,
    ConsumoEstudioReactivo,
    LoteReactivoLab,
    SalidaAnaliticaLab,
)
from lims.models import Analito

User = get_user_model()


class RobotChemistPdfCapturaTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Emp Robot Chemist', rfc='ROB123456AAA')
        self.user = User.objects.create_user(
            username='robot_chemist',
            password='rc-secret-99',
            empresa=self.empresa,
            rol='QUIMICO',
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente RC',
            nombres='Paciente',
            apellido_paterno='RC',
            fecha_nacimiento=date(1992, 5, 10),
            sexo='M',
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('100.00'),
            anticipo=Decimal('100.00'),
            estado='EN_PROCESO',
            estado_pago='PAGADO',
            responsable_ingreso=self.user,
        )
        self.client = Client()
        self.client.force_login(self.user)

    @patch('core.views.laboratorio_reportes.paciente_autorizado_canal_digital_resultados', return_value=True)
    def test_imprimir_resultados_devuelve_pdf_200(self, mock_auth):
        r = self.client.get(f'/laboratorio/imprimir/{self.orden.id}/', follow=True)
        self.assertIn(r.status_code, [200, 301, 302], getattr(r, 'content', b'')[:500])
        self.assertEqual(r.get('Content-Type'), 'application/pdf')
        self.assertGreater(len(r.content), 200, 'PDF demasiado pequeño o vacío')

    def test_generar_reporte_pdf_bytes_sin_error(self):
        pdf = generar_reporte_pdf(self.orden, request=None)
        self.assertIsInstance(pdf, (bytes, bytearray))
        self.assertGreater(len(pdf), 200)

    def test_captura_industrial_responde_200_sin_lineas(self):
        r = self.client.get(f'/laboratorio/captura/{self.orden.id}/', follow=True)
        self.assertEqual(r.status_code, 200)


class RobotChemistFefoTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Emp RC FEFO', rfc='RCF123456AAA')
        self.user = User.objects.create_user(
            username='rc_fefo',
            password='secret123',
            empresa=self.empresa,
            rol='ADMIN',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Pac FEFO',
            nombres='Pac',
            apellido_paterno='FEFO',
            fecha_nacimiento=date(1990, 1, 1),
            sexo='M',
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('50.00'),
            anticipo=Decimal('0'),
            estado='EN_PROCESO',
            estado_pago='PAGADO',
            responsable_ingreso=self.user,
        )

    def test_fefo_analito_calculado_sin_salida_analitica(self):
        calc = Analito.objects.create(
            empresa=self.empresa,
            codigo='RC-CALC',
            abreviatura='CALC',
            nombre='Calculado RC',
            departamento='Química',
            es_calculado=True,
            formula='1',
        )
        reactivo = CatalogoReactivoLab.objects.create(
            empresa=self.empresa,
            codigo_interno='R-RC',
            nombre='Reactivo RC',
        )
        ConsumoEstudioReactivo.objects.create(
            empresa=self.empresa,
            analito=calc,
            reactivo=reactivo,
            cantidad_por_prueba=Decimal('2.0000'),
            unidad='UL',
            activo=True,
        )
        LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=reactivo,
            numero_lote='L-RC',
            fecha_caducidad=date(2031, 1, 1),
            cantidad_inicial=Decimal('50'),
            cantidad_actual=Decimal('50'),
            estado='ACTIVO',
        )
        ResultadoParametro.objects.create(
            orden=self.orden,
            analito=calc,
            valor='1',
            capturado_por=self.user,
            validado=True,
            validado_por=self.user,
            aprobado_por_humano=True,
        )
        self.assertFalse(
            SalidaAnaliticaLab.objects.filter(orden=self.orden, analito=calc).exists()
        )
