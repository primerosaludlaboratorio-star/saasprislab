from django.contrib.auth import get_user_model
from django.test import TestCase

from core.agent.pris_tools_operativos import tool_buscar_o_crear_paciente
from core.models import Empresa, Paciente

User = get_user_model()


class BuscarOCrearPacienteConfirmationTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Pacientes", rfc="PAC123456ABC")
        self.user = User.objects.create_user(
            username="recepcion_tester",
            password="Test12345!",
            email="recepcion@test.local",
            empresa=self.empresa,
        )

    def test_pide_confirmacion_antes_de_crear_si_no_existe(self):
        respuesta = tool_buscar_o_crear_paciente(
            {
                "nombres": "Paciente Nuevo",
                "apellido_paterno": "Prueba",
                "telefono": "5551234567",
            },
            self.empresa,
            self.user,
        )

        self.assertTrue(respuesta.get("necesita_confirmacion"))
        self.assertIn("crear", respuesta.get("resumen", "").lower())
        self.assertEqual(Paciente.objects.filter(empresa=self.empresa).count(), 0)

    def test_crea_paciente_solo_cuando_ya_esta_confirmado(self):
        respuesta = tool_buscar_o_crear_paciente(
            {
                "nombres": "Paciente Nuevo",
                "apellido_paterno": "Prueba",
                "telefono": "5551234567",
                "confirmado": True,
            },
            self.empresa,
            self.user,
        )

        self.assertTrue(respuesta.get("exito"))
        self.assertEqual(Paciente.objects.filter(empresa=self.empresa).count(), 1)
