from django.test import SimpleTestCase

from core.views.pris_ia.views import _sanitizar_prompt_externo, _serializar_resultado_externo


class PrisAiPrivacyTests(SimpleTestCase):
    def test_redacts_patient_fields_before_external_provider(self):
        prompt = (
            '{"paciente":"María López", "paciente_nombre":"María López", "telefono":"2281234567", '
            '"fecha_nacimiento":"1980-01-02", "resultado":"120"}'
        )
        safe = _sanitizar_prompt_externo(prompt)
        self.assertNotIn('María López', safe)
        self.assertNotIn('2281234567', safe)
        self.assertNotIn('1980-01-02', safe)
        self.assertIn('[REDACTADO]', safe)

    def test_redacts_nested_patient_tool_results(self):
        safe = _serializar_resultado_externo({
            'pacientes': [{'id': 7, 'nombre': 'Juan Pérez', 'telefono': '2281234567'}],
            'estudios': [{'nombre': 'Glucosa'}],
        })
        self.assertNotIn('Juan Pérez', safe)
        self.assertNotIn('2281234567', safe)
        self.assertIn('Glucosa', safe)
