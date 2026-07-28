"""Contratos de error controlado para el flujo regulatorio de Farmacia."""

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client, TestCase

from core.models import Empresa, Producto, Sucursal
from core.services.ventas.catalogo_service import CatalogoService


class FarmaciaRegulatorioContractTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Regulatorio",
            rfc="REG123456789",
        )
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre="Sucursal Regulatorio",
            codigo_sucursal="SUC-REG-001",
        )
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="regulatorio_test",
            password="regulatorio_test_123",
            empresa=self.empresa,
            sucursal=self.sucursal,
            rol="ADMIN",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            nombre="Amoxicilina Regulatorio",
            codigo_barras="REG-AMOX-001",
            precio_compra=Decimal("10.00"),
            precio_publico=Decimal("20.00"),
            stock=10,
            es_antibiotico=True,
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_producto_faltante_no_se_convierte_en_500(self):
        response = self.client.post(
            "/farmacia/erp/antibioticos/validar/",
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["success"], False)

    def test_producto_inexistente_devuelve_404_controlado(self):
        response = self.client.post(
            "/farmacia/erp/antibioticos/validar/",
            data=json.dumps({"producto_id": 999999999}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["success"], False)

    def test_material_de_curacion_no_hereda_restriccion_de_receta(self):
        material = Producto.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            nombre='Jeringa de prueba',
            codigo_barras='REG-JERINGA-001',
            categoria='CURACION',
            clasificacion_sanitaria='VI',
            precio_compra=Decimal('1.00'),
            precio_publico=Decimal('2.00'),
            stock=3,
            # Simula una importación histórica incorrecta: la categoría manda.
            es_antibiotico=True,
            requiere_receta=True,
        )
        self.assertFalse(material.necesita_receta())
        response = self.client.post(
            reverse('farmacia:validar_antibiotico'),
            data=json.dumps({'producto_id': material.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['requiere_validacion'])

    def test_busqueda_pdV_serializa_material_de_curacion_como_libre(self):
        material = Producto.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            nombre='Jeringa búsqueda',
            codigo_barras='REG-JERINGA-002',
            categoria='CURACION',
            clasificacion_sanitaria='VI',
            precio_compra=Decimal('1.00'),
            precio_publico=Decimal('2.00'),
            stock=3,
            es_antibiotico=True,
            requiere_receta=True,
        )
        resultado = next(
            item for item in CatalogoService.buscar_productos_pdv(self.empresa, 'Jeringa búsqueda')
            if item['id'] == material.id
        )
        self.assertFalse(resultado['es_antibiotico'])
        self.assertFalse(resultado['es_controlado'])
        self.assertFalse(resultado['requiere_receta'])

    def test_material_de_curacion_no_se_bloquea_por_receta_de_otro_producto(self):
        """Una jeringa puede acompañar una receta sin heredar su cantidad limitada."""
        material = Producto.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            nombre='Jeringa libre de receta',
            codigo_barras='REG-JERINGA-003',
            categoria='CURACION',
            requiere_receta=True,
            es_antibiotico=True,
        )
        self.assertFalse(material.requiere_receta_farmacia())

    def test_conciliacion_ocr_prioriza_equivalencia_y_tolerancia_de_lectura(self):
        from farmacia.services.receta_ocr import conciliar_medicamentos

        producto = Producto.objects.create(
            empresa=self.empresa,
            nombre='Panclasa',
            sustancia_activa='Trimetilfloroglucinol',
            equivalencias_comerciales='Panclasa gotas, trimetil floroglucinol',
            codigo_barras='REG-OCR-001',
        )
        sugerencias = conciliar_medicamentos(self.empresa, {
            'medicamentos': [{'texto': 'Panclasa gotas'}],
        })
        self.assertEqual(sugerencias[0]['candidatos'][0]['producto_id'], producto.id)

    def test_antibiotico_sin_datos_medico_exige_cedula_y_nombre(self):
        response = self.client.post(
            "/farmacia/erp/antibioticos/validar/",
            data=json.dumps({"producto_id": self.producto.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()["requiere_validacion"])

    def test_entrada_con_codigo_globalmente_existente_no_devuelve_500(self):
        otra_empresa = Empresa.objects.create(
            nombre="Otra Empresa",
            rfc="OTR123456789",
        )
        Producto.objects.create(
            empresa=otra_empresa,
            nombre="Producto con codigo reservado",
            codigo_barras="CODIGO-RESERVADO-001",
            precio_compra=Decimal("10.00"),
            precio_publico=Decimal("20.00"),
        )

        response = self.client.post(
            "/farmacia/almacen/entradas/",
            data=json.dumps({
                "codigo": "CODIGO-RESERVADO-001",
                "nombre": "Producto nuevo",
                "cantidad": 1,
                "costo_unitario": "10.00",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["status"], "error")
