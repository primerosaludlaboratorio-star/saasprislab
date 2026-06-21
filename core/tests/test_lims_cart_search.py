from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from core.lims_cart import search_lims_catalog
from core.models import Empresa, OrdenDeServicio, Paciente
from core.views.laboratorio import api_ordenes_recientes
from lims.models import Analito, PerfilLims


Usuario = get_user_model()


class LimsCartSearchTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa LIMS', rfc='LIM260620TST')

        self.usuario = Usuario.objects.create_user(
            username='lims_search_user',
            password='Test123456!',
            empresa=self.empresa,
            rol='ADMIN',
        )

        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente LIMS',
            nombres='Paciente',
            apellido_paterno='LIMS',
            sexo='M',
        )

        self.analito_glucosa = Analito.objects.create(
            empresa=self.empresa,
            codigo='GLU',
            abreviatura='GLU',
            nombre='GLUCOSA',
            departamento='BIOQUIMICA',
            tipo_muestra='SUERO',
            es_vendible_individualmente=True,
            costo_lista=Decimal('85.00'),
        )
        self.perfil_qs6 = PerfilLims.objects.create(
            empresa=self.empresa,
            nombre='QUIMICA SANGUINEA 6',
            descripcion='Perfil rutinario QS6',
            costo_lista=Decimal('350.00'),
        )
        self.perfil_bh = PerfilLims.objects.create(
            empresa=self.empresa,
            nombre='CITOMETRIA HEMATICA COMPLETA',
            descripcion='Biometria hematica completa',
            costo_lista=Decimal('170.00'),
        )

    def test_search_lims_catalog_alias_qs6_encuentra_perfil_operativo(self):
        resultados = search_lims_catalog('QS6', empresa=self.empresa)

        self.assertTrue(
            any(item['id'] == f'perfil:{self.perfil_qs6.id}' for item in resultados),
            resultados,
        )

    def test_search_lims_catalog_alias_bh_prioriza_citometria_hematica(self):
        resultados = search_lims_catalog('BH', empresa=self.empresa)

        self.assertTrue(resultados, 'La búsqueda BH no devolvió resultados')
        self.assertEqual(resultados[0]['id'], f'perfil:{self.perfil_bh.id}')

    def test_api_ordenes_recientes_incluye_estado_icono_para_bitacora(self):
        OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('85.00'),
            anticipo=Decimal('0.00'),
            estado='PENDIENTE_PAGO',
            estado_pago='PENDIENTE',
            responsable_ingreso=self.usuario,
            folio_orden='LAB-TEST-001',
        )

        factory = RequestFactory()
        request = factory.get('/laboratorio/api/ordenes-recientes/')
        request.user = self.usuario

        response = api_ordenes_recientes(request)
        payload = response.json()

        self.assertEqual(payload['status'], 'success')
        self.assertTrue(payload['ordenes'])
        self.assertIn('estado_icono', payload['ordenes'][0])
