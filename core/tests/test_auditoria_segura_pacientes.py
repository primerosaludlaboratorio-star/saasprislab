from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import Empresa, Paciente
from pacientes.portal_models import SolicitudAccesoPortal, UsuarioPaciente


class AuditoriaSeguraPacientesCommandTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Pacientes Audit", activa=True)
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo="Paciente Portal Audit",
            sexo="F",
        )

    def test_command_runs_without_mutating_counts(self):
        before = {
            "empresas": Empresa.objects.count(),
            "pacientes": Paciente.objects.count(),
            "usuarios_portal": UsuarioPaciente.objects.count(),
            "solicitudes": SolicitudAccesoPortal.objects.count(),
        }
        out = StringIO()

        call_command(
            "auditoria_segura_pacientes",
            "--empresa-id",
            str(self.empresa.id),
            stdout=out,
        )

        after = {
            "empresas": Empresa.objects.count(),
            "pacientes": Paciente.objects.count(),
            "usuarios_portal": UsuarioPaciente.objects.count(),
            "solicitudes": SolicitudAccesoPortal.objects.count(),
        }

        self.assertEqual(before, after)
        output = out.getvalue()
        self.assertIn("AUDITORIA SEGURA PACIENTES", output)
        self.assertIn("snapshot_pacientes", output)
