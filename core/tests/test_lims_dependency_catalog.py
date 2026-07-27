from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import Empresa
from lims.models import Analito, PerfilAnalito, PerfilLims, ValorReferenciaAnalito


class LimsDependencyCatalogTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa BUN', rfc='BUN260727TST')
        self.urea = Analito.objects.create(
            empresa=self.empresa,
            codigo='URE',
            id_legacy=2111,
            abreviatura='URE',
            nombre='UREA',
            departamento='BIOQUIMICA CLINICA',
            tipo_resultado='CALCULO',
            formula='BUN*2.14',
            es_calculado=True,
        )
        self.perfil = PerfilLims.objects.create(
            empresa=self.empresa,
            nombre='QS DEPENDENCIA BUN',
        )
        PerfilAnalito.objects.create(
            empresa=self.empresa,
            perfil=self.perfil,
            analito=self.urea,
            orden=1,
        )

    def test_dry_run_no_mutates_catalog(self):
        out = StringIO()
        call_command(
            'ensure_lims_dependencies',
            empresa_id=self.empresa.id,
            dry_run=True,
            stdout=out,
        )
        self.assertFalse(Analito.objects.filter(codigo='171').exists())
        self.assertIn('BUN existente=False', out.getvalue())

    def test_reconciles_bun_ranges_and_profile_link_idempotently(self):
        call_command(
            'ensure_lims_dependencies',
            empresa_id=self.empresa.id,
            link_profiles=True,
        )
        call_command(
            'ensure_lims_dependencies',
            empresa_id=self.empresa.id,
            link_profiles=True,
        )

        bun = Analito.objects.get(codigo='171')
        self.assertEqual(bun.empresa_id, self.empresa.id)
        self.assertFalse(bun.es_calculado)
        self.assertEqual(bun.formula, '')
        self.assertEqual(bun.rangos.count(), 2)
        self.assertEqual(
            PerfilAnalito.objects.filter(perfil=self.perfil, analito=bun).count(),
            1,
        )
