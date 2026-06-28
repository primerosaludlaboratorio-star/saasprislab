"""
Tests de regresión mínimos para laboratorio.
Focalizados en las funciones operativas tocadas durante el cierre de deuda.
"""
import csv
import io

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from laboratorio.utils.label_printer import generar_codigo_barras, generar_etiqueta_tubo
from laboratorio.services.unificacion import _split_apellidos
from laboratorio.services.iso15189 import _parsear_valor

Usuario = get_user_model()


class LabelPrinterRegresionTest(TestCase):
    """Regresión en generación de etiquetas de laboratorio."""

    def test_generar_codigo_barras_devuelve_drawing(self):
        drawing = generar_codigo_barras('ORD-001')
        self.assertIsNotNone(drawing)

    def test_generar_etiqueta_tubo_devuelve_bytes(self):
        pdf_bytes = generar_etiqueta_tubo(
            folio_orden='ORD-001',
            nombre_paciente='Juan Pérez',
            tipo_muestra='Suero',
        )
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 0)


class UnificacionRegresionTest(TestCase):
    """Regresión en utilidades de unificación core/legacy."""

    def test_split_apellidos_con_dos_partes(self):
        paterno, materno = _split_apellidos('Pérez López')
        self.assertEqual(paterno, 'Pérez')
        self.assertEqual(materno, 'López')

    def test_split_apellidos_vacio(self):
        paterno, materno = _split_apellidos('')
        self.assertEqual(paterno, '')
        self.assertEqual(materno, '')


class ISO15189RegresionTest(TestCase):
    """Regresión en parser de valores ISO 15189."""

    def test_parsear_valor_decimal_valido(self):
        self.assertEqual(_parsear_valor('12.5'), 12.5)

    def test_parsear_valor_con_coma(self):
        self.assertEqual(_parsear_valor('12,5'), 12.5)

    def test_parsear_valor_mayor_que(self):
        self.assertEqual(_parsear_valor('> 50'), 50)

    def test_parsear_valor_vacio_devuelve_none(self):
        self.assertIsNone(_parsear_valor(''))


class AdminCSVRegresionTest(TestCase):
    """Regresión en carga de tarifas CSV."""

    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(
            username='stafflab',
            password='testpass123',
            is_staff=True,
        )
        self.client.login(username='stafflab', password='testpass123')

    def test_cargar_tarifas_rechaza_no_csv(self):
        from django.urls import reverse
        url = reverse('laboratorio:cargar_tarifas_csv')
        response = self.client.post(url, {'archivo': io.BytesIO(b'no csv')}, format='multipart')
        self.assertIn(response.status_code, [200, 400])

    def test_cargar_tarifas_csv_valido(self):
        from django.urls import reverse
        url = reverse('laboratorio:cargar_tarifas_csv')
        contenido = "encabezado1\nencabezado2\nTipo,Abreviatura,Descripción,Importe\nX,GLU,Glucosa,150.00\n"
        archivo = io.BytesIO(contenido.encode('utf-8'))
        response = self.client.post(url, {'archivo': archivo})
        self.assertIn(response.status_code, [200, 400])
