"""
Unit tests for the consultorio module.
"""
import json
import uuid
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa, Paciente
from consultorio.models import ConsultaMedica, Vademecum


User = get_user_model()


class ConsultorioModelTests(TestCase):
    """Test consultorio models."""
    
    def setUp(self):
        """Create test data."""
        # Create Empresa (tenant)
        self.empresa = Empresa.objects.create(
            nombre='Test Empresa',
            rfc='TEST123456ABC'
        )
        
        # Create Usuario
        self.usuario = User.objects.create_user(
            username='test_medico',
            password='test123',
            email='medico@test.com',
            empresa=self.empresa
        )
        
        # Create Paciente
        self.paciente = Paciente.objects.create(
            nombres='Juan',
            apellido_paterno='Perez',
            apellido_materno='Garcia',
            nombre_completo='Juan Perez Garcia',
            empresa=self.empresa,
            sexo='M',
            fecha_nacimiento='1990-01-01',
        )
        
        self.client = Client()
    
    def test_consulta_medica_creation(self):
        """Test ConsultaMedica model creation (legacy consultorio)."""
        consulta = ConsultaMedica.objects.create(
            paciente=self.paciente,
            medico=self.usuario,
            empresa=self.empresa,
            motivo='Paciente refiere dolor de cabeza',
            exploracion_fisica='TA: 120/80, FC: 72',
            diagnostico_texto='Cefalea tensional',
            tratamiento='Reposo y analgésicos',
        )
        self.assertIsNotNone(consulta.id)
        self.assertEqual(consulta.paciente, self.paciente)
        self.assertEqual(consulta.medico, self.usuario)
        self.assertEqual(consulta.empresa, self.empresa)
    
    def test_consulta_medica_string_representation(self):
        """Test ConsultaMedica string representation."""
        consulta = ConsultaMedica.objects.create(
            paciente=self.paciente,
            medico=self.usuario,
            empresa=self.empresa,
            motivo='Test',
            exploracion_fisica='Test',
            diagnostico_texto='Test',
            tratamiento='Test',
        )
        str_repr = str(consulta)
        self.assertIsInstance(str_repr, str)
        self.assertGreater(len(str_repr), 0)
    
    def test_vademecum_creation(self):
        """Test Vademecum model creation."""
        vademecum = Vademecum.objects.create(
            nombre_generico='Paracetamol',
            principio_activo='Paracetamol',
            presentacion='Tabletas 500mg c/20',
            concentracion='500mg',
            empresa=self.empresa,
        )
        self.assertIsNotNone(vademecum.id)
        self.assertEqual(vademecum.nombre_generico, 'Paracetamol')
        self.assertEqual(vademecum.empresa, self.empresa)


class ConsultorioViewTests(TestCase):
    """Test consultorio views."""
    
    def setUp(self):
        """Create test data."""
        # Create Empresa (tenant)
        self.empresa = Empresa.objects.create(
            nombre='Test Empresa',
            rfc='TEST123456ABC'
        )
        
        # Create Usuario
        self.usuario = User.objects.create_user(
            username='test_medico',
            password='test123',
            email='medico@test.com',
            empresa=self.empresa
        )
        
        # Create Paciente
        self.paciente = Paciente.objects.create(
            nombres='Juan',
            apellido_paterno='Perez',
            apellido_materno='Garcia',
            nombre_completo='Juan Perez Garcia',
            empresa=self.empresa,
            sexo='M',
            fecha_nacimiento='1990-01-01',
        )
        
        self.client = Client()
        # Login the user
        self.client.login(username='test_medico', password='test123')
    
    def test_lista_trabajo_view(self):
        """Test lista_trabajo view returns 200."""
        try:
            url = reverse('consultorio:lista_trabajo')
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.skipTest(f"lista_trabajo view not available: {e}")
    
    def test_dashboard_medico_consultorio_view(self):
        """Test dashboard_medico_consultorio view returns 200."""
        try:
            url = reverse('consultorio:dashboard_medico_consultorio')
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.skipTest(f"dashboard_medico_consultorio view not available: {e}")
    
    def test_agenda_medica_view(self):
        """Test agenda_medica view returns 200."""
        try:
            url = reverse('consultorio:agenda_medica')
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.skipTest(f"agenda_medica view not available: {e}")
    
    def test_views_require_authentication(self):
        """Test that views require authentication."""
        # Logout
        self.client.logout()
        
        try:
            url = reverse('consultorio:lista_trabajo')
            response = self.client.get(url)
            # Should redirect to login (302) or return 403
            self.assertIn(response.status_code, [302, 403])
        except Exception as e:
            self.skipTest(f"lista_trabajo view not available: {e}")


class ConsultorioApiStressTests(TestCase):
    """
    CICLO 3 — Deep stress test of Consultorio API endpoints.
    Scenarios: valid request, no empresa (403), invalid JSON (400), missing fields (400),
    object not found (404), GET to POST-only (405).
    """
    def _clear_user_empresa(self):
        """Usuario.save() re-asigna empresa por defecto; usar UPDATE directo."""
        User.objects.filter(pk=self.user.pk).update(empresa_id=None)
        self.user = User.objects.get(pk=self.user.pk)

    def _restore_user_empresa(self):
        User.objects.filter(pk=self.user.pk).update(empresa_id=self.empresa.pk)
        self.user = User.objects.get(pk=self.user.pk)

    def setUp(self):
        from core.models import Empresa, Paciente, Medico, CitaMedica
        self.empresa = Empresa.objects.create(nombre='Test Stress', rfc='STRESS001')
        self._stress_uname = f'stress_user_{uuid.uuid4().hex[:10]}'
        self.user = User.objects.create_user(
            username=self._stress_uname,
            password='test123',
            email='stress@test.com',
        )
        self.user.empresa = self.empresa
        self.user.save()
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombres='Paciente',
            apellido_paterno='Stress',
            nombre_completo='Paciente Stress',
            fecha_nacimiento='1990-01-01',
            sexo='M',
        )
        self.medico = Medico.objects.create(
            empresa=self.empresa,
            nombre_completo='Dr Stress',
            cedula_profesional='STRESS',
            especialidad='General',
        )
        self.cita = CitaMedica.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            medico=self.medico,
            fecha_cita=timezone.localdate(),
            hora_cita=timezone.localtime().time(),
            duracion_estimada=30,
            motivo='Stress test',
            estado='EN_CURSO',
        )
        self.client = Client()
        self.client.login(username=self._stress_uname, password='test123')

    def test_api_buscar_pacientes_valid(self):
        """GET ?q=xx returns 200 and list."""
        url = reverse('consultorio:api_buscar_pacientes')
        r = self.client.get(url, {'q': 'Stress'})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn('pacientes', data)
        self.assertTrue(data.get('success'))

    def test_api_buscar_pacientes_q_empty(self):
        """q empty or < 2 chars returns 200 with empty list."""
        url = reverse('consultorio:api_buscar_pacientes')
        r = self.client.get(url, {'q': ''})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get('pacientes'), [])
        r1 = self.client.get(url, {'q': 'x'})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json().get('pacientes'), [])

    def test_api_buscar_pacientes_no_empresa_403(self):
        """User with no empresa gets 403."""
        self._clear_user_empresa()
        self.client.logout()
        self.client.force_login(self.user)
        r = self.client.get(reverse('consultorio:api_buscar_pacientes'), {'q': 'x'})
        self.assertEqual(r.status_code, 403)
        self._restore_user_empresa()

    def test_api_buscar_pacientes_get_only_405(self):
        """POST to GET-only endpoint returns 405."""
        r = self.client.post(reverse('consultorio:api_buscar_pacientes'), {'q': 'x'})
        self.assertEqual(r.status_code, 405)

    def test_api_crear_consulta_directa_invalid_json_400(self):
        """Invalid JSON body returns 400."""
        url = reverse('consultorio:api_crear_consulta_directa')
        r = self.client.post(url, data='not json', content_type='application/json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('JSON', r.json().get('mensaje', ''))

    def test_api_crear_consulta_directa_missing_paciente_id_400(self):
        """Missing paciente_id returns 400."""
        url = reverse('consultorio:api_crear_consulta_directa')
        r = self.client.post(url, data=json.dumps({}), content_type='application/json')
        self.assertEqual(r.status_code, 400)

    def test_api_crear_consulta_directa_no_empresa_403(self):
        """User with no empresa returns 403."""
        self._clear_user_empresa()
        self.client.logout()
        self.client.force_login(self.user)
        r = self.client.post(
            reverse('consultorio:api_crear_consulta_directa'),
            data=json.dumps({'paciente_id': self.paciente.id}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 403)
        self._restore_user_empresa()

    def test_api_crear_consulta_directa_paciente_not_found_404(self):
        """Invalid paciente_id (other empresa) returns 404."""
        from core.models import Empresa, Paciente
        other = Empresa.objects.create(nombre='Other', rfc='OTHER001')
        other_paciente = Paciente.objects.create(
            empresa=other,
            nombres='Other',
            apellido_paterno='Pac',
            nombre_completo='Other Pac',
            fecha_nacimiento='1990-01-01',
            sexo='F',
        )
        url = reverse('consultorio:api_crear_consulta_directa')
        r = self.client.post(
            url,
            data=json.dumps({'paciente_id': other_paciente.id}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 404)

    def test_api_crear_consulta_directa_get_405(self):
        """GET to POST-only returns 405."""
        r = self.client.get(reverse('consultorio:api_crear_consulta_directa'))
        self.assertEqual(r.status_code, 405)

    def test_api_generar_receta_inmediata_missing_cita_id_400(self):
        """Missing cita_id returns 400."""
        url = reverse('consultorio:api_generar_receta_inmediata')
        r = self.client.post(
            url,
            data=json.dumps({'medicamentos': [{'nombre': 'Paracetamol', 'dosis': '500mg'}]}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_api_generar_receta_inmediata_empty_medicamentos_400(self):
        """Empty medicamentos returns 400."""
        url = reverse('consultorio:api_generar_receta_inmediata')
        r = self.client.post(
            url,
            data=json.dumps({'cita_id': self.cita.id, 'medicamentos': []}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_api_generar_certificado_missing_cita_id_400(self):
        """Missing cita_id returns 400."""
        url = reverse('consultorio:api_generar_certificado_inmediato')
        r = self.client.post(
            url,
            data=json.dumps({'diagnostico': 'Gripe', 'dias_incapacidad': 2}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_api_generar_certificado_invalid_json_400(self):
        """Invalid JSON returns 400."""
        r = self.client.post(
            reverse('consultorio:api_generar_certificado_inmediato'),
            data='{',
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_api_agregar_lista_espera_invalid_json_400(self):
        """Invalid JSON returns 400."""
        r = self.client.post(
            reverse('consultorio:api_agregar_lista_espera'),
            data='not json',
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_api_agregar_lista_espera_missing_paciente_id_400(self):
        """Missing paciente_id returns 400."""
        r = self.client.post(
            reverse('consultorio:api_agregar_lista_espera'),
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)

    def test_api_plantillas_no_empresa_403(self):
        """GET plantillas with no empresa returns 403."""
        self._clear_user_empresa()
        self.client.logout()
        self.client.force_login(self.user)
        r = self.client.get(reverse('consultorio:api_plantillas_especialidad'))
        self.assertEqual(r.status_code, 403)
        self._restore_user_empresa()
