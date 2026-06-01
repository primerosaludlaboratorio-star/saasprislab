"""Enfoque 5 — Contrato HL7 JSON (mock dispositivo); standby vs auth."""
import json

from django.test import Client, TestCase, override_settings

from core.models import Empresa


class Hl7MockDeviceTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_sin_api_key_responde_401_cuando_activo(self):
        with override_settings(HL7_ACTIVE=True, HL7_API_KEY='cursor-guardian-key'):
            r = self.client.post(
                '/api/iot/hl7/',
                data=json.dumps({'protocolo': 'JSON', 'resultados': []}),
                content_type='application/json',
            )
        self.assertEqual(r.status_code, 401)

    def test_con_api_key_json_vacio_integra_cero(self):
        emp = Empresa.objects.create(nombre='Emp HL7 Mock', rfc='HL7M123456AA')
        with override_settings(HL7_ACTIVE=True, HL7_API_KEY='cursor-guardian-key'):
            r = self.client.post(
                '/api/iot/hl7/',
                data=json.dumps({'protocolo': 'JSON', 'resultados': []}),
                content_type='application/json',
                HTTP_X_PRISLAB_API_KEY='cursor-guardian-key',
                HTTP_X_EMPRESA_ID=str(emp.pk),
            )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get('ok') is True or body.get('integrados') == 0)
