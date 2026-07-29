from decimal import Decimal
from django.test import TestCase
from django.test import SimpleTestCase

from lims.veterinary_catalog import is_veterinary_catalog_text


class VeterinaryCatalogFilterTests(SimpleTestCase):
    def test_rejects_veterinary_identifiers(self):
        self.assertTrue(is_veterinary_catalog_text('GLU-FEL', 'Glucosa felina'))
        self.assertTrue(is_veterinary_catalog_text('Perfil canino'))
        self.assertTrue(is_veterinary_catalog_text('GLUCAN', 'Glucosa can'))
        self.assertTrue(is_veterinary_catalog_text('EQUINO'))

    def test_keeps_human_catalog_identifiers(self):
        self.assertFalse(is_veterinary_catalog_text('GLU', 'Glucosa', 'Química clínica'))
        self.assertFalse(is_veterinary_catalog_text('BH', 'Biometría hemática'))
from django.contrib.auth import get_user_model
from core.models import Empresa, Paciente
from lims.models import Analito, ValorReferenciaAnalito

User = get_user_model()

class AnalitoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre='Lab Test', rfc='LABT990101XXX')
        cls.analito = Analito.objects.create(
            empresa=cls.empresa,
            codigo='GLU',
            abreviatura='GLU',
            nombre='Glucosa en sangre',
            departamento='Química Clínica',
            tipo_resultado='NUMERICO',
            unidades='mg/dL'
        )

    def test_creacion_analito(self):
        self.assertEqual(Analito.objects.count(), 1)
        self.assertEqual(self.analito.nombre, 'Glucosa en sangre')

    def test_analito_str(self):
        self.assertEqual(str(self.analito), 'GLU — Glucosa en sangre')


class ValorReferenciaAnalitoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre='Lab Test', rfc='LABT990101XXX')
        cls.analito = Analito.objects.create(
            empresa=cls.empresa,
            codigo='GLU',
            abreviatura='GLU',
            nombre='Glucosa en sangre',
            departamento='Química Clínica'
        )
        # Rango para adulto masculino
        ValorReferenciaAnalito.objects.create(
            analito=cls.analito,
            sexo='M',
            unidad_edad='ANOS',
            edad_minima=18,
            edad_maxima=99,
            ref_minimo=Decimal('70.00'),
            ref_maximo=Decimal('100.00'),
            valor_critico_bajo=Decimal('50.00'),
            valor_critico_alto=Decimal('400.00'),
            es_critico_si_fuera_de_rango=False
        )
        # Rango para bebé (días)
        ValorReferenciaAnalito.objects.create(
            analito=cls.analito,
            sexo='I',
            unidad_edad='DIAS',
            edad_minima=0,
            edad_maxima=30,
            ref_minimo=Decimal('40.00'),
            ref_maximo=Decimal('90.00'),
        )

    def test_aplica_para_paciente_adulto(self):
        from datetime import date, timedelta
        paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombres='Juan',
            apellido_paterno='Pérez',
            nombre_completo='Juan Pérez',
            sexo='M',
            fecha_nacimiento=date.today() - timedelta(days=30*365)
        )
        rango = ValorReferenciaAnalito.aplica_para_paciente(self.analito, paciente=paciente)
        self.assertIsNotNone(rango)
        self.assertEqual(rango.ref_minimo, Decimal('70.00'))

    def test_aplica_para_paciente_bebe(self):
        # Forzamos los parámetros
        rango = ValorReferenciaAnalito.aplica_para_paciente(
            self.analito, edad_dias=15, edad_anios=0, sexo='M'
        )
        self.assertIsNotNone(rango)
        self.assertEqual(rango.ref_minimo, Decimal('40.00'))

    def test_aplica_no_encuentra_rango(self):
        # Mujer adulta, no definimos rango para mujer
        rango = ValorReferenciaAnalito.aplica_para_paciente(
            self.analito, edad_dias=10000, edad_anios=25, sexo='F'
        )
        self.assertIsNone(rango)
