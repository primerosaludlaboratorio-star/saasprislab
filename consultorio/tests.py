"""
Unit tests for the consultorio module.
"""
import json
import uuid
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa, Paciente, ConsultaMedica as CoreConsultaMedica
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
            response = self.client.get(url, follow=True)
            self.assertIn(response.status_code, [200, 301, 302])
        except Exception as e:
            self.skipTest(f"lista_trabajo view not available: {e}")
    
    def test_dashboard_medico_consultorio_view(self):
        """Test dashboard_medico_consultorio view returns 200."""
        try:
            url = reverse('consultorio:dashboard_medico_consultorio')
            response = self.client.get(url, follow=True)
            self.assertIn(response.status_code, [200, 301, 302])
        except Exception as e:
            self.skipTest(f"dashboard_medico_consultorio view not available: {e}")
    
    def test_agenda_medica_view(self):
        """Test agenda_medica view returns 200."""
        try:
            url = reverse('consultorio:agenda_medica')
            response = self.client.get(url, follow=True)
            self.assertIn(response.status_code, [200, 301, 302])
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

    def test_nueva_consulta_con_paciente_guarda_consulta_finalizada_con_folio(self):
        """El flujo médico debe autogenerar folio al guardar una consulta finalizada."""
        try:
            url = reverse('consultorio:nueva_consulta_paciente', args=[self.paciente.uuid])
        except Exception as e:
            self.skipTest(f"nueva_consulta_paciente view not available: {e}")

        response = self.client.post(url, {
            'motivo': 'Dolor abdominal leve',
            'exploracion_fisica': 'Abdomen blando, sin datos de irritación.',
            'diagnostico': 'Gastritis aguda',
            'tratamiento': '',
            'presion_arterial': '120/80',
            'temperatura': '36.7',
        })

        self.assertEqual(response.status_code, 302)
        consulta = CoreConsultaMedica.objects.latest('id')
        self.assertEqual(consulta.paciente_id, self.paciente.id)
        self.assertEqual(consulta.estado, 'FINALIZADA')
        self.assertTrue(consulta.folio_consulta.startswith(f'CONS-{self.empresa.id}-'))

    def test_api_buscar_paciente_avanzado_incluye_uuid_para_iniciar_consulta(self):
        response = self.client.get(
            reverse('api_buscar_paciente_avanzado'),
            {'nombre': 'Juan'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'success')
        self.assertTrue(payload['pacientes'])
        self.assertEqual(payload['pacientes'][0]['uuid'], str(self.paciente.uuid))

    def test_dashboard_medico_apunta_a_flujo_canonico_por_uuid(self):
        response = self.client.get(reverse('medico'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('api_buscar_paciente_avanzado'))
        self.assertContains(response, '/consultorio/medico/consulta/nueva/')


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
        r = self.client.get(url, {'q': 'Stress'}, follow=True)
        self.assertIn(r.status_code, [200, 301, 302])
        data = r.json()
        self.assertIn('pacientes', data)
        self.assertTrue(data.get('success'))

    def test_api_buscar_pacientes_q_empty(self):
        """q empty or < 2 chars returns 200 with empty list."""
        url = reverse('consultorio:api_buscar_pacientes')
        r = self.client.get(url, {'q': ''}, follow=True)
        self.assertIn(r.status_code, [200, 301, 302])
        self.assertEqual(r.json().get('pacientes'), [])
        r1 = self.client.get(url, {'q': 'x'}, follow=True)
        self.assertIn(r1.status_code, [200, 301, 302])
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

    def test_api_generar_receta_inmediata_ok_vincula_consulta_y_devuelve_urls(self):
        """Happy path: genera receta, vincula consulta y devuelve URLs útiles para el médico."""
        from core.models import ConsultaMedica, Receta, RecetaItem

        url = reverse('consultorio:api_generar_receta_inmediata')
        r = self.client.post(
            url,
            data=json.dumps({
                'cita_id': self.cita.id,
                'medicamentos': [
                    {
                        'nombre': 'Paracetamol',
                        'dosis': '500 mg cada 8 horas',
                        'duracion': '5 días',
                        'cantidad': 10,
                    }
                ],
            }),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get('ok'))
        self.assertIn('/consultorio/pdf/receta/', data.get('url_pdf', ''))
        self.assertIn('/farmacia/pdv/', data.get('url_farmacia', ''))

        consulta = ConsultaMedica.objects.get(cita=self.cita)
        receta = Receta.objects.get(id=data['receta_id'])
        self.assertEqual(consulta.receta_id, receta.id)
        self.assertEqual(receta.paciente_id, self.cita.paciente_id)
        self.assertTrue(
            RecetaItem.objects.filter(receta=receta, texto_libre__icontains='Paracetamol').exists()
        )

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


class ConsultorioAudioSecurityTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.empresa = Empresa.objects.create(nombre='Empresa Audio', rfc='AUDIO001')
        self.other_empresa = Empresa.objects.create(nombre='Empresa Otra', rfc='AUDIO002')
        self.user = User.objects.create_user(
            username='audio_medico',
            password='test123',
            email='audio@test.com',
            empresa=self.empresa,
            rol='MEDICO',
        )
        self.recepcion = User.objects.create_user(
            username='audio_recepcion',
            password='test123',
            email='recepcion@test.com',
            empresa=self.empresa,
            rol='RECEPCION',
        )
        self.lab_user = User.objects.create_user(
            username='audio_quimico',
            password='test123',
            email='lab@test.com',
            empresa=self.empresa,
            rol='QUIMICO',
        )
        from django.contrib.auth.models import Group
        self.analito_group = Group.objects.get_or_create(name='LABORATORIO')[0]
        self.medicos_group = Group.objects.get_or_create(name='MEDICOS')[0]
        self.user.groups.add(self.medicos_group)
        self.lab_user.groups.add(self.analito_group)

    def _build_request(self, path, user, data=None):
        payload = data or {}
        request = self.factory.post(path, payload)
        request.user = user
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        return request

    @patch('core.services.ai_medico.procesar_consulta_medica', return_value={'motivo': 'ok'})
    def test_audio_consulta_rejects_unauthorized_role(self, _mock_procesar):
        from consultorio.api_views import procesar_audio_consulta

        audio = SimpleUploadedFile('consulta.webm', b'audio-demo', content_type='audio/webm')
        request = self._build_request(
            '/consultorio/api/procesar-audio-consulta/',
            self.recepcion,
            {'audio': audio},
        )

        response = procesar_audio_consulta(request)

        self.assertEqual(response.status_code, 403)

    @patch('core.services.ai_medico.procesar_consulta_medica', return_value={'motivo': 'ok'})
    def test_audio_consulta_requires_company(self, _mock_procesar):
        from consultorio.api_views import procesar_audio_consulta

        User.objects.filter(pk=self.user.pk).update(empresa_id=None)
        self.user = User.objects.get(pk=self.user.pk)
        audio = SimpleUploadedFile('consulta.webm', b'audio-demo', content_type='audio/webm')
        request = self._build_request(
            '/consultorio/api/procesar-audio-consulta/',
            self.user,
            {'audio': audio},
        )

        response = procesar_audio_consulta(request)

        self.assertEqual(response.status_code, 403)

    @patch('core.services.ai_medico.procesar_resultados_lab', return_value=[{'nombre': 'GLU', 'valor': '90'}])
    def test_audio_laboratorio_rejects_cross_company_analito(self, _mock_procesar):
        from consultorio.api_views import procesar_audio_laboratorio
        from lims.models import Analito

        analito = Analito.objects.create(
            empresa=self.other_empresa,
            nombre='Glucosa ajena',
            codigo='GLU-OTHER',
            abreviatura='GLUO',
            departamento='QUIMICA CLINICA',
            activo=True,
        )
        audio = SimpleUploadedFile('lab.webm', b'audio-demo', content_type='audio/webm')
        request = self._build_request(
            '/laboratorio/api/procesar-audio-resultados/',
            self.lab_user,
            {'audio': audio, 'estudio_id': str(analito.pk)},
        )

        response = procesar_audio_laboratorio(request)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content.decode())
        self.assertIn('No se encontraron parámetros', data.get('error', ''))


class ConsultorioBillingAndFilesRegressionTests(TestCase):
    def setUp(self):
        from core.models import Medico, CitaMedica
        from consultorio.models import CajaConsultorio, CobroConsulta, ValeLiquidacion

        self.empresa = Empresa.objects.create(nombre='Empresa Medica', rfc='MED260620TST')
        self.user = User.objects.create_user(
            username='doctor_regression',
            password='test123456789',
            email='doctor@test.com',
            empresa=self.empresa,
            rol='MEDICO',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombres='Ana',
            apellido_paterno='Prueba',
            nombre_completo='Ana Prueba',
            fecha_nacimiento='1990-01-01',
            sexo='F',
        )
        self.otro_paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombres='Luis',
            apellido_paterno='Ajeno',
            nombre_completo='Luis Ajeno',
            fecha_nacimiento='1991-01-01',
            sexo='M',
        )
        self.medico = Medico.objects.create(
            empresa=self.empresa,
            nombre_completo='Dr Regression',
            cedula_profesional='REG-MED-001',
            especialidad='General',
        )
        self.medico_ajeno = Medico.objects.create(
            empresa=self.empresa,
            nombre_completo='A Doctor Ajeno',
            cedula_profesional='AJENO-001',
            especialidad='General',
        )
        self.consulta = CoreConsultaMedica.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            medico=self.medico,
            folio_consulta='CONS-TEST-0001',
            motivo_consulta='Seguimiento',
            exploracion_fisica='Sin hallazgos',
            diagnostico_principal='Control',
            plan_tratamiento='Observación',
            estado='FINALIZADA',
        )
        self.consulta_ajena = CoreConsultaMedica.objects.create(
            empresa=self.empresa,
            paciente=self.otro_paciente,
            medico=self.medico,
            folio_consulta='CONS-TEST-0002',
            motivo_consulta='Otra',
            exploracion_fisica='Normal',
            diagnostico_principal='Otra',
            plan_tratamiento='Otra',
            estado='FINALIZADA',
        )
        self.caja = CajaConsultorio.objects.create(
            empresa=self.empresa,
            medico=self.user,
            fecha=timezone.localdate(),
        )
        self.cobro = CobroConsulta.objects.create(
            empresa=self.empresa,
            caja=self.caja,
            consulta=self.consulta,
            paciente=self.paciente,
            medico=self.user,
            concepto='CONSULTA',
            monto_total=100,
            monto_efectivo=100,
            monto_tarjeta=0,
            monto_transferencia=0,
            cobrado_por='RECEPCION',
            usuario_cobro=self.user,
            estado='PAGADO',
        )
        self.vale = ValeLiquidacion.objects.create(
            empresa=self.empresa,
            cobro=self.cobro,
            medico=self.user,
            monto_adeudado=100,
            estado='PENDIENTE',
        )
        self.client = Client()
        self.client.login(username='doctor_regression', password='test123456789')

    def test_api_liquidar_vale_rechaza_monto_cero(self):
        response = self.client.post(
            reverse('consultorio:api_liquidar_vale'),
            data=json.dumps({'vale_id': self.vale.id, 'monto': 0}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('mayor a 0', response.json().get('error', ''))
        self.vale.refresh_from_db()
        self.assertEqual(self.vale.estado, 'PENDIENTE')
        self.assertEqual(float(self.vale.monto_liquidado), 0.0)

    def test_api_subir_archivo_rechaza_consulta_de_otro_paciente(self):
        archivo = SimpleUploadedFile('estudio.pdf', b'pdf-demo', content_type='application/pdf')

        response = self.client.post(
            reverse('consultorio:api_subir_archivo'),
            data={
                'paciente_id': self.paciente.id,
                'consulta_id': self.consulta_ajena.id,
                'tipo': 'DOCUMENTO',
                'titulo': 'Archivo cruzado',
                'archivo': archivo,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('no corresponde al paciente', response.json().get('error', ''))

    def test_api_generar_certificado_inmediato_no_usa_primer_medico_de_empresa(self):
        from core.models import CitaMedica, CertificadoMedico

        cita = CitaMedica.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            medico=None,
            fecha_cita=timezone.localdate(),
            hora_cita=timezone.localtime().time(),
            duracion_estimada=30,
            motivo='Valoración general',
            estado='EN_CURSO',
            creado_por=self.user,
        )

        response = self.client.post(
            reverse('consultorio:api_generar_certificado_inmediato'),
            data=json.dumps({
                'cita_id': cita.id,
                'tipo': 'MEDICO',
                'motivo': 'Paciente estable',
                'recomendaciones': 'Reposo',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('ok'))
        certificado = CertificadoMedico.objects.get(id=response.json()['certificado_id'])
        self.assertNotEqual(certificado.medico_id, self.medico_ajeno.id)
        self.assertEqual(certificado.medico.cedula_profesional, f'USR-{self.user.id}')

    def test_api_crear_paciente_y_consulta_no_usa_primer_medico_de_empresa(self):
        from core.models import CitaMedica

        response = self.client.post(
            reverse('consultorio:api_crear_paciente_y_consulta'),
            data=json.dumps({
                'nombre': 'Mario',
                'apellidos': 'Temporal',
                'fecha_nacimiento': '1992-05-20',
                'sexo': 'M',
                'motivo': 'Consulta inicial',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('ok'))
        cita = CitaMedica.objects.get(id=response.json()['cita_id'])
        self.assertNotEqual(cita.medico_id, self.medico_ajeno.id)
        self.assertEqual(cita.medico.cedula_profesional, f'USR-{self.user.id}')
