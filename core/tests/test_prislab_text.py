from django.test import SimpleTestCase

from core.templatetags.prislab_text import nombre_lims


class NombreLimsTest(SimpleTestCase):
    def test_normaliza_frase_en_mayusculas(self):
        self.assertEqual(nombre_lims('PERFIL HEPATICO'), 'Perfil hepatico')

    def test_preserva_abreviaturas_clinicas(self):
        self.assertEqual(nombre_lims('TSH'), 'TSH')
        self.assertEqual(nombre_lims('CK-MB'), 'CK-MB')
