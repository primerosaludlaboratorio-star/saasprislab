from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from core.models import Empresa, Producto, Sucursal


User = get_user_model()


class EntradaMercanciaPreciosTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa Precios', rfc='PRE123456789')
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre='Sucursal Precios',
            codigo_sucursal='SUC-PRE-001',
        )
        self.user = User.objects.create_user(
            username='entrada_precios',
            password='entrada_precios_123',
            empresa=self.empresa,
            sucursal=self.sucursal,
            rol='ADMIN',
            is_staff=True,
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            nombre='Paracetamol 500 mg',
            codigo_barras='7500000099999',
            precio_compra=Decimal('23.50'),
            precio_publico=Decimal('41.90'),
            stock=10,
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_busqueda_para_entrada_expone_costo_y_precio_vigentes(self):
        response = self.client.get('/farmacia/api/buscar-productos-compra/?q=Paracetamol')

        self.assertEqual(response.status_code, 200)
        producto = response.json()['productos'][0]
        self.assertEqual(producto['precio_compra'], 23.5)
        self.assertEqual(producto['precio_publico'], 41.9)

    def test_formulario_precarga_ambos_precios_al_seleccionar_existente(self):
        response = self.client.get('/farmacia/almacen/entradas/')
        contenido = response.content.decode('utf-8')

        self.assertEqual(response.status_code, 200)
        self.assertIn("producto.precio_publico", contenido)
        self.assertIn("ent-venta-memoria", contenido)

    def test_marca_es_campo_de_texto_editable_con_sugerencias(self):
        response = self.client.get('/farmacia/almacen/entradas/')
        contenido = response.content.decode('utf-8')

        self.assertIn('id="ent-marca" class="form-control"', contenido)
        self.assertIn('list="marcas-farmacia"', contenido)
        self.assertIn('Maver', contenido)
        self.assertIn('Campo editable', contenido)
