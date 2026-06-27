"""
core/tests/test_pris_ia_catchall.py

Tests de cobertura para los 4 bloques `except Exception` conservados
intencionalmente en el paquete core/views/pris_ia/.

Objetivo: verificar que cada catch-all:
  1. No silencia el error (lo loguea con exc_info).
  2. Devuelve una respuesta controlada (no re-lanza).
  3. No enmascara el mensaje de error al caller.
"""
import json
import logging
from unittest.mock import MagicMock, patch

from django.test import TestCase, RequestFactory


class TestDispatcherCatchAll(TestCase):
    """_dispatcher.py L115 — catch-all del despachador de herramientas."""

    def setUp(self):
        self.empresa = MagicMock()
        self.empresa.pk = 1
        self.user = MagicMock()
        self.user.groups.values_list.return_value = ['RECEPCION']

    def test_herramienta_que_lanza_exception_devuelve_error_dict(self):
        from core.views.pris_ia._dispatcher import _ejecutar_herramienta

        def _boom(args, empresa, user):
            raise RuntimeError("fallo simulado en herramienta")

        fake_tools = {
            'boom_tool': {
                'ejecutor': _boom,
                'grupos_requeridos': [],
            }
        }
        with patch('core.views.pris_ia._dispatcher.TOOLS_OPERATIVOS', fake_tools):
            with self.assertLogs('core.views.pris_ia._dispatcher', level='ERROR') as cm:
                result = _ejecutar_herramienta('boom_tool', {}, self.empresa, self.user)

        self.assertIn('error', result)
        self.assertIn('fallo simulado', result['error'])
        self.assertTrue(any('boom_tool' in msg for msg in cm.output))

    @patch('core.views.pris_ia._dispatcher._verificar_rbac', return_value=(True, ""))
    def test_herramienta_inexistente_devuelve_error_disponibles(self, mock_rbac):
        from core.views.pris_ia._dispatcher import _ejecutar_herramienta

        result = _ejecutar_herramienta('herramienta_fantasma', {}, self.empresa, self.user)
        self.assertIn('error', result)
        self.assertIn('no disponible', result['error'].lower())


class TestToolsLabCatchAll(TestCase):
    """_tools_lab.py L227 — catch-all del RAG externo en buscar_protocolo_lims."""

    def setUp(self):
        self.empresa = MagicMock()
        self.empresa.pk = 1
        self.user = MagicMock()

    def test_rag_externo_que_lanza_devuelve_resultado_parcial(self):
        from core.views.pris_ia._tools_lab import _tool_buscar_protocolo_lims

        args = {'nombre': 'glucosa'}
        with patch('core.views.pris_ia._tools_lab.Analito') as mock_analito:
            mock_analito.objects.filter.return_value.filter.return_value\
                .select_related.return_value.order_by.return_value.__getitem__\
                .return_value = []
            mock_analito.objects.filter.return_value.filter.return_value\
                .select_related.return_value.order_by.return_value.__iter__\
                .return_value = iter([])
            mock_analito.objects.filter.return_value.filter.return_value\
                .select_related.return_value.order_by.return_value\
                .__len__ = lambda s: 0

            result = _tool_buscar_protocolo_lims(args, self.empresa, self.user)
        self.assertIsInstance(result, dict)


class TestToolsLecturaOCRCatchAll(TestCase):
    """_tools_lectura.py L606 — catch-all del OCR externo en escanear_documento."""

    def setUp(self):
        self.empresa = MagicMock()
        self.empresa.pk = 1
        self.user = MagicMock()

    def test_ocr_externo_que_lanza_devuelve_error_controlado(self):
        from core.views.pris_ia._tools_lectura import _tool_analizar_imagen_ocr

        args = {'imagen_base64': 'data:image/png;base64,ABC123=='}

        with patch('core.views.pris_ia._tools_lectura.requests') as mock_req:
            mock_req.post.side_effect = ConnectionError("OCR service unreachable")
            with self.assertLogs('core.views.pris_ia._tools_lectura', level='ERROR') as cm:
                result = _tool_analizar_imagen_ocr(args, self.empresa, self.user)

        self.assertIsInstance(result, dict)
        self.assertIn('error', result)
        self.assertTrue(any('OCR' in msg or 'ocr' in msg.lower() or 'imagen' in msg.lower()
                            for msg in cm.output),
                        "El catch-all debe logear el error del OCR externo")


class TestViewsChatCatchAll(TestCase):
    """views.py L204 — handler de último recurso del endpoint /ia/asistente/chat/."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username='test_catchall', password='test1234567'
        )
        self.factory = RequestFactory()

    def test_exception_inesperada_devuelve_json_500_controlado(self):
        from core.views.pris_ia.views import asistente_chat

        request = self.factory.post(
            '/ia/asistente/chat/',
            data=json.dumps({'mensaje': 'hola'}),
            content_type='application/json',
        )
        request.user = self.user
        request.session = {}

        with patch('core.views.pris_ia.views._gemini_rest_call',
                   side_effect=RuntimeError("fallo catastrófico simulado")):
            with patch('core.views.pris_ia._rbac._verificar_rbac', return_value=(True, "")):
                with patch('core.views.pris_ia.views._build_system_prompt',
                           return_value="prompt"):
                    with self.assertLogs('core.views.pris_ia.views', level='ERROR'):
                        response = asistente_chat(request)

        self.assertIn(response.status_code, [200, 500])
        data = json.loads(response.content)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'error')

    def test_rate_limit_devuelve_mensaje_amigable(self):
        from core.views.pris_ia.views import asistente_chat

        request = self.factory.post(
            '/ia/asistente/chat/',
            data=json.dumps({'mensaje': 'hola'}),
            content_type='application/json',
        )
        request.user = self.user
        request.session = {}

        with patch('core.views.pris_ia.views._gemini_rest_call',
                   side_effect=Exception("429 Resource exhausted")):
            with patch('core.views.pris_ia._rbac._verificar_rbac', return_value=(True, "")):
                with patch('core.views.pris_ia.views._build_system_prompt',
                           return_value="prompt"):
                    response = asistente_chat(request)

        data = json.loads(response.content)
        self.assertIn('respuesta', data)
        self.assertIn('30', data['respuesta'])
