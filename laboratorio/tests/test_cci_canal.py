from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import Empresa
from lims.models import Analito
from laboratorio.cci_models import EstadoCanalAnalizador
from laboratorio.models import Equipo
from laboratorio.services.cci_canal import actualizar_canal_por_westgard


class CciCanalFailureHandlingTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='CCI Error Handling')
        self.equipo = Equipo.objects.create(nombre='Equipo CCI Error Handling')
        self.analito = Analito.objects_all.create(
            empresa=self.empresa,
            codigo='CCI-ERROR-HANDLING',
            abreviatura='CCIERR',
            nombre='Analito CCI Error Handling',
            departamento='Quimica clinica',
        )

    @patch('inventario.models.NotificacionDiscrepancia.objects.create')
    def test_notification_validation_error_does_not_break_channel_block(self, create_notification):
        create_notification.side_effect = ValidationError('notification payload rejected')

        actualizar_canal_por_westgard(
            self.empresa,
            self.equipo,
            self.analito,
            'RECHAZO',
            ['1_3s'],
        )

        estado = EstadoCanalAnalizador.objects.get(
            empresa=self.empresa,
            equipo=self.equipo,
            analito=self.analito,
        )
        self.assertEqual(estado.estado_operativo, EstadoCanalAnalizador.ALERTA_QC)
