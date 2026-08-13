import json
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from core.models import CitaMedica, ConsultaMedica, Empresa, Medico, Paciente, Usuario


class ConsultorioAiSecurityTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Consultorio IA', rfc='CIA010101AAA')
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente de Prueba',
            nombres='Paciente',
            apellido_paterno='de Prueba',
            fecha_nacimiento='1990-01-01',
            sexo='F',
        )
        self.medico_user = Usuario.objects.create_user(
            username='medico_ia', password='pass12345', empresa=self.empresa,
            rol='MEDICO', cedula_interna='IA-MED-1',
        )
        self.otro_medico_user = Usuario.objects.create_user(
            username='otro_medico_ia', password='pass12345', empresa=self.empresa,
            rol='MEDICO', cedula_interna='IA-MED-2',
        )
        self.medico = Medico.objects.create(
            empresa=self.empresa, nombre_completo='Medico IA',
            cedula_profesional='IA-MED-1', especialidad='General',
        )
        self.otro_medico = Medico.objects.create(
            empresa=self.empresa, nombre_completo='Otro Medico IA',
            cedula_profesional='IA-MED-2', especialidad='General',
        )
        self.cita = CitaMedica.objects.create(
            empresa=self.empresa, paciente=self.paciente, medico=self.medico,
            fecha_cita='2026-08-13', hora_cita='09:00', motivo='Seguimiento',
        )
        self.consulta = ConsultaMedica.objects.create(
            empresa=self.empresa, paciente=self.paciente, medico=self.medico,
            cita=self.cita, folio_consulta='CONS-IA-001', estado='EN_CURSO',
        )
        self.client = Client()

    def test_medico_no_puede_sobrescribir_transcripcion_de_otra_consulta(self):
        self.client.login(username='otro_medico_ia', password='pass12345')
        with patch('core.utils.gemini_client.generate_content', return_value=json.dumps({
            'motivo_consulta': 'texto', 'pronostico': 'BUENO',
            'medicamentos_detectados': [], 'signos_vitales_detectados': {},
        })):
            response = self.client.post(
                reverse('consultorio:api_analizar_transcripcion'),
                data=json.dumps({'cita_id': self.cita.id, 'transcripcion_completa': 'texto'}),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 403)
        self.consulta.refresh_from_db()
        self.assertFalse(self.consulta.transcripcion_completa)

    def test_respuesta_ia_no_puede_inyectar_campos_fuera_del_contrato(self):
        self.client.login(username='medico_ia', password='pass12345')
        payload = {
            'motivo_consulta': 'texto', 'pronostico': 'BUENO',
            'medicamentos_detectados': [], 'signos_vitales_detectados': {},
            'campo_interno_no_permitido': 'no debe salir',
        }
        with patch('core.utils.gemini_client.generate_content', return_value=json.dumps(payload)):
            response = self.client.post(
                reverse('consultorio:api_analizar_transcripcion'),
                data=json.dumps({'transcripcion_completa': 'texto'}),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('campo_interno_no_permitido', response.json()['campos_soap'])
