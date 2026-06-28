"""
Tests para el módulo de Enfermería.
Cubre captura de signos vitales, triage, tenant, permisos y alertas clínicas.
"""
from datetime import date, time

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.models import Empresa, Paciente, CitaMedica, SignosVitales

Usuario = get_user_model()


class EnfermeriaURLTest(TestCase):
    """Verifica que las URLs del módulo resuelven correctamente."""

    def test_urls_resuelven_ok(self):
        urls = [
            'enfermeria:dashboard_enfermeria',
            'enfermeria:lista_pacientes_triage',
            'enfermeria:alertas_signos_criticos',
        ]
        for url_name in urls:
            with self.subTest(url=url_name):
                url = reverse(url_name)
                self.assertIsNotNone(url)

    def test_urls_con_parametros_resuelven_ok(self):
        self.assertIsNotNone(reverse('enfermeria:capturar_signos_vitales', args=[1]))
        self.assertIsNotNone(reverse('enfermeria:historial_signos_paciente', args=[1]))
        self.assertIsNotNone(reverse('enfermeria:graficas_tendencias', args=[1]))


class EnfermeriaVistaTest(TestCase):
    """Pruebas funcionales de las vistas del módulo enfermería."""

    def setUp(self):
        self.client = Client()
        self.empresa = Empresa.objects.create(nombre='Clínica Test')
        self.empresa_otra = Empresa.objects.create(nombre='Otra Clínica')
        self.user = Usuario.objects.create_user(
            username='enfermera',
            password='testpass123',
            empresa=self.empresa,
            rol='RECEPCION',
        )
        self.user_sin_empresa = Usuario.objects.create_user(
            username='sinempresa',
            password='testpass123',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente Test',
            nombres='Paciente',
            apellido_paterno='Test',
        )
        self.paciente_otra = Paciente.objects.create(
            empresa=self.empresa_otra,
            nombre_completo='Paciente Otra',
            nombres='Paciente',
            apellido_paterno='Otra',
        )
        self.cita = CitaMedica.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            fecha_cita=date.today(),
            hora_cita=time(10, 0),
            motivo='Consulta general',
            estado='EN_SALA',
        )

    def test_dashboard_requiere_login(self):
        response = self.client.get(reverse('enfermeria:dashboard_enfermeria'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_usuario_sin_empresa_redirige(self):
        self.client.force_login(self.user_sin_empresa)
        response = self.client.get(reverse('enfermeria:dashboard_enfermeria'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_muestra_metricas(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('enfermeria:dashboard_enfermeria'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'enfermeria/dashboard.html')
        self.assertEqual(response.context['pacientes_pendientes'], 1)
        self.assertEqual(response.context['empresa'], self.empresa)

    def test_lista_triage_filtra_por_empresa(self):
        CitaMedica.objects.create(
            empresa=self.empresa_otra,
            paciente=self.paciente_otra,
            fecha_cita=date.today(),
            hora_cita=time(11, 0),
            motivo='Otra consulta',
            estado='EN_SALA',
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('enfermeria:lista_pacientes_triage'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pacientes'].count(), 1)
        self.assertEqual(response.context['pacientes'].first().paciente, self.paciente)

    def test_capturar_signos_vitales_crea_registro(self):
        self.client.force_login(self.user)
        url = reverse('enfermeria:capturar_signos_vitales', args=[self.cita.id])
        data = {
            'peso': 70.0,
            'talla': 1.75,
            'presion_arterial_sistolica': 120,
            'presion_arterial_diastolica': 80,
            'temperatura': 36.5,
            'frecuencia_cardiaca': 75,
            'frecuencia_respiratoria': 18,
            'saturacion_oxigeno': 98,
            'glucosa_capilar': 95.0,
            'perimetro_abdominal': 85.0,
            'observaciones': 'Sin observaciones',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SignosVitales.objects.count(), 1)
        signos = SignosVitales.objects.first()
        self.assertEqual(signos.paciente, self.paciente)
        self.assertEqual(signos.empresa, self.empresa)
        self.assertEqual(signos.cita, self.cita)
        self.assertEqual(signos.registrado_por, self.user)

        # La cita debe pasar a EN_CURSO
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, 'EN_CURSO')

    def test_capturar_signos_vitales_cita_otra_empresa_devuelve_404(self):
        self.client.force_login(self.user)
        cita_otra = CitaMedica.objects.create(
            empresa=self.empresa_otra,
            paciente=self.paciente_otra,
            fecha_cita=date.today(),
            hora_cita=time(12, 0),
            motivo='Consulta externa',
            estado='EN_SALA',
        )
        url = reverse('enfermeria:capturar_signos_vitales', args=[cita_otra.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_historial_signos_filtra_por_empresa(self):
        self.client.force_login(self.user)
        SignosVitales.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            presion_arterial_sistolica=120,
            frecuencia_cardiaca=75,
        )
        SignosVitales.objects.create(
            empresa=self.empresa_otra,
            paciente=self.paciente_otra,
            presion_arterial_sistolica=130,
            frecuencia_cardiaca=80,
        )
        url = reverse('enfermeria:historial_signos_paciente', args=[self.paciente.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['signos'].count(), 1)
        self.assertEqual(response.context['signos'].first().paciente, self.paciente)

    def test_historial_paciente_otra_empresa_devuelve_404(self):
        self.client.force_login(self.user)
        url = reverse('enfermeria:historial_signos_paciente', args=[self.paciente_otra.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_graficas_tendencias_genera_json(self):
        self.client.force_login(self.user)
        SignosVitales.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            presion_arterial_sistolica=120,
            presion_arterial_diastolica=80,
            temperatura=36.5,
        )
        url = reverse('enfermeria:graficas_tendencias', args=[self.paciente.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('datos_presion', response.context)
        self.assertIn('datos_temperatura', response.context)

    def test_alertas_criticas_detectan_signos_anormales(self):
        self.client.force_login(self.user)
        SignosVitales.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            presion_arterial_sistolica=150,
            temperatura=38.5,
            frecuencia_cardiaca=110,
        )
        response = self.client.get(reverse('enfermeria:alertas_signos_criticos'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['alertas'].count(), 1)

    def test_alertas_criticas_no_muestran_otra_empresa(self):
        self.client.force_login(self.user)
        SignosVitales.objects.create(
            empresa=self.empresa_otra,
            paciente=self.paciente_otra,
            presion_arterial_sistolica=180,
            temperatura=39.0,
        )
        response = self.client.get(reverse('enfermeria:alertas_signos_criticos'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['alertas'].count(), 0)


class EnfermeriaFormTest(TestCase):
    """Pruebas de validación del formulario de signos vitales."""

    def test_peso_fuera_de_rango_invalido(self):
        from enfermeria.forms import SignosVitalesForm
        form = SignosVitalesForm(data={'peso': 400})
        self.assertFalse(form.is_valid())
        self.assertIn('peso', form.errors)

    def test_temperatura_fuera_de_rango_invalida(self):
        from enfermeria.forms import SignosVitalesForm
        form = SignosVitalesForm(data={'temperatura': 50})
        self.assertFalse(form.is_valid())
        self.assertIn('temperatura', form.errors)

    def test_presion_sistolica_alta_marcada_como_inusual(self):
        from enfermeria.forms import SignosVitalesForm
        form = SignosVitalesForm(data={'presion_arterial_sistolica': 260})
        self.assertFalse(form.is_valid())
        self.assertIn('presion_arterial_sistolica', form.errors)

    def test_signos_normales_validos(self):
        from enfermeria.forms import SignosVitalesForm
        form = SignosVitalesForm(data={
            'peso': 70.0,
            'talla': 1.75,
            'temperatura': 36.5,
            'presion_arterial_sistolica': 120,
            'presion_arterial_diastolica': 80,
            'frecuencia_cardiaca': 75,
            'frecuencia_respiratoria': 18,
            'saturacion_oxigeno': 98,
        })
        self.assertTrue(form.is_valid())
