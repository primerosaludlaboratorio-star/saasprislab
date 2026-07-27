from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import Empresa
from lims.models import Analito
from laboratorio.models import NoConformidad, RondaEQA, ResultadoEQA


class ComplianceISO15189Tests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Compliance Test', rfc='CMP260727AAA')
        self.user = get_user_model().objects.create_user(
            username='compliance_owner', password='strong-test-password',
            empresa=self.empresa, rol='DIRECTOR',
        )

    def test_capa_requires_evidence_before_closing(self):
        item = NoConformidad.objects.create(
            empresa=self.empresa,
            titulo='Control no documentado',
            descripcion='Falta evidencia de control.',
            origen='AUDITORIA_INTERNA',
            detectada_por=self.user,
        )
        item.transition('INVESTIGACION', self.user)
        item.causa_raiz = 'Procedimiento no actualizado.'
        item.accion_correctiva = 'Actualizar procedimiento y capacitar.'
        item.transition('ACCION_CORRECTIVA', self.user)
        item.transition('VERIFICACION', self.user)

        with self.assertRaises(ValidationError):
            item.transition('CERRADA', self.user)

        item.evidencia_verificacion = 'Acta CAPA-001 y muestra de auditoria.'
        item.transition('CERRADA', self.user)
        self.assertEqual(item.eventos.count(), 4)

    def test_eqa_z_score_and_evaluation_are_calculated(self):
        analito = Analito.objects.create(
            empresa=self.empresa,
            nombre='Glucosa EQA',
            codigo='EQA-GLU',
            abreviatura='GLU',
            departamento='Quimica clinica',
        )
        ronda = RondaEQA.objects.create(
            empresa=self.empresa, proveedor='Proveedor PEEC',
            programa='Quimica clinica', codigo_ronda='2026-01',
            responsable=self.user,
        )
        resultado = ResultadoEQA.objects.create(
            ronda=ronda, analito=analito,
            resultado_laboratorio=Decimal('102'),
            media_grupo=Decimal('100'),
            desviacion_grupo=Decimal('2'),
        )

        self.assertEqual(resultado.evaluar(), 'SATISFACTORIO')
        self.assertEqual(resultado.z_score, Decimal('1'))
