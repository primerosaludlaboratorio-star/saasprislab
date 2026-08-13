import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from core.views.historial_resultados import api_resultados_grafica
from core.views.incidencias import marcar_incidencia_revisada
from core.views.voice import historial_comandos


class TenantBoundaryViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.empresa = SimpleNamespace(pk=11)
        self.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
            empresa=self.empresa,
            username='director-tenant-11',
        )

    def test_result_history_requires_analito_from_request_tenant(self):
        request = self.factory.get('/historial-resultados/7/grafica/99/')
        request.user = self.user
        paciente = SimpleNamespace(pk=7)
        analito = SimpleNamespace(pk=99)
        resultados = MagicMock()
        resultados.select_related.return_value.order_by.return_value = []

        with patch(
            'core.views.historial_resultados.get_object_or_404',
            side_effect=[paciente, analito],
        ) as finder, patch(
            'core.views.historial_resultados.ResultadoParametro.objects.filter',
            return_value=resultados,
        ), patch(
            'core.views.historial_resultados._ref_min_max_analito',
            return_value=(None, None),
        ), patch(
            'core.views.historial_resultados.JsonResponse',
            return_value='response',
        ):
            api_resultados_grafica.__wrapped__(request, paciente_id=7, estudio_id=99)

        self.assertEqual(finder.call_args_list[1].kwargs['empresa'], self.empresa)

    def test_incidence_review_cannot_cross_tenant(self):
        request = self.factory.post(
            '/incidencias/99/revisar/',
            data=json.dumps({'estado': 'JUSTIFICADA'}),
            content_type='application/json',
        )
        request.user = self.user
        incidencia = SimpleNamespace(
            estado_revision='PENDIENTE',
            revisado_por=None,
            fecha_revision=None,
            comentario_revision=None,
            get_estado_revision_display=lambda: 'Justificada',
            save=MagicMock(),
        )

        with patch(
            'core.views.incidencias.get_object_or_404',
            return_value=incidencia,
        ) as finder:
            response = marcar_incidencia_revisada.__wrapped__(request, 99)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(finder.call_args.kwargs['empresa'], self.empresa)

    def test_voice_director_history_is_limited_to_request_tenant(self):
        request = self.factory.get('/api/voice/historial/')
        request.user = self.user
        manager = MagicMock()
        manager.filter.return_value.count.return_value = 0
        manager.filter.return_value.__getitem__.return_value = []

        with patch('core.views.voice.VoiceAuditLog.objects', manager):
            response = historial_comandos.__wrapped__(request)

        self.assertEqual(response.status_code, 200)
        manager.filter.assert_called_once_with(empresa=self.empresa)
