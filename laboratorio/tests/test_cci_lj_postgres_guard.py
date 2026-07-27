"""
CCI / Levey-Jennings — contrato PostgreSQL para integración futura.

Las vistas ``laboratorio.views.cci_api`` usan agregados SQL (p. ej. ``STDDEV_SAMP``)
que SQLite no soporta. El Quality Gate corre en SQLite; este módulo queda
registrado en CI como recordatorio: aquí deben vivir tests que toquen ``cci_api``.
Se omite en SQLite (Quality Gate) y en cualquier motor distinto de PostgreSQL.

Motor puro Westgard: ``laboratorio.tests.test_westgard`` (SimpleTestCase, sin BD).
"""
import unittest
from decimal import Decimal

from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa, Usuario
from lims.models import Analito
from laboratorio.cci_models import MedicionControlInterno
from laboratorio.models import Equipo


@unittest.skipUnless(
    connection.vendor == 'postgresql',
    'cci_api / STDDEV_SAMP: integración L-J solo en PostgreSQL (CI usa SQLite)',
)
class CciLjPostgresIntegrationGuard(TestCase):
    """Pruebas reales de agregados CCI contra PostgreSQL."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='CCI PostgreSQL')
        self.usuario = Usuario.objects.create_user(
            username='cci-postgres',
            password='test-password-123',
            empresa=self.empresa,
        )
        self.equipo = Equipo.objects.create(nombre='Equipo CCI PostgreSQL')
        self.analito = Analito.objects_all.create(
            empresa=self.empresa,
            codigo='CCI-GLU-POSTGRES',
            abreviatura='GLU',
            nombre='Glucosa CCI PostgreSQL',
            departamento='Quimica clinica',
        )
        for value in ('100.000000', '101.000000', '99.000000'):
            MedicionControlInterno.objects.create(
                empresa=self.empresa,
                equipo=self.equipo,
                analito=self.analito,
                valor=Decimal(value),
                fecha_medicion=timezone.now(),
            )
        self.client = Client()
        self.client.force_login(self.usuario)

    def test_entorno_es_postgresql(self):
        self.assertEqual(connection.vendor, 'postgresql')

    def test_summary_executes_stddev_sample(self):
        response = self.client.get(
            reverse('laboratorio:api_cci_lj_summary'),
            {'equipo_id': self.equipo.pk, 'analito_id': self.analito.pk},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['resumen']['n'], 3)
        self.assertIsNotNone(payload['resumen']['stddev_samp_valor'])

    def test_series_executes_postgresql_grouping(self):
        response = self.client.get(
            reverse('laboratorio:api_cci_lj_series'),
            {'equipo_id': self.equipo.pk, 'analito_id': self.analito.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['series'])
