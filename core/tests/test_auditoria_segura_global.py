from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import Empresa, Paciente


class AuditoriaSeguraGlobalCommandTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Global Audit", activa=True)
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo="Paciente Global Audit",
            sexo="M",
        )

    def test_global_command_runs_and_keeps_data_intact(self):
        before = {
            "empresas": Empresa.objects.count(),
            "pacientes": Paciente.objects.count(),
        }
        out = StringIO()

        call_command(
            "auditoria_segura_global",
            "--empresa-id",
            str(self.empresa.id),
            stdout=out,
        )

        after = {
            "empresas": Empresa.objects.count(),
            "pacientes": Paciente.objects.count(),
        }

        self.assertEqual(before, after)
        output = out.getvalue()
        self.assertIn("AUDITORIA SEGURA GLOBAL", output)
        self.assertIn("auditoria_segura_farmacia", output)
        self.assertIn("auditoria_segura_laboratorio", output)
        self.assertIn("auditoria_segura_consultorio", output)
        self.assertIn("auditoria_segura_pacientes", output)
