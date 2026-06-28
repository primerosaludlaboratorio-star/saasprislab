"""Tests para el módulo contable general: catálogo, pólizas y balance."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from contabilidad.models import CuentaContable, Poliza, AsientoContable
from core.models import Empresa


Usuario = get_user_model()


class ContabilidadGeneralTests(TestCase):
    """Valida flujo básico de catálogo, pólizas y balance."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa Contable', rfc='CON260626AAA')
        self.user = Usuario.objects.create_user(
            username='finanzas_contable',
            password='testpass123',
            empresa=self.empresa,
            rol='FINANZAS',
        )
        self.client.force_login(self.user)

    def test_dashboard_contabilidad_carga(self):
        resp = self.client.get(reverse('contabilidad:dashboard_contabilidad'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Contabilidad')

    def test_catalogo_cuentas_carga(self):
        resp = self.client.get(reverse('contabilidad:catalogo_cuentas'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Catálogo de Cuentas')

    def test_crear_cuenta(self):
        resp = self.client.post(reverse('contabilidad:crear_cuenta'), {
            'codigo': '1000',
            'nombre': 'Caja',
            'tipo': 'ACTIVO',
            'descripcion': 'Efectivo',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(CuentaContable.objects.filter(empresa=self.empresa, codigo='1000').exists())

    def test_crear_poliza(self):
        caja = CuentaContable.objects.create(
            empresa=self.empresa, codigo='1000', nombre='Caja', tipo='ACTIVO', naturaleza='DEUDOR'
        )
        ventas = CuentaContable.objects.create(
            empresa=self.empresa, codigo='4000', nombre='Ventas', tipo='INGRESO', naturaleza='ACREEDOR'
        )
        resp = self.client.post(reverse('contabilidad:crear_poliza'), {
            'tipo': 'DIARIO',
            'fecha': '2026-06-26',
            'concepto': 'Ventas del día',
            'cuenta_0': caja.id,
            'cargo_0': '1000.00',
            'abono_0': '0',
            'cuenta_1': ventas.id,
            'cargo_1': '0',
            'abono_1': '1000.00',
        })
        self.assertEqual(resp.status_code, 302)
        poliza = Poliza.objects.get(empresa=self.empresa)
        self.assertEqual(poliza.asientos.count(), 2)

    def test_autorizar_poliza(self):
        poliza = Poliza.objects.create(
            empresa=self.empresa,
            tipo='DIARIO',
            concepto='Test',
            creado_por=self.user,
        )
        resp = self.client.post(reverse('contabilidad:autorizar_poliza', kwargs={'poliza_id': poliza.id}))
        self.assertEqual(resp.status_code, 302)
        poliza.refresh_from_db()
        self.assertEqual(poliza.estado, 'AUTORIZADA')

    def test_api_cuentas(self):
        CuentaContable.objects.create(
            empresa=self.empresa, codigo='1000', nombre='Caja', tipo='ACTIVO'
        )
        resp = self.client.get(reverse('contabilidad:api_cuentas') + '?q=caja')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data['cuentas']), 1)

    def test_reporte_balance_general_carga(self):
        resp = self.client.get(reverse('reporte_balance_general'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Balance General')

    def test_cuentas_por_cobrar_carga(self):
        resp = self.client.get(reverse('cuentas_por_cobrar'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Cuentas por Cobrar')

    def test_convenios_lista_carga(self):
        resp = self.client.get(reverse('convenios_lista'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Convenios')
