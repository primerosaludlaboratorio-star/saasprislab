from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import Empresa, OrdenDeServicio
from lims.models import Analito


class AuditoriaSeguraLaboratorioCommandTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Lab Audit", activa=True)
        self.analito = Analito.objects.create(
            empresa=self.empresa,
            codigo="GLU-AUD",
            abreviatura="GLU",
            nombre="Glucosa Audit",
            departamento="QUIMICA CLINICA",
            costo_lista=0,
        )

    def test_command_runs_without_mutating_counts(self):
        before = {
            "empresas": Empresa.objects.count(),
            "analitos": Analito.objects.count(),
            "ordenes": OrdenDeServicio.objects.count(),
        }
        out = StringIO()

        call_command(
            "auditoria_segura_laboratorio",
            "--empresa-id",
            str(self.empresa.id),
            stdout=out,
        )

        after = {
            "empresas": Empresa.objects.count(),
            "analitos": Analito.objects.count(),
            "ordenes": OrdenDeServicio.objects.count(),
        }

        self.assertEqual(before, after)
        output = out.getvalue()
        self.assertIn("AUDITORIA SEGURA LABORATORIO", output)
        self.assertIn("snapshot_laboratorio", output)
