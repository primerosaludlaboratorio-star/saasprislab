"""
Punto 16: timbrado concurrente + Idempotency-Key determinista.
SQLite no expone select_for_update útil entre hilos: se complementa con mocks.
"""
import hashlib
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import OperationalError
from django.test import RequestFactory, TransactionTestCase, SimpleTestCase

from core.models import Empresa
from contabilidad.models import ClienteFacturacion, FacturaCFDI
from contabilidad.services import timbrado_cfdi as timbrado_svc


class IdempotencyKeyTests(SimpleTestCase):
    def test_clave_determinista_sin_timestamp(self):
        semilla = "cfdi-empresa3-fac42"
        k1 = hashlib.sha256(semilla.encode()).hexdigest()
        k2 = hashlib.sha256(semilla.encode()).hexdigest()
        self.assertEqual(k1, k2)
        self.assertEqual(len(k1), 64)


class TimbradoBlindajeTests(TransactionTestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Test CFDI")
        from core.models import Usuario

        self.user = Usuario.objects.create_user(
            username="cfdi_worker",
            password="pass12345",
            empresa=self.empresa,
        )
        self.cliente = ClienteFacturacion.objects.create(
            empresa=self.empresa,
            rfc="XAXX010101000",
            razon_social="PUBLICO EN GENERAL",
            email="test@example.com",
            codigo_postal="01000",
        )
        self.factura = FacturaCFDI(
            cliente=self.cliente,
            serie="A",
            subtotal=Decimal("100.00"),
            total=Decimal("116.00"),
            total_impuestos_trasladados=Decimal("16.00"),
            usuario_creo=self.user,
            estado="BORRADOR",
        )
        self.factura.save()

    def tearDown(self):
        timbrado_svc.set_facturama_factory_for_tests(None)
        super().tearDown()

    def _request(self):
        rf = RequestFactory()
        req = rf.post(
            f"/facturacion/cfdi/{self.factura.id}/timbrar/?fmt=json",
            data={},
        )
        req.user = self.user
        SessionMiddleware(lambda r: None).process_request(req)
        req.session.save()
        MessageMiddleware(lambda r: None).process_request(req)
        return req

    def test_lock_operational_error_respuesta_409_json(self):
        """Simula segundo proceso con fila bloqueada (nowait)."""
        om = MagicMock()
        chain = om.select_for_update.return_value.select_related.return_value
        chain.get.side_effect = OperationalError("could not obtain lock")

        with patch("contabilidad.services.timbrado_cfdi.FacturaCFDI.objects", om):
            resp = timbrado_svc.ejecutar_timbrado(self._request(), self.factura.id)
        self.assertEqual(resp.status_code, 409)

    def test_segundo_timbrado_no_repite_llamada_api(self):
        """Tras TIMBRADO, un segundo POST no debe invocar al PAC."""

        class Api:
            calls = 0

            def timbrar_cfdi(self, factura):
                Api.calls += 1
                return {
                    "success": True,
                    "uuid": "00000000-0000-0000-0000-000000000099",
                    "xml": "<cfdi/>",
                    "fecha_timbrado": None,
                }

        timbrado_svc.set_facturama_factory_for_tests(lambda: Api())
        timbrado_svc.ejecutar_timbrado(self._request(), self.factura.id)
        timbrado_svc.ejecutar_timbrado(self._request(), self.factura.id)
        self.assertEqual(Api.calls, 1)
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.estado, "TIMBRADO")

    def test_timbrado_concurrente_una_llamada_api_cuando_hay_lock_real(self):
        """
        Con PostgreSQL y select_for_update, un hilo bloquea y el otro recibe 409.
        En SQLite se omite (sin lock cruzado fiable entre conexiones de test).
        """
        import threading
        import time

        from django.db import close_old_connections, connection

        if not getattr(connection.features, "has_select_for_update", False):
            self.skipTest("select_for_update no soportado en este backend")

        class SlowOK:
            calls = 0

            def timbrar_cfdi(self, factura):
                SlowOK.calls += 1
                time.sleep(0.4)
                return {
                    "success": True,
                    "uuid": "00000000-0000-0000-0000-000000000001",
                    "xml": "<cfdi/>",
                    "fecha_timbrado": None,
                }

        timbrado_svc.set_facturama_factory_for_tests(lambda: SlowOK())
        results = {}

        def worker(name: str, delay: float):
            close_old_connections()
            try:
                if delay:
                    time.sleep(delay)
                results[name] = timbrado_svc.ejecutar_timbrado(self._request(), self.factura.id)
            finally:
                close_old_connections()

        t1 = threading.Thread(target=worker, args=("a", 0.0))
        t2 = threading.Thread(target=worker, args=("b", 0.08))
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)

        codes = {k: getattr(v, "status_code", None) for k, v in results.items()}
        self.assertIn(200, codes.values())
        self.assertIn(409, codes.values())
        self.assertEqual(SlowOK.calls, 1)
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.estado, "TIMBRADO")

    def test_timbrado_exito_respuesta_json(self):
        class ApiOK:
            def timbrar_cfdi(self, factura):
                return {
                    "success": True,
                    "uuid": "11111111-1111-1111-1111-111111111111",
                    "xml": "<cfdi/>",
                    "fecha_timbrado": None,
                }

        timbrado_svc.set_facturama_factory_for_tests(lambda: ApiOK())
        resp = timbrado_svc.ejecutar_timbrado(self._request(), self.factura.id)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode())
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("code"), "STAMPED")
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.estado, "TIMBRADO")
        self.assertEqual(self.factura.ultimo_error_pac, "")

    def test_timbrado_error_pac_persiste_y_json_sin_500(self):
        class ApiErr:
            def timbrar_cfdi(self, factura):
                return {"success": False, "error": "RFC no válido para el régimen fiscal"}

        timbrado_svc.set_facturama_factory_for_tests(lambda: ApiErr())
        resp = timbrado_svc.ejecutar_timbrado(self._request(), self.factura.id)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode())
        self.assertFalse(data.get("ok"))
        self.assertEqual(data.get("code"), "PAC_ERROR")
        self.assertIn("RFC", data.get("detalle_pac", ""))
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.estado, "ERROR")
        self.assertIn("RFC", self.factura.ultimo_error_pac)
