"""Tests del motor puro Westgard (sin BD).

Las APIs L-J en ``laboratorio.views.cci_api`` usan STDDEV_SAMP (PostgreSQL). Esta
suite de CI solo ejercita ``evaluar_westgard``; cualquier test futuro que toque
agregados SQL debe usar ``@skipUnless(connection.vendor == 'postgresql', ...)``
o ejecutarse solo en jobs con Postgres.
"""
from django.test import SimpleTestCase

from laboratorio.services.westgard import evaluar_westgard


class WestgardMotorTests(SimpleTestCase):
    """Cada regla con ventana que termina en el último punto."""

    def test_ok_sin_violaciones(self):
        r = evaluar_westgard([100.0, 101.0, 99.0], media=100.0, sd=10.0)
        self.assertEqual(r.estado, 'OK')
        self.assertEqual(r.reglas_violadas, [])

    def test_1_3s_rechazo(self):
        # z = 3.1 en el último punto (media 100, sd 10 → 131)
        r = evaluar_westgard([100.0, 100.0, 131.0], media=100.0, sd=10.0)
        self.assertIn('1_3s', r.reglas_violadas)
        self.assertEqual(r.estado, 'RECHAZO')

    def test_1_2s_warning_sin_rechazo(self):
        r = evaluar_westgard([100.0, 100.0, 125.0], media=100.0, sd=10.0)
        self.assertIn('1_2s', r.reglas_violadas)
        self.assertNotIn('1_3s', r.reglas_violadas)
        self.assertEqual(r.estado, 'WARNING')

    def test_2_2s_rechazo(self):
        r = evaluar_westgard([100.0, 121.0, 122.0], media=100.0, sd=10.0)
        self.assertIn('2_2s', r.reglas_violadas)
        self.assertEqual(r.estado, 'RECHAZO')

    def test_r_4s_rechazo(self):
        # dos últimos: 2.5σ y -2.5σ → diferencia 5σ
        r = evaluar_westgard([0.0, 25.0, -25.0], media=100.0, sd=10.0)
        self.assertIn('R_4s', r.reglas_violadas)
        self.assertEqual(r.estado, 'RECHAZO')

    def test_4_1s_rechazo(self):
        # cuatro puntos > 1σ: 112, 112, 112, 112
        r = evaluar_westgard([112.0, 112.0, 112.0, 112.0], media=100.0, sd=10.0)
        self.assertIn('4_1s', r.reglas_violadas)
        self.assertEqual(r.estado, 'RECHAZO')

    def test_10_x_rechazo(self):
        z_vals = [0.5] * 10
        r = evaluar_westgard(z_vals, media=0.0, sd=1.0, valores_son_z=True)
        self.assertIn('10_x', r.reglas_violadas)
        self.assertEqual(r.estado, 'RECHAZO')

    def test_valores_son_z_1_3s(self):
        r = evaluar_westgard([0.0, 0.0, 3.2], media=0.0, sd=1.0, valores_son_z=True)
        self.assertIn('1_3s', r.reglas_violadas)
        self.assertEqual(r.estado, 'RECHAZO')

    def test_sd_cero_error(self):
        r = evaluar_westgard([1.0, 2.0], media=1.0, sd=0.0)
        self.assertEqual(r.estado, 'ERROR')
