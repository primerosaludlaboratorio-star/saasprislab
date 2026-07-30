import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection

from core.models import Empresa, Lote, Producto, Sucursal


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

    def test_entrada_reconoce_variante_y_producto_de_otra_sucursal_del_tenant(self):
        otra_sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre='Sucursal Catalogo',
            codigo_sucursal='SUC-PRE-002',
        )
        producto = Producto.objects.create(
            empresa=self.empresa,
            sucursal=otra_sucursal,
            nombre='KETOROLACO 30MG TABLETA SUBLINGUAL (4)',
            codigo_barras='785120754759',
            forma_farmaceutica='Tableta sublingual',
            concentracion='30 mg',
            presentacion='4 tabletas',
            precio_compra=Decimal('11.49'),
            precio_publico=Decimal('75.00'),
            stock=0,
        )
        Lote.objects.create(
            empresa=self.empresa,
            producto=producto,
            numero_lote='KET-TEST-01',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad=0,
            costo_adquisicion=Decimal('11.49'),
        )

        busqueda = self.client.get(
            '/farmacia/api/buscar-productos-compra/',
            {'q': 'esketorolaco sublingual 4 tabletas'},
        )
        self.assertEqual(busqueda.status_code, 200)
        self.assertEqual(busqueda.json()['productos'][0]['id'], producto.id)

        entrada = self.client.post(
            '/farmacia/almacen/entradas/',
            data=json.dumps({
                'producto_id': producto.id,
                'codigo': producto.codigo_barras,
                'nombre': producto.nombre,
                'lote': 'KET-TEST-01',
                'caducidad': (date.today() + timedelta(days=365)).isoformat(),
                'cantidad': 4,
                'costo_unitario': '11.49',
                'precio_venta': '75.00',
            }),
            content_type='application/json',
        )
        self.assertEqual(entrada.status_code, 200)
        self.assertEqual(entrada.json()['status'], 'success')

        lotes = self.client.get(f'/farmacia/api/lotes-producto/{producto.id}/?modo=entrada')
        self.assertEqual(lotes.status_code, 200)

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

    def test_entrada_existente_conserva_producto_para_capturar_multiples_lotes(self):
        response = self.client.get('/farmacia/almacen/entradas/')
        contenido = response.content.decode('utf-8')

        self.assertEqual(response.status_code, 200)
        self.assertIn('function prepararSiguienteLote(res)', contenido)
        self.assertIn('GUARDAR LOTE Y CONTINUAR', contenido)
        self.assertNotIn('location.reload()', contenido)

    def test_busqueda_pdv_no_hace_consulta_por_cada_producto(self):
        with CaptureQueriesContext(connection) as consultas:
            response = self.client.get('/farmacia/api/buscar-producto-pdv/?termino=Paracetamol')

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(consultas), 12)

    def test_productos_sin_codigo_pueden_coexistir_y_aparecen_por_separado(self):
        for lote in ('VAL-01', 'VAL-02'):
            response = self.client.post(
                '/farmacia/almacen/entradas/',
                data=json.dumps({
                    'nombre': 'Valaciclovir 500 mg',
                    'codigo': '',
                    'lote': lote,
                    'caducidad': (date.today() + timedelta(days=365)).isoformat(),
                    'cantidad': 2,
                    'costo_unitario': '10.00',
                    'precio_venta': '20.00',
                }),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['status'], 'success')

        productos = Producto.objects.filter(
            empresa=self.empresa,
            nombre='Valaciclovir 500 mg',
        )
        self.assertEqual(productos.count(), 2)
        self.assertEqual(productos.filter(codigo_barras__isnull=True).count(), 2)

        response = self.client.get(
            '/farmacia/api/buscar-productos-compra/',
            {'q': 'Valaciclovir 500 mg'},
        )
        self.assertEqual(response.status_code, 200)
        encontrados = [
            item for item in response.json()['productos']
            if item['nombre'] == 'Valaciclovir 500 mg'
        ]
        self.assertEqual(len(encontrados), 2)
        self.assertEqual({item['codigo_barras'] for item in encontrados}, {None})
        self.assertEqual(len({item['id'] for item in encontrados}), 2)

    def test_codigo_se_puede_limpiar_y_reasignar_con_auditoria_de_conflicto(self):
        ampicilina = Producto.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            nombre='Ampicilina 500 mg',
            codigo_barras='BAR-AMP-001',
            precio_compra=Decimal('10.00'),
            precio_publico=Decimal('20.00'),
        )
        valaciclovir = Producto.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            nombre='Valaciclovir 500 mg',
            codigo_barras='BAR-VAL-001',
            precio_compra=Decimal('10.00'),
            precio_publico=Decimal('20.00'),
        )

        limpiar = self.client.post(
            '/farmacia/almacen/entradas/',
            data=json.dumps({
                'producto_id': ampicilina.id,
                'codigo': '',
                'nombre': ampicilina.nombre,
                'lote': 'AMP-EDIT-01',
                'caducidad': (date.today() + timedelta(days=365)).isoformat(),
                'cantidad': 1,
                'costo_unitario': '10.00',
                'precio_venta': '20.00',
            }),
            content_type='application/json',
        )
        self.assertEqual(limpiar.status_code, 200)
        ampicilina.refresh_from_db()
        self.assertIsNone(ampicilina.codigo_barras)

        reasignar = self.client.post(
            '/farmacia/almacen/entradas/',
            data=json.dumps({
                'producto_id': ampicilina.id,
                'codigo': 'BAR-AMP-001',
                'nombre': ampicilina.nombre,
                'lote': 'AMP-EDIT-02',
                'caducidad': (date.today() + timedelta(days=365)).isoformat(),
                'cantidad': 1,
                'costo_unitario': '10.00',
                'precio_venta': '20.00',
            }),
            content_type='application/json',
        )
        self.assertEqual(reasignar.status_code, 200)
        ampicilina.refresh_from_db()
        self.assertEqual(ampicilina.codigo_barras, 'BAR-AMP-001')

        conflicto = self.client.post(
            '/farmacia/almacen/entradas/',
            data=json.dumps({
                'producto_id': valaciclovir.id,
                'codigo': 'BAR-AMP-001',
                'nombre': valaciclovir.nombre,
                'lote': 'VAL-EDIT-01',
                'caducidad': (date.today() + timedelta(days=365)).isoformat(),
                'cantidad': 1,
                'costo_unitario': '10.00',
                'precio_venta': '20.00',
            }),
            content_type='application/json',
        )
        self.assertEqual(conflicto.status_code, 409)
        valaciclovir.refresh_from_db()
        self.assertEqual(valaciclovir.codigo_barras, 'BAR-VAL-001')

    def test_lector_no_asigna_automaticamente_el_primer_resultado(self):
        response = self.client.get('/farmacia/almacen/entradas/')
        contenido = response.content.decode('utf-8')

        self.assertEqual(response.status_code, 200)
        self.assertIn("const producto = productos.find(function(p) { return String(p.codigo_barras || '').trim() === codigo; });", contenido)
        self.assertNotIn("}) || productos[0]", contenido)
