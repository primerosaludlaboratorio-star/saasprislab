"""Enfoque 2 — LIMS ↔ inventario: validación descuenta lote FEFO (backend verificable)."""
import json
import shutil
import tempfile
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.test import Client, TestCase

from core.models import DetalleOrden, Empresa, OrdenDeServicio, Paciente
from inventario.models import CatalogoReactivoLab, ConsumoEstudioReactivo, LoteReactivoLab
from lims.models import Analito, ValorReferenciaAnalito

User = get_user_model()


class LimsInventorySyncTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_tmp = tempfile.mkdtemp()
        cls._pdf_field = OrdenDeServicio._meta.get_field('archivo_resultado')
        cls._orig_pdf_storage = cls._pdf_field.storage
        cls._pdf_field.storage = FileSystemStorage(location=cls._media_tmp)

    @classmethod
    def tearDownClass(cls):
        cls._pdf_field.storage = cls._orig_pdf_storage
        shutil.rmtree(cls._media_tmp, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Emp LIMS Inv', rfc='LIM123456AAA')
        self.user = User.objects.create_user(
            username='inv_sync_user',
            password='inv-pass-88',
            empresa=self.empresa,
            rol='QUIMICO',
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Pac Inv',
            nombres='P',
            apellido_paterno='Inv',
            fecha_nacimiento=date(1991, 3, 3),
            sexo='F',
        )
        self.analito = Analito.objects.create(
            empresa=self.empresa,
            codigo='INV-NA',
            abreviatura='INVNA',
            nombre='Sodio Inv',
            departamento='Química',
            tipo_resultado='NUMERICO',
            unidades='mEq/L',
            es_calculado=False,
        )
        ValorReferenciaAnalito.objects.create(
            analito=self.analito,
            sexo='F',
            unidad_edad='ANOS',
            edad_minima=0,
            edad_maxima=120,
            ref_minimo=135,
            ref_maximo=145,
        )
        self.reactivo = CatalogoReactivoLab.objects.create(
            empresa=self.empresa,
            codigo_interno='R-INV',
            nombre='Reactivo sync',
        )
        ConsumoEstudioReactivo.objects.create(
            empresa=self.empresa,
            analito=self.analito,
            reactivo=self.reactivo,
            cantidad_por_prueba=Decimal('3.0000'),
            unidad='UL',
            activo=True,
        )
        self.lote = LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=self.reactivo,
            numero_lote='L-SYNC-01',
            fecha_caducidad=date(2032, 1, 1),
            cantidad_inicial=Decimal('200'),
            cantidad_actual=Decimal('200'),
            estado='ACTIVO',
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('80.00'),
            anticipo=Decimal('80.00'),
            estado='EN_PROCESO',
            estado_pago='PAGADO',
            responsable_ingreso=self.user,
        )
        self.detalle = DetalleOrden.objects.create(
            orden=self.orden,
            analito=self.analito,
            precio_momento=Decimal('80.00'),
        )
        self.client = Client()
        self.assertTrue(self.client.login(username='inv_sync_user', password='inv-pass-88'))

    def test_validar_descontar_lote_coherente_con_consumo(self):
        url = f'/laboratorio/api/guardar-resultados/{self.orden.id}/'
        payload = {
            'accion': 'validar',
            'resultados': {
                str(self.detalle.id): {
                    'resultado': '',
                    'observaciones': '',
                    'parametros': {str(self.analito.id): {'valor': '140'}},
                }
            },
        }
        r = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200, r.content[:800])
        self.assertEqual(r.json().get('status'), 'success')
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, Decimal('197'))
