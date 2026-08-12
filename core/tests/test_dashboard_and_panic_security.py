import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from core.views.dashboard_unificado import api_kpis_tiempo_real, dashboard_unificado
from core.views.laboratorio_captura import registrar_notificacion_panico
from core.views.monitor_produccion import _puede_validar_resultados
from core.views.transferencias import api_buscar_productos_transferencia
from core.utils.pris_audio_vision import generar_hash_digital, verificar_integridad
from core.views.administracion_usuarios import (
    api_actualizar_tarifa,
    api_actualizar_usuario,
    _puede_delegar_privilegios,
)
from core.views.configuracion import configuracion_empresa
from core.views.director import director_analizadores_probar_conexion
from core.views.excepciones_lab import registrar_merma
from core.views.catalogos import catalogo_convenios
from core.agent.tools.registry import TOOLS_OPERATIVOS
from farmacia.views.inventario import carga_masiva_productos
from farmacia.views.devoluciones import procesar_devolucion_venta
from farmacia.views.compras import entrada_express


class DashboardAndPanicSecurityTests(SimpleTestCase):
    def test_employee_cannot_bulk_load_pharmacy_catalog(self):
        request = RequestFactory().post('/farmacia/inventario/carga-masiva/', data={})
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='CAJERO',
            username='cajero',
        )
        response = carga_masiva_productos.__wrapped__(request)
        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_use_alternate_return_endpoint(self):
        request = RequestFactory().post(
            '/farmacia/devoluciones/procesar-venta/',
            data='{}',
            content_type='application/json',
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            is_staff=False,
            rol='CAJERO',
            username='cajero',
            empresa=object(),
            groups=SimpleNamespace(filter=lambda **kwargs: SimpleNamespace(exists=lambda: False)),
        )
        response = procesar_devolucion_venta.__wrapped__(request)
        self.assertEqual(response.status_code, 302)

    def test_employee_without_inventory_permission_cannot_use_express_entry(self):
        request = RequestFactory().post(
            '/farmacia/compras/entrada-express/',
            data='{}',
            content_type='application/json',
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            has_perms=lambda permission: False,
        )
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            entrada_express.__wrapped__(request)

    def test_employee_cannot_create_convenio(self):
        request = RequestFactory().post('/catalogos/convenios/', data={})
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='CAJERO',
            username='cajero',
        )
        response = catalogo_convenios.__wrapped__(request)
        self.assertEqual(response.status_code, 403)

    def test_operational_registry_has_one_effective_rbac_source(self):
        self.assertTrue(all('grupos' not in entry for entry in TOOLS_OPERATIVOS.values()))

    def test_employee_cannot_change_company_configuration(self):
        request = RequestFactory().get('/configuracion/empresa/')
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='CAJERO',
        )
        with patch('core.views.configuracion.get_empresa_usuario', return_value=object()):
            response = configuracion_empresa(request)
        self.assertEqual(response.status_code, 403)

    def test_analyzer_probe_rejects_loopback_before_connecting(self):
        request = RequestFactory().post(
            '/director/analizadores/probar/',
            data=json.dumps({'ip': '127.0.0.1', 'puerto': 80}),
            content_type='application/json',
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='LABORATORIO',
            empresa=object(),
        )
        response = director_analizadores_probar_conexion.__wrapped__(request)
        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_register_inventory_shrinkage(self):
        request = RequestFactory().post('/laboratorio/merma/', data='{}', content_type='application/json')
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='CAJERO',
            username='cajero',
        )
        response = registrar_merma.__wrapped__(request)
        self.assertEqual(response.status_code, 403)

    def test_staff_without_admin_role_cannot_update_users(self):
        request = RequestFactory().post('/administracion/usuarios/1/', data='{}', content_type='application/json')
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            is_staff=True,
            rol='CAJERO',
            username='cajero',
        )
        response = api_actualizar_usuario.__wrapped__(request, 1)
        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_delegate_admin_or_staff_privileges(self):
        manager = SimpleNamespace(is_superuser=False, rol='GERENTE')
        self.assertFalse(_puede_delegar_privilegios(manager, {'rol': 'ADMIN'}))
        self.assertFalse(_puede_delegar_privilegios(manager, {'is_staff': True}))
        self.assertTrue(_puede_delegar_privilegios(manager, {'rol': 'QUIMICO'}))

    def test_tenant_admin_cannot_update_global_tariff(self):
        request = RequestFactory().post('/administracion/tarifas/1/', data='{}', content_type='application/json')
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            is_staff=True,
            rol='ADMIN',
            empresa=object(),
            username='admin',
        )
        response = api_actualizar_tarifa.__wrapped__(request, 1)
        self.assertEqual(response.status_code, 403)

    def test_transfer_search_accepts_text_filter(self):
        request = RequestFactory().get('/transferencias/api/buscar-productos/?q=guante')
        request.user = SimpleNamespace(is_authenticated=True, empresa=object())
        class FakeQuerySet:
            def filter(self, *args, **kwargs):
                return self

            def __getitem__(self, key):
                return []

            def __iter__(self):
                return iter(())

        with patch('core.views.transferencias.Producto.objects.filter', return_value=FakeQuerySet()):
            response = api_buscar_productos_transferencia.__wrapped__(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'productos': []})

    def test_audio_integrity_lookup_is_tenant_scoped(self):
        empresa = object()
        timestamp = '2026-07-30T12:00:00+00:00'
        registro = SimpleNamespace(
            parametros_extraidos={'hash_sha256': generar_hash_digital('prueba', timestamp)},
            timestamp=SimpleNamespace(isoformat=lambda: timestamp),
            transcripcion='prueba',
        )
        manager = Mock()
        manager.get.return_value = registro

        with patch('core.models.VoiceAuditLog.objects', manager):
            resultado = verificar_integridad(7, empresa=empresa)

        manager.get.assert_called_once_with(pk=7, empresa=empresa)
        self.assertTrue(resultado['valido'])

    def test_clinical_release_gate_is_role_scoped(self):
        self.assertFalse(_puede_validar_resultados(SimpleNamespace(
            is_superuser=False,
            is_staff=False,
            rol='CAJERO',
        )))
        self.assertTrue(_puede_validar_resultados(SimpleNamespace(
            is_superuser=False,
            is_staff=False,
            rol='LABORATORIO',
        )))

    def test_employee_cannot_access_financial_dashboard(self):
        request = RequestFactory().get('/dashboard-unificado/')
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='CAJERO',
            username='empleado',
        )

        response = dashboard_unificado.__wrapped__(request)

        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_access_realtime_financial_kpis(self):
        request = RequestFactory().get('/api/kpis-tiempo-real/')
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='RECEPCION',
            username='recepcion',
        )

        response = api_kpis_tiempo_real.__wrapped__(request)

        self.assertEqual(response.status_code, 403)

    def test_panic_notification_rejects_analito_outside_order(self):
        request = RequestFactory().post(
            '/laboratorio/captura/1/panico/',
            data={
                'analito_id': '77',
                'valor_critico': '1',
                'medico_notificado': 'Dr. Prueba',
                'medio_notificacion': 'TEL',
            },
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            empresa=object(),
            username='quimico',
        )
        orden = Mock()
        orden.detalles.filter.return_value.exists.return_value = False

        with patch(
            'core.views.laboratorio_captura.get_object_or_404',
            return_value=orden,
        ):
            response = registrar_notificacion_panico.__wrapped__(request, 1)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['success'], False)
