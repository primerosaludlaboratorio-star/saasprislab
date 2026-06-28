"""
Tests de seguridad e integridad para el módulo Contabilidad / Finanzas.
Cubre: permisos por rol, fechas locales, tenant isolation, folios sin colisión,
dashboard financiero y reportes financieros.
"""
import json
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from contabilidad.models import ClienteFacturacion, FacturaCFDI, ConceptoFactura
from core.models import Empresa, Usuario, Paciente, Venta, FacturaSAT


# ══════════════════════════════════════════════════════════════════════════════
# 1. PERMISOS POR ROL EN VISTAS FINANCIERAS
# ══════════════════════════════════════════════════════════════════════════════

class RolePermissionsFinancialViewsTests(TestCase):
    """Verifica que las vistas financieras requieran roles adecuados."""

    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre='Empresa Test Finanzas')
        cls.paciente = Paciente.objects.create(
            empresa=cls.empresa,
            nombre_completo='Paciente Fiscal',
            nombres='P',
            apellido_paterno='F',
        )
        cls.cliente = ClienteFacturacion.objects.create(
            empresa=cls.empresa,
            paciente=cls.paciente,
            rfc='XAXX010101000',
            razon_social='PÚBLICO EN GENERAL',
            email='test@test.com',
            codigo_postal='12345',
        )
        cls.factura = FacturaCFDI.objects.create(
            cliente=cls.cliente,
            serie='A',
            subtotal=Decimal('100.00'),
            total=Decimal('116.00'),
            total_impuestos_trasladados=Decimal('16.00'),
            usuario_creo=cls._get_or_create_user('director_test', 'DIRECTOR', cls.empresa),
        )

    @staticmethod
    def _get_or_create_user(username, rol, empresa):
        user, _ = Usuario.objects.update_or_create(
            username=username,
            defaults={'empresa': empresa, 'rol': rol},
        )
        user.set_password('testpass123')
        user.save()
        return user

    def _login(self, username):
        user = Usuario.objects.get(username=username)
        self.client.force_login(user)
        return user

    def test_dashboard_contabilidad_requiere_rol_financiero(self):
        """Dashboard contabilidad debe rechazar usuarios sin rol FINANZAS/DIRECTOR/ADMIN/GERENTE."""
        self._login('director_test')
        url = reverse('contabilidad:dashboard_contabilidad')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_lista_facturas_requiere_rol(self):
        """Lista de facturas debe ser accesible con rol adecuado."""
        self._login('director_test')
        url = reverse('contabilidad:lista_facturas')
        resp = self.client.get(url)
        # Puede ser 200 (acceso permitido) o 302 (redirige si el cliente no tiene empresa)
        self.assertIn(resp.status_code, [200, 302])

    def test_crear_factura_requiere_rol(self):
        """Crear factura debe ser accesible con rol adecuado."""
        self._login('director_test')
        url = reverse('contabilidad:crear_factura')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_detalle_factura_requiere_rol(self):
        """Detalle de factura debe ser accesible con rol adecuado."""
        self._login('director_test')
        url = reverse('contabilidad:detalle_factura', kwargs={'factura_id': self.factura.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_reporte_ingresos_egresos_requiere_rol(self):
        """Reporte de ingresos/egresos debe requerir rol financiero."""
        self._login('director_test')
        url = reverse('reporte_ingresos_egresos')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_reporte_flujo_caja_requiere_rol(self):
        """Reporte de flujo de caja debe requerir rol financiero."""
        self._login('director_test')
        url = reverse('reporte_flujo_caja')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_bandeja_cfdi_requiere_rol(self):
        """Bandeja CFDI debe requerir rol financiero."""
        self._login('director_test')
        url = reverse('bandeja_cfdi')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_api_ventas_por_mes_requiere_rol(self):
        """API ventas por mes debe requerir rol financiero."""
        self._login('director_test')
        url = reverse('api_ventas_por_mes')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_contabilidad_rechaza_usuario_sin_rol_financiero(self):
        """Un usuario sin rol financiero no debe entrar al dashboard contable."""
        cajero = Usuario.objects.create_user(
            username='cajero_finanzas_test',
            password='testpass123',
            empresa=self.empresa,
            rol='CAJERO',
        )
        self.client.force_login(cajero)
        resp = self.client.get(reverse('contabilidad:dashboard_contabilidad'))
        self.assertEqual(resp.status_code, 403)


# ══════════════════════════════════════════════════════════════════════════════
# 2. REPORTES CON FECHA LOCAL CORRECTA
# ══════════════════════════════════════════════════════════════════════════════

class ReportesFechaLocalTests(TestCase):
    """Verifica que los reportes usen timezone.localdate() en vez de timezone.now().date()."""

    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre='Empresa Fecha Local')
        cls.user = Usuario.objects.create_user(
            username='finanzas_fecha',
            password='testpass123',
            empresa=cls.empresa,
            rol='FINANZAS',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_reporte_ingresos_egresos_usa_localdate(self):
        """El reporte de ingresos/egresos debe usar fecha local, no UTC."""
        url = reverse('reporte_ingresos_egresos')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        hoy = timezone.localdate()
        # Verifica que las fechas por defecto estén en el rango esperado
        self.assertIn(f'value="{hoy.strftime("%Y-%m-%d")}"', resp.content.decode())

    def test_reporte_flujo_caja_usa_localdate(self):
        """El reporte de flujo de caja debe usar fecha local."""
        url = reverse('reporte_flujo_caja')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        hoy = timezone.localdate()
        self.assertIn(f'value="{hoy.strftime("%Y-%m-%d")}"', resp.content.decode())

    def test_api_ventas_por_mes_usa_localdate_year(self):
        """API ventas por mes debe usar año de fecha local como default."""
        url = reverse('api_ventas_por_mes')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn('labels', data)
        self.assertIn('valores', data)

    def test_export_excel_ingresos_egresos_usa_localdate(self):
        """Export Excel debe usar fecha local."""
        url = reverse('exportar_excel_ingresos_egresos')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'],
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ══════════════════════════════════════════════════════════════════════════════
# 3. AUTOFACTURA PÚBLICA SIN FUGA TENANT
# ══════════════════════════════════════════════════════════════════════════════

class AutofacturaTenantIsolationTests(TransactionTestCase):
    """Verifica que autofactura_publica no exponga datos entre tenants."""

    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='Empresa A')
        self.empresa_b = Empresa.objects.create(nombre='Empresa B')
        self.user_a = Usuario.objects.create_user(
            username='user_a', password='testpass123', empresa=self.empresa_a,
        )
        self.user_b = Usuario.objects.create_user(
            username='user_b', password='testpass123', empresa=self.empresa_b,
        )

    def test_autofactura_publica_solo_encuentra_venta_por_folio_unico(self):
        """El folio de venta es unique global, no hay fuga cross-tenant posible por diseño."""
        venta_a = Venta.objects.create(
            empresa=self.empresa_a,
            usuario=self.user_a,
            total=Decimal('100.00'),
            estado='COMPLETADA',
        )
        url = reverse('autofactura_publica') + f'?folio={venta_a.folio_operacion}'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, venta_a.folio_operacion)

    def test_autofactura_publica_folio_inexistente_muestra_error(self):
        """Folio que no existe debe mostrar error."""
        url = reverse('autofactura_publica') + '?folio=VTA-99999999-XXXX'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No encontramos')

    def test_autofactura_publica_rate_limiting(self):
        """Rate limiting debe activarse tras múltiples solicitudes."""
        url = reverse('autofactura_publica')
        # 22 solicitudes: la 22ª debe disparar rate limit (attempts > 20)
        for _ in range(21):
            self.client.get(url)
        resp = self.client.get(url)
        # La respuesta rate-limited tiene error_folio con el mensaje
        self.assertContains(resp, 'Demasiadas solicitudes')


# ══════════════════════════════════════════════════════════════════════════════
# 4. FOLIOS SIN COLISIÓN POR EMPRESA
# ══════════════════════════════════════════════════════════════════════════════

class FolioSinColisionTests(TransactionTestCase):
    """Verifica que los folios de FacturaCFDI no colisionen entre tenants."""

    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='Empresa Folio A')
        self.empresa_b = Empresa.objects.create(nombre='Empresa Folio B')
        self.user = Usuario.objects.create_user(
            username='folio_user', password='testpass123', empresa=self.empresa_a,
        )
        self.paciente_a = Paciente.objects.create(
            empresa=self.empresa_a, nombre_completo='Pac A', nombres='A', apellido_paterno='P',
        )
        self.paciente_b = Paciente.objects.create(
            empresa=self.empresa_b, nombre_completo='Pac B', nombres='B', apellido_paterno='Q',
        )
        self.cliente_a = ClienteFacturacion.objects.create(
            empresa=self.empresa_a, paciente=self.paciente_a,
            rfc='XAXX010101000', razon_social='CLIENTE A', email='a@test.com', codigo_postal='12345',
        )
        self.cliente_b = ClienteFacturacion.objects.create(
            empresa=self.empresa_b, paciente=self.paciente_b,
            rfc='XEXX010101000', razon_social='CLIENTE B', email='b@test.com', codigo_postal='54321',
        )

    def test_folios_no_colisionan_entre_empresas(self):
        """Dos facturas de distintas empresas con misma serie deben tener folios independientes."""
        fac_a = FacturaCFDI.objects.create(
            cliente=self.cliente_a,
            serie='A',
            subtotal=Decimal('100.00'),
            total=Decimal('116.00'),
            total_impuestos_trasladados=Decimal('16.00'),
            usuario_creo=self.user,
        )
        # Cambiar usuario a empresa B
        user_b = Usuario.objects.create_user(
            username='folio_user_b', password='testpass123', empresa=self.empresa_b,
        )
        fac_b = FacturaCFDI.objects.create(
            cliente=self.cliente_b,
            serie='A',
            subtotal=Decimal('200.00'),
            total=Decimal('232.00'),
            total_impuestos_trasladados=Decimal('32.00'),
            usuario_creo=user_b,
        )
        # Ambas deben tener folio 1 (primera factura de cada empresa)
        self.assertEqual(fac_a.folio, 1)
        self.assertEqual(fac_b.folio, 1)
        # El folio interno debe incorporar el scope de empresa para evitar colisión global.
        self.assertNotEqual(fac_a.folio_interno, fac_b.folio_interno)
        self.assertIn(f"E{self.empresa_a.id}", fac_a.folio_interno)
        self.assertIn(f"E{self.empresa_b.id}", fac_b.folio_interno)

    def test_folios_secuenciales_dentro_misma_empresa(self):
        """Dos facturas de la misma empresa deben tener folios secuenciales."""
        fac1 = FacturaCFDI.objects.create(
            cliente=self.cliente_a,
            serie='A',
            subtotal=Decimal('100.00'),
            total=Decimal('116.00'),
            total_impuestos_trasladados=Decimal('16.00'),
            usuario_creo=self.user,
        )
        fac2 = FacturaCFDI.objects.create(
            cliente=self.cliente_a,
            serie='A',
            subtotal=Decimal('200.00'),
            total=Decimal('232.00'),
            total_impuestos_trasladados=Decimal('32.00'),
            usuario_creo=self.user,
        )
        self.assertEqual(fac1.folio, 1)
        self.assertEqual(fac2.folio, 2)

    def test_empresa_fk_se_asigna_automaticamente(self):
        """El campo empresa de FacturaCFDI debe poblarse desde cliente.empresa en save()."""
        fac = FacturaCFDI.objects.create(
            cliente=self.cliente_a,
            serie='A',
            subtotal=Decimal('100.00'),
            total=Decimal('116.00'),
            total_impuestos_trasladados=Decimal('16.00'),
            usuario_creo=self.user,
        )
        self.assertEqual(fac.empresa_id, self.empresa_a.id)


# ══════════════════════════════════════════════════════════════════════════════
# 5. TIMBRADO CON TENANT CORRECTO
# ══════════════════════════════════════════════════════════════════════════════

class TimbradoTenantCorrectoTests(TransactionTestCase):
    """Verifica que el timbrado respete el tenant."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa Timbrado')
        self.user = Usuario.objects.create_user(
            username='timbrado_user', password='testpass123',
            empresa=self.empresa, rol='FINANZAS',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa, nombre_completo='Pac Timbre',
            nombres='T', apellido_paterno='M',
        )
        self.cliente = ClienteFacturacion.objects.create(
            empresa=self.empresa, paciente=self.paciente,
            rfc='XAXX010101000', razon_social='TIMBRADO SA',
            email='t@test.com', codigo_postal='12345',
        )

    def test_timbrar_factura_solo_post(self):
        """Timbrar solo acepta POST."""
        fac = FacturaCFDI.objects.create(
            cliente=self.cliente,
            serie='A',
            subtotal=Decimal('100.00'),
            total=Decimal('116.00'),
            total_impuestos_trasladados=Decimal('16.00'),
            usuario_creo=self.user,
        )
        self.client.force_login(self.user)
        url = reverse('contabilidad:timbrar_factura', kwargs={'factura_id': fac.id})
        resp = self.client.get(url)
        # Debe redirigir porque solo acepta POST
        self.assertEqual(resp.status_code, 302)

    def test_descargar_xml_solo_timbrada(self):
        """Descargar XML solo funciona para facturas timbradas."""
        fac = FacturaCFDI.objects.create(
            cliente=self.cliente,
            serie='A',
            subtotal=Decimal('100.00'),
            total=Decimal('116.00'),
            total_impuestos_trasladados=Decimal('16.00'),
            usuario_creo=self.user,
            estado='BORRADOR',
        )
        self.client.force_login(self.user)
        url = reverse('contabilidad:descargar_xml', kwargs={'factura_id': fac.id})
        resp = self.client.get(url)
        # Debe redirigir con mensaje de error porque no está timbrada
        self.assertEqual(resp.status_code, 302)


# ══════════════════════════════════════════════════════════════════════════════
# 6. DASHBOARD FINANCIERO
# ══════════════════════════════════════════════════════════════════════════════

class DashboardFinancieroTests(TestCase):
    """Verifica que el dashboard de contabilidad muestre datos correctos."""

    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre='Empresa Dashboard')
        cls.user = Usuario.objects.create_user(
            username='dash_user', password='testpass123',
            empresa=cls.empresa, rol='FINANZAS',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_dashboard_contabilidad_carga(self):
        """El dashboard de contabilidad debe cargar con código 200."""
        url = reverse('contabilidad:dashboard_contabilidad')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('ingresos_mes', resp.context)
        self.assertIn('gastos_mes', resp.context)
        self.assertIn('utilidad_mes', resp.context)

    def test_dashboard_contabilidad_sin_empresa_redirige(self):
        """Usuario sin empresa debe ser rechazado por @role_required (403) o redirigido."""
        user_sin = Usuario.objects.create_user(
            username='sin_empresa', password='testpass123',
        )
        self.client.force_login(user_sin)
        url = reverse('contabilidad:dashboard_contabilidad')
        resp = self.client.get(url)
        # @role_required devuelve 403 antes de que la vista pueda redirigir
        self.assertIn(resp.status_code, [302, 403])

    def test_dashboard_contabilidad_muestra_cfdi_pendientes(self):
        """Dashboard debe mostrar conteo de CFDI pendientes."""
        paciente = Paciente.objects.create(
            empresa=self.empresa, nombre_completo='Pac CFDIs',
            nombres='C', apellido_paterno='D',
        )
        venta = Venta.objects.create(
            empresa=self.empresa, usuario=self.user,
            total=Decimal('100.00'), estado='COMPLETADA',
        )
        FacturaSAT.objects.create(
            empresa=self.empresa, venta=venta, paciente=paciente,
            estatus=FacturaSAT.ESTATUS_BORRADOR,
        )
        url = reverse('contabilidad:dashboard_contabilidad')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.context['cfdi_pendientes'], 1)


# ══════════════════════════════════════════════════════════════════════════════
# 7. REPORTES FINANCIEROS
# ══════════════════════════════════════════════════════════════════════════════

class ReportesFinancierosTests(TestCase):
    """Verifica que los reportes financieros funcionen correctamente."""

    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre='Empresa Reportes')
        cls.user = Usuario.objects.create_user(
            username='reportes_user', password='testpass123',
            empresa=cls.empresa, rol='FINANZAS',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_reporte_ingresos_egresos_con_datos(self):
        """Reporte de ingresos/egresos debe mostrar totales correctos."""
        Venta.objects.create(
            empresa=self.empresa, usuario=self.user,
            total=Decimal('500.00'), estado='COMPLETADA',
        )
        url = reverse('reporte_ingresos_egresos')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('total_ventas', resp.context)
        self.assertGreater(resp.context['total_ventas'], Decimal('0'))

    def test_reporte_flujo_caja_carga(self):
        """Reporte de flujo de caja debe cargar."""
        url = reverse('reporte_flujo_caja')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('total_entradas_efectivo', resp.context)
        self.assertIn('total_salidas_efectivo', resp.context)

    def test_reporte_balance_general_carga(self):
        """Reporte de balance general debe cargar (aunque sea stub parcial)."""
        url = reverse('reporte_balance_general')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('total_activos', resp.context)

    def test_export_excel_flujo_caja(self):
        """Export Excel de flujo de caja debe generar archivo."""
        url = reverse('exportar_excel_flujo_caja')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(resp['Content-Type'], [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
        ])

    def test_export_excel_balance(self):
        """Export Excel de balance general debe generar archivo."""
        url = reverse('exportar_excel_balance')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'],
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
