from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import CitaMedica, ConsultaMedica, Empresa, Paciente


class AuditoriaSeguraConsultorioCommandTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Consultorio Audit", activa=True)
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo="Paciente Audit",
            sexo="M",
        )

    def test_command_runs_without_mutating_counts(self):
        before = {
            "empresas": Empresa.objects.count(),
            "pacientes": Paciente.objects.count(),
            "citas": CitaMedica.objects.count(),
            "consultas": ConsultaMedica.objects.count(),
        }
        out = StringIO()

        call_command(
            "auditoria_segura_consultorio",
            "--empresa-id",
            str(self.empresa.id),
            stdout=out,
        )

        after = {
            "empresas": Empresa.objects.count(),
            "pacientes": Paciente.objects.count(),
            "citas": CitaMedica.objects.count(),
            "consultas": ConsultaMedica.objects.count(),
        }

        self.assertEqual(before, after)
        output = out.getvalue()
        self.assertIn("AUDITORIA SEGURA CONSULTORIO", output)
        self.assertIn("snapshot_consultorio", output)
