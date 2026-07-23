from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from core.services.lims.coherencia_clinica import (
    evaluar_orden_canonica,
    evaluar_resultado_canonico,
)


class CoherenciaClinicaContractTest(SimpleTestCase):
    def test_resultado_sin_analito_no_se_considera_clinicamente_validable(self):
        resultado = SimpleNamespace(analito_id=None, valor='95')
        orden = SimpleNamespace(paciente=None)

        payload = evaluar_resultado_canonico(resultado, orden)

        self.assertEqual(payload['fuente'], 'SIN_ANALITO')
        self.assertFalse(payload['es_critico'])

    @patch('core.services.lims.coherencia_clinica.validar_resultado_analito_lims')
    def test_resultado_usa_contexto_lims_y_no_muta(self, validar):
        validar.return_value = SimpleNamespace(
            nivel='CRITICO_ALTO',
            es_critico=True,
            es_anormal=True,
            mensaje='critico',
            rango_min=1,
            rango_max=10,
            critico_min=None,
            critico_max=20,
        )
        resultado = SimpleNamespace(analito_id=7, valor='25')
        orden = SimpleNamespace(paciente=None, paciente_edad_snapshot=40, paciente_sexo_snapshot='M')

        payload = evaluar_resultado_canonico(resultado, orden)

        validar.assert_called_once_with(
            7,
            '25',
            edad_paciente=40,
            sexo_paciente='M',
            edad_dias=None,
        )
        self.assertEqual(payload['fuente'], 'LIMS_VALOR_REFERENCIA_ANALITO')
        self.assertTrue(payload['es_critico'])

    @patch('core.services.lims.coherencia_clinica.evaluar_asistencia_clinica_orden')
    def test_orden_expone_capas_y_conserva_candado_humano(self, evaluar):
        evaluar.return_value = {'debe_bloquear': False, 'alertas': []}
        orden = object()
        empresa = object()
        payload = evaluar_orden_canonica(orden, empresa, accion='validar')

        self.assertTrue(payload['capas']['rangos_lims'])
        self.assertTrue(payload['capas']['liberacion_humana'])
        self.assertEqual(payload['fuente_orquestacion'], 'core.services.lims.coherencia_clinica')
