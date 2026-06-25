from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
import json
import uuid

from core.models import Empresa, Sucursal, Producto
from laboratorio.models import Equipo
from mantenimiento.models import ExpedienteEquipo, SensorIoT, LecturaSensorIoT, TicketMantenimientoCMMS
from inventario.models import LoteInsumoGeneral, CatalogoInsumoGeneral

Usuario = get_user_model()

class MantenimientoScopingTest(TestCase):
    def setUp(self):
        # Create two companies
        self.empresa_a = Empresa.objects.create(nombre="Empresa A", rfc="RFC111111AAA")
        self.empresa_b = Empresa.objects.create(nombre="Empresa B", rfc="RFC222222BBB")

        # Create users
        self.user_a = Usuario.objects.create_user(
            username='usera', password='password123', empresa=self.empresa_a
        )
        self.user_b = Usuario.objects.create_user(
            username='userb', password='password123', empresa=self.empresa_b
        )

        # Create physical equipment (Equipo is in laboratorio app)
        self.equipo_phys_a = Equipo.objects.create(nombre="Analizador Físico A", protocolo="HL7", activo=True)
        self.equipo_phys_b = Equipo.objects.create(nombre="Analizador Físico B", protocolo="HL7", activo=True)

        # Create ExpedienteEquipo (linked to respective companies)
        self.expediente_a = ExpedienteEquipo.objects.create(
            empresa=self.empresa_a,
            equipo=self.equipo_phys_a,
            tipo_equipo='ANALIZADOR',
            silo_refacciones='GENERAL'
        )
        self.expediente_b = ExpedienteEquipo.objects.create(
            empresa=self.empresa_b,
            equipo=self.equipo_phys_b,
            tipo_equipo='ANALIZADOR',
            silo_refacciones='GENERAL'
        )

        # Create general products and lotes for the silos
        self.insumo_a = CatalogoInsumoGeneral.objects.create(
            empresa=self.empresa_a,
            codigo_interno="TORN-A",
            nombre="Tornillos Refacción A",
            activo=True
        )
        self.lote_general_a = LoteInsumoGeneral.objects.create(
            empresa=self.empresa_a,
            insumo=self.insumo_a,
            cantidad_inicial=100.0,
            cantidad_actual=100.0,
            precio_unitario_compra=5.0
        )

        self.insumo_b = CatalogoInsumoGeneral.objects.create(
            empresa=self.empresa_b,
            codigo_interno="TORN-B",
            nombre="Tornillos Refacción B",
            activo=True
        )
        self.lote_general_b = LoteInsumoGeneral.objects.create(
            empresa=self.empresa_b,
            insumo=self.insumo_b,
            cantidad_inicial=50.0,
            cantidad_actual=50.0,
            precio_unitario_compra=6.0
        )

        self.client = Client()

    def test_api_stock_lote_para_refaccion_scoping(self):
        """User A should not access stock information of a lote from Empresa B."""
        self.client.login(username='usera', password='password123')
        
        # Requesting a lote belonging to self (Empresa A) -> Should return 200
        url = reverse('mantenimiento:api_stock_lote')
        response = self.client.get(url, {'silo': 'GENERAL', 'lote_id': self.lote_general_a.id})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['lote_id'], self.lote_general_a.id)

        # Requesting a lote belonging to Empresa B -> Should return 404 (Lote not found under Empresa A context)
        response = self.client.get(url, {'silo': 'GENERAL', 'lote_id': self.lote_general_b.id})
        self.assertEqual(response.status_code, 404)

    def test_crear_ticket_expediente_cross_tenant_validation(self):
        """A user cannot link a ticket to an equipment file (expediente) of another company."""
        self.client.login(username='usera', password='password123')

        # Attempting to POST ticket linked to expediente of Empresa B
        url = reverse('mantenimiento:crear_ticket')
        post_data = {
            'expediente': self.expediente_b.id,
            'titulo': 'Falla Crítica Cruzada',
            'descripcion': 'Intento de vincular ticket a otra empresa.',
            'tipo_origen': 'MANUAL'
        }
        
        response = self.client.post(url, post_data)
        # Should return 404 because expediente_b is not found for Empresa A
        self.assertEqual(response.status_code, 404)

        # Linking to self expediente should succeed (redirects to detail, 302)
        post_data['expediente'] = self.expediente_a.id
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

    def test_qr_equipo_publico_logged_in_cross_tenant(self):
        """Public QR is readable by anyone, but user_logueado actions only active if user's company matches."""
        # 1. Anonymous access -> user_logueado should be False
        url = reverse('mantenimiento:qr_equipo', args=[self.expediente_a.qr_uid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['usuario_logueado'])

        # 2. Logged in as User B (different company) -> user_logueado should still be False
        self.client.login(username='userb', password='password123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['usuario_logueado'])

        # 3. Logged in as User A (matching company) -> user_logueado should be True
        self.client.login(username='usera', password='password123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['usuario_logueado'])

    def test_api_iot_lectura_rechaza_codigos_duplicados_cross_tenant(self):
        """IoT sensor reading endpoint rejects ambiguous duplicated codes across companies."""
        # Create duplicate code sensor for Empresa A and Empresa B
        code = "SENSOR-DUPLICATE-XYZ"
        sensor_a = SensorIoT.objects.create(
            empresa=self.empresa_a,
            codigo=code,
            nombre="Sensor A",
            tipo="TEMPERATURA",
            activo=True
        )
        sensor_b = SensorIoT.objects.create(
            empresa=self.empresa_b,
            codigo=code,
            nombre="Sensor B",
            tipo="TEMPERATURA",
            activo=True
        )

        url = reverse('mantenimiento:api_iot_lectura')
        headers = {'HTTP_X_SENSOR_TOKEN': code}
        post_data = {'temperatura': 4.5, 'humedad': 50.0}

        # Sending POST request -> Should succeed and not return a 500 error due to MultipleObjectsReturned
        response = self.client.post(
            url,
            json.dumps(post_data),
            content_type="application/json",
            **headers
        )
        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertIn('ambiguo', data['error'])
        self.assertFalse(LecturaSensorIoT.objects.filter(sensor__in=[sensor_a, sensor_b]).exists())
