from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from core.utils.lims_tokens_v75 import MotorOrdenesLIMS
from core.utils.notificaciones import crear_notificacion


class LegacyUtilsRepairTests(SimpleTestCase):
    def test_notification_bridge_writes_to_current_model(self):
        manager = MagicMock()
        expected = object()
        manager.create.return_value = expected

        with patch('core.utils.notificaciones.NotificacionSistema.objects', manager):
            result = crear_notificacion(
                tipo='CADUCIDAD_VENCIDA',
                titulo='Lote vencido',
                mensaje='Retirar lote',
                empresa=SimpleNamespace(pk=7),
                referencia_tipo='Lote',
                referencia_id=22,
                accion_url='/farmacia/lote/22/',
            )

        self.assertIs(result, expected)
        kwargs = manager.create.call_args.kwargs
        self.assertEqual(kwargs['tipo'], 'CRITICO')
        self.assertEqual(kwargs['objeto_tipo'], 'Lote')
        self.assertEqual(kwargs['objeto_id'], '22')
        self.assertEqual(kwargs['enlace'], '/farmacia/lote/22/')

    def test_lims_token_resolution_is_scoped_to_empresa(self):
        manager = MagicMock()
        manager.filter.return_value.first.return_value = None
        empresa = SimpleNamespace(pk=7)

        with patch('lims.models.Analito.objects', manager):
            result = MotorOrdenesLIMS._resolver_token(
                {'tipo': 'analito', 'codigo': 'GLU'},
                empresa=empresa,
            )

        self.assertIsNone(result)
        self.assertEqual(manager.filter.call_args_list[0].kwargs['empresa'], empresa)
        self.assertEqual(manager.filter.call_args_list[1].kwargs['empresa'], empresa)

