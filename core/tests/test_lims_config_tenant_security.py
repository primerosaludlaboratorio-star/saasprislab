from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from types import SimpleNamespace

from core.models import Empresa
from lims.models import Analito, ValorReferenciaAnalito
from lims.views.tenant_lims import empresa_lims


Usuario = get_user_model()


class LimsConfigTenantSecurityTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='PRISLAB Test', rfc='LIM260621TST')
        self.otra_empresa = Empresa.objects.create(nombre='Otro Lab Test', rfc='LIM260621OTR')
        self.usuario = Usuario.objects.create_user(
            username='lims_staff_tenant',
            password='Test2026!LIMS',
            empresa=self.empresa,
            is_staff=True,
            is_superuser=True,
        )
        self.client.login(username='lims_staff_tenant', password='Test2026!LIMS')

        self.analito_propio = self._analito(self.empresa, 'GLU-T1', 'Glucosa Tenant 1')
        self.analito_ajeno = self._analito(self.otra_empresa, 'GLU-T2', 'Glucosa Tenant 2')
        ValorReferenciaAnalito.objects.create(
            analito=self.analito_propio,
            sexo='I',
            unidad_edad='ANOS',
            edad_minima=0,
            edad_maxima=120,
            ref_minimo='70',
            ref_maximo='100',
        )

    def _analito(self, empresa, codigo, nombre):
        return Analito.objects.create(
            empresa=empresa,
            codigo=codigo,
            abreviatura=codigo,
            nombre=nombre,
            departamento='QUIMICA',
            activo=True,
        )

    def test_parametros_estudio_no_expone_analito_de_otro_tenant(self):
        response = self.client.get(reverse('api_parametros_estudio', args=[self.analito_propio.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['estudio']['id'], self.analito_propio.id)

        response = self.client.get(reverse('api_parametros_estudio', args=[self.analito_ajeno.id]))
        self.assertEqual(response.status_code, 404)

    def test_buscar_parametros_solo_devuelve_empresa_del_usuario(self):
        response = self.client.get(reverse('api_buscar_parametros'), {'q': 'Glucosa'})

        self.assertEqual(response.status_code, 200)
        ids = {item['id'] for item in response.json()['parametros']}
        self.assertIn(self.analito_propio.id, ids)
        self.assertNotIn(self.analito_ajeno.id, ids)

    def test_rangos_parametro_no_expone_analito_de_otro_tenant(self):
        response = self.client.get(reverse('api_rangos_parametro', args=[self.analito_propio.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['rangos']), 1)

        response = self.client.get(reverse('api_rangos_parametro', args=[self.analito_ajeno.id]))
        self.assertEqual(response.status_code, 404)

    def test_staff_sin_empresa_no_puede_usar_config_lims(self):
        Usuario.objects.create_user(
            username='staff_sin_empresa',
            password='Test2026!LIMS',
            is_staff=True,
            is_superuser=True,
        )
        self.client.login(username='staff_sin_empresa', password='Test2026!LIMS')

        response = self.client.get(reverse('api_buscar_parametros'), {'q': 'Glucosa'})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['parametros'], [])

    def test_empresa_lims_ignora_empresa_de_respaldo_del_request(self):
        request = SimpleNamespace(
            user=SimpleNamespace(
                is_authenticated=True,
                empresa=None,
            ),
            empresa_actual=self.empresa,
        )

        self.assertIsNone(empresa_lims(request))
