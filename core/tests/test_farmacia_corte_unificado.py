"""Regresiones para corte de caja unificado de Farmacia."""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase

from core.models import Empresa, MovimientoCaja, Paciente, Sucursal, Venta
from farmacia.models import AperturaCaja, CierreTurnoFarmacia
from farmacia.services.corte_caja_unificado import calcular_precorte_unificado, cerrar_turno_unificado


User = get_user_model()


class CorteCajaUnificadoTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.empresa = Empresa.objects.create(
            nombre='Empresa Corte',
            rfc='COR123456789',
        )
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre='Sucursal Corte',
            codigo_sucursal='SUC-COR-001',
        )
        self.user = User.objects.create_user(
            username='cajero_corte',
            password='cajero_corte_123',
            email='cajero-corte@example.com',
            rol='ADMIN',
            empresa=self.empresa,
            sucursal=self.sucursal,
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            nombres='Cliente',
            apellido_paterno='Corte',
            nombre_completo='Cliente Corte',
            empresa=self.empresa,
            sucursal=self.sucursal,
        )
        self.apertura = AperturaCaja.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            usuario_responsable=self.user,
            fondo_efectivo=Decimal('100.00'),
            fondo_vales=Decimal('0.00'),
        )
        self.venta = Venta.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            usuario=self.user,
            paciente=self.paciente,
            total=Decimal('80.00'),
            subtotal=Decimal('80.00'),
            estado='COMPLETADA',
        )
        self.client.login(username='cajero_corte', password='cajero_corte_123')

    def test_corte_unificado_crea_cierre_formal_y_cierra_apertura(self):
        corte = cerrar_turno_unificado(
            cajero=self.user,
            empresa=self.empresa,
            sucursal=self.sucursal,
            efectivo_declarado=Decimal('180.00'),
            imprimir_ticket=False,
        )

        self.apertura.refresh_from_db()
        cierre = CierreTurnoFarmacia.objects.get(apertura_caja=self.apertura)

        self.assertFalse(self.apertura.activa)
        self.assertEqual(self.apertura.cerrada_con, cierre)
        self.assertEqual(cierre.efectivo_teorico, Decimal('80.00'))
        self.assertEqual(cierre.efectivo_declarado, Decimal('180.00'))
        self.assertEqual(cierre.diferencia_efectivo, Decimal('0.00'))
        self.assertEqual(corte['farmacia']['cierre_id'], cierre.id)
        self.assertEqual(corte['fondo_inicial'], '100.00')
        self.assertEqual(corte['efectivo_esperado'], '180.00')
        self.assertEqual(corte['diferencia'], '0.00')

    def test_corte_unificado_no_duplica_cierre_si_no_hay_apertura_activa(self):
        cerrar_turno_unificado(
            cajero=self.user,
            empresa=self.empresa,
            sucursal=self.sucursal,
            efectivo_declarado=Decimal('180.00'),
            imprimir_ticket=False,
        )
        segundo = cerrar_turno_unificado(
            cajero=self.user,
            empresa=self.empresa,
            sucursal=self.sucursal,
            efectivo_declarado=Decimal('180.00'),
            imprimir_ticket=False,
        )

        self.assertEqual(CierreTurnoFarmacia.objects.filter(apertura_caja=self.apertura).count(), 1)
        self.assertEqual(segundo['farmacia']['estado'], 'sin_apertura')

    def test_api_corte_unificado_cierra_apertura_y_devuelve_json(self):
        response = self.client.post(
            '/api/caja/corte-unificado/',
            data=json.dumps({'efectivo_declarado': '180.00', 'imprimir_ticket': False}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['corte']['estado'], 'CUADRADO')
        self.assertEqual(CierreTurnoFarmacia.objects.filter(apertura_caja=self.apertura).count(), 1)

    def test_api_corte_unificado_rechaza_monto_invalido(self):
        response = self.client.post(
            '/api/caja/corte-unificado/',
            data=json.dumps({'efectivo_declarado': 'abc'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertIn('efectivo_declarado', data['error'])
        self.assertEqual(CierreTurnoFarmacia.objects.count(), 0)

    def test_api_corte_unificado_rechaza_efectivo_omitido(self):
        response = self.client.post(
            '/api/caja/corte-unificado/',
            data=json.dumps({}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertIn('obligatorio', data['error'])
        self.assertEqual(CierreTurnoFarmacia.objects.count(), 0)

    def test_api_corte_unificado_rechaza_monto_no_finito(self):
        response = self.client.post(
            '/api/caja/corte-unificado/',
            data=json.dumps({'efectivo_declarado': 'NaN'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('finito', response.json()['error'])
        self.apertura.refresh_from_db()
        self.assertTrue(self.apertura.activa)

    def test_api_corte_unificado_rechaza_json_malformado(self):
        response = self.client.post(
            '/api/caja/corte-unificado/',
            data='{"efectivo_declarado": 180.00',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertIn('JSON', data['error'])
        self.assertEqual(CierreTurnoFarmacia.objects.count(), 0)

    def test_api_corte_unificado_rechaza_json_no_utf8(self):
        response = self.client.post(
            '/api/caja/corte-unificado/',
            data=b'\x80',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertIn('JSON', data['error'])
        self.assertEqual(CierreTurnoFarmacia.objects.count(), 0)

    def test_api_corte_repetido_devuelve_conflicto_y_no_simula_exito(self):
        primera = self.client.post(
            '/api/caja/corte-unificado/',
            data=json.dumps({'efectivo_declarado': '180.00', 'imprimir_ticket': False}),
            content_type='application/json',
        )
        segunda = self.client.post(
            '/api/caja/corte-unificado/',
            data=json.dumps({'efectivo_declarado': '180.00', 'imprimir_ticket': False}),
            content_type='application/json',
        )

        self.assertEqual(primera.status_code, 200)
        self.assertEqual(segunda.status_code, 409)
        self.assertFalse(segunda.json()['ok'])

    def test_no_se_permiten_dos_aperturas_activas_en_la_misma_sucursal(self):
        with self.assertRaises(ValidationError):
            AperturaCaja.objects.create(
                empresa=self.empresa,
                sucursal=self.sucursal,
                usuario_responsable=self.user,
                fondo_efectivo=Decimal('50.00'),
                fondo_vales=Decimal('0.00'),
            )

    def test_precorte_es_solo_lectura_y_conserva_apertura(self):
        antes = CierreTurnoFarmacia.objects.count()

        precorte = calcular_precorte_unificado(
            cajero=self.user,
            empresa=self.empresa,
            sucursal=self.sucursal,
        )

        self.apertura.refresh_from_db()
        self.assertTrue(precorte['solo_lectura'])
        self.assertEqual(precorte['estado'], 'PRECORTE')
        self.assertEqual(precorte['farmacia']['total'], '80.00')
        self.assertEqual(precorte['efectivo_esperado'], '180.00')
        self.assertEqual(CierreTurnoFarmacia.objects.count(), antes)
        self.assertTrue(self.apertura.activa)

    def test_api_precorte_admin_devuelve_resumen_sin_cerrar(self):
        response = self.client.get('/api/caja/precorte/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['precorte']['solo_lectura'])
        self.assertEqual(data['precorte']['farmacia']['ventas'], 1)
        self.assertEqual(CierreTurnoFarmacia.objects.count(), 0)
        self.apertura.refresh_from_db()
        self.assertTrue(self.apertura.activa)

    def test_api_precorte_permite_personal_y_no_expone_ganancias(self):
        empleado = User.objects.create_user(
            username='empleado_precorte',
            password='empleado_precorte_123',
            email='empleado-precorte@example.com',
            rol='CAJERO',
            empresa=self.empresa,
            sucursal=self.sucursal,
        )
        self.client.force_login(empleado)

        response = self.client.get('/api/caja/precorte/')

        self.assertEqual(response.status_code, 200)
        data = response.json()['precorte']
        self.assertTrue(data['solo_lectura'])
        self.assertNotIn('ganancia', data)
        self.assertNotIn('margen', data)
        self.assertNotIn('costo', data)

    def test_precorte_de_entrega_incluye_actividad_de_todo_el_turno(self):
        empleado = User.objects.create_user(
            username='empleado_entrega',
            password='empleado-entrega-123',
            email='empleado-entrega@example.com',
            rol='CAJERO',
            empresa=self.empresa,
            sucursal=self.sucursal,
        )
        MovimientoCaja.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            tipo_movimiento='TRANSFERENCIA',
            concepto='RETIRO_BOVEDA',
            monto=Decimal('25.00'),
            usuario_responsable=self.user,
            referencia='Retiro de prueba para entrega de turno',
        )

        precorte = calcular_precorte_unificado(
            cajero=empleado,
            empresa=self.empresa,
            sucursal=self.sucursal,
        )

        self.assertEqual(precorte['apertura']['responsable_apertura'], self.user.username)
        self.assertEqual(precorte['farmacia']['ventas'], 1)
        self.assertEqual(precorte['farmacia']['retiros'], '25.00')
        self.assertEqual(precorte['efectivo_esperado'], '155.00')
        self.assertEqual(len(precorte['farmacia']['movimientos']), 2)

    def test_personal_entrante_puede_cerrar_apertura_de_otro_usuario(self):
        empleado = User.objects.create_user(
            username='empleado_cierre',
            password='empleado-cierre-123',
            email='empleado-cierre@example.com',
            rol='CAJERO',
            empresa=self.empresa,
            sucursal=self.sucursal,
        )

        corte = cerrar_turno_unificado(
            cajero=empleado,
            empresa=self.empresa,
            sucursal=self.sucursal,
            efectivo_declarado=Decimal('180.00'),
            imprimir_ticket=False,
        )

        cierre = CierreTurnoFarmacia.objects.get(apertura_caja=self.apertura)
        self.assertEqual(corte['estado'], 'CUADRADO')
        self.assertEqual(cierre.usuario_responsable, self.user)
        self.assertEqual(cierre.cerrado_por, empleado)

    @patch('farmacia.services.corte_caja_unificado._cerrar_laboratorio')
    def test_api_corte_unificado_revierte_si_laboratorio_falla(self, mock_cerrar_laboratorio):
        mock_cerrar_laboratorio.return_value = {'total': Decimal('0'), 'estado': 'error', 'error': 'boom'}

        response = self.client.post(
            '/api/caja/corte-unificado/',
            data=json.dumps({'efectivo_declarado': '180.00', 'imprimir_ticket': False}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertIn('No fue posible completar', data['error'])
        self.assertEqual(CierreTurnoFarmacia.objects.count(), 0)
        self.apertura.refresh_from_db()
        self.assertTrue(self.apertura.activa)
