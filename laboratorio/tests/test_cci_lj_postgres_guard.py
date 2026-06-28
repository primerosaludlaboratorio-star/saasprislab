"""
CCI / Levey-Jennings — contrato PostgreSQL para integración futura.

Las vistas ``laboratorio.views.cci_api`` usan agregados SQL (p. ej. ``STDDEV_SAMP``)
que SQLite no soporta. El Quality Gate corre en SQLite; este módulo queda
registrado en CI como recordatorio: aquí deben vivir tests que toquen ``cci_api``.
Se omite en SQLite (Quality Gate) y en cualquier motor distinto de PostgreSQL.

Motor puro Westgard: ``laboratorio.tests.test_westgard`` (SimpleTestCase, sin BD).
"""
import unittest

from django.db import connection
from django.test import TestCase


@unittest.skipUnless(
    connection.vendor == 'postgresql',
    'cci_api / STDDEV_SAMP: integración L-J solo en PostgreSQL (CI usa SQLite)',
)
class CciLjPostgresIntegrationGuard(TestCase):
    """Placeholder para pruebas de integración contra cci_api cuando exista job Postgres."""

    def test_entorno_es_postgresql(self):
        self.assertEqual(connection.vendor, 'postgresql')
