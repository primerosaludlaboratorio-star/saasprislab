from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection

from core.models import Empresa
from lims.models import Analito, PerfilAnalito, PerfilLims, PrecioItem


User = get_user_model()


class LimsPreciosPerformanceTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa Precios LIMS', rfc='LIM260723PER')
        self.user = User.objects.create_user(
            username='lims_precios_perf',
            password='lims_precios_perf_123',
            empresa=self.empresa,
            rol='ADMIN',
            is_staff=True,
        )
        self.client = Client()
        self.client.force_login(self.user)
        for index in range(12):
            perfil = PerfilLims.objects.create(
                empresa=self.empresa,
                nombre=f'Perfil rendimiento {index}',
                costo_lista=10,
            )
            analito = Analito.objects.create(
                empresa=self.empresa,
                codigo=f'PERF-{index}',
                abreviatura=f'P{index}',
                nombre=f'Analito rendimiento {index}',
                departamento='QUIMICA',
            )
            PerfilAnalito.objects.create(
                empresa=self.empresa,
                perfil=perfil,
                analito=analito,
            )
            PrecioItem.objects.create(
                empresa=self.empresa,
                tipo='P',
                perfil=perfil,
                precio_venta=10,
            )

    def test_lista_precios_no_consulta_por_cada_perfil(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/lims/precios/', HTTP_HOST='testserver')

        self.assertEqual(response.status_code, 200)
        # El limite admite autenticacion, middleware y render, pero evita una
        # consulta adicional por cada perfil listado.
        self.assertLessEqual(len(queries), 30, queries)
