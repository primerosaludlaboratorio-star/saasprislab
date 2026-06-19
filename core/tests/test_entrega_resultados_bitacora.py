import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import signing
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import BitacoraEntregaResultados, ConsentimientoInformado, Empresa, OrdenDeServicio, Paciente


Usuario = get_user_model()


class EntregaResultadosBitacoraTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Entrega", rfc="ENT260507TST")
        self.usuario = Usuario.objects.create_user(
            username="entrega_user",
            password="test123456789",
            empresa=self.empresa,
            rol="ADMIN",
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo="Paciente Entrega",
            sexo="F",
            email="paciente@example.com",
            telefono="9211234567",
        )
        self.client.login(username="entrega_user", password="test123456789")

    def _crear_orden(self, estado="RESULTADOS_LISTOS"):
        orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            responsable_ingreso=self.usuario,
            total=Decimal("100.00"),
            anticipo=Decimal("100.00"),
            estado="PAGADO",
        )
        OrdenDeServicio.objects.filter(id=orden.id).update(
            estado=estado,
            archivo_resultado="resultados_pdf/test.pdf",
        )
        orden.refresh_from_db()
        ConsentimientoInformado.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            orden=orden,
            firma_digital="data:image/png;base64,abc",
            acepta_privacidad=True,
            acepta_procesamiento=True,
        )
        return orden

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="noreply@example.com")
    def test_envio_email_crea_bitacora_core(self):
        orden = self._crear_orden()

        response = self.client.post(
            reverse("api_enviar_email_masivo_resultados"),
            data=json.dumps({"ordenes": [orden.id]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        bitacora = BitacoraEntregaResultados.objects.get(orden_id=orden.id, canal="EMAIL")
        self.assertEqual(bitacora.empresa, self.empresa)
        self.assertEqual(bitacora.destino_envio, "paciente@example.com")
        self.assertEqual(bitacora.usuario_entrega, self.usuario)

    def test_portal_publico_crea_bitacora_de_lectura(self):
        orden = self._crear_orden(estado="ENTREGADO")
        token = signing.dumps({"oid": orden.id, "eid": self.empresa.id}, salt="resultados-publicos")

        response = self.client.get(reverse("resultados_publicos", args=[token]))

        self.assertEqual(response.status_code, 200)
        bitacora = BitacoraEntregaResultados.objects.get(orden_id=orden.id, canal="PORTAL")
        self.assertTrue(bitacora.confirmado_lectura)
        self.assertEqual(bitacora.paciente_nombre, "Paciente Entrega")

    def test_whatsapp_crea_bitacora_core(self):
        orden = self._crear_orden()

        response = self.client.post(reverse("api_marcar_whatsapp_enviado", args=[orden.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        bitacora = BitacoraEntregaResultados.objects.get(orden_id=orden.id, canal="WHATSAPP")
        self.assertEqual(bitacora.destino_envio, "9211234567")
        self.assertEqual(bitacora.usuario_entrega, self.usuario)
