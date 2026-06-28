"""Enfoque 1 — Flujo de oro: borrador → validar → RESULTADOS_LISTOS (API captura)."""
import json
import os
import shutil
import uuid
from datetime import date
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.models import Group
from django.test import Client, TestCase

from core.models import DetalleOrden, Empresa, OrdenDeServicio, Paciente
from lims.models import Analito, ValorReferenciaAnalito

User = get_user_model()


class GuardianGoldenLifecycleTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base_tmp = os.path.join(str(settings.BASE_DIR), '.tmp', 'test-media')
        os.makedirs(base_tmp, exist_ok=True)
        cls._media_tmp = os.path.join(base_tmp, f'guardian-{uuid.uuid4().hex}')
        os.makedirs(cls._media_tmp, exist_ok=True)
        cls._pdf_field = OrdenDeServicio._meta.get_field('archivo_resultado')
        cls._orig_pdf_storage = cls._pdf_field.storage
        cls._pdf_field.storage = FileSystemStorage(location=cls._media_tmp)

    @classmethod
    def tearDownClass(cls):
        cls._pdf_field.storage = cls._orig_pdf_storage
        shutil.rmtree(cls._media_tmp, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Emp Golden Lab', rfc='GOL123456AAA')
        self.user = User.objects.create_user(
            username='golden_quimico',
            password='golden-pass-99',
            empresa=self.empresa,
            rol='QUIMICO',
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente Golden',
            nombres='Paciente',
            apellido_paterno='Golden',
            fecha_nacimiento=date(1993, 6, 15),
            sexo='M',
        )
        self.analito = Analito.objects.create(
            empresa=self.empresa,
            codigo='GOL-GLU',
            abreviatura='GGLU',
            nombre='Glucosa Golden',
            departamento='Química',
            tipo_resultado='NUMERICO',
            unidades='mg/dL',
            es_calculado=False,
        )
        ValorReferenciaAnalito.objects.create(
            analito=self.analito,
            sexo='M',
            unidad_edad='ANOS',
            edad_minima=0,
            edad_maxima=120,
            ref_minimo=70,
            ref_maximo=110,
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('150.00'),
            anticipo=Decimal('150.00'),
            estado='EN_PROCESO',
            estado_pago='PAGADO',
            responsable_ingreso=self.user,
        )
        self.detalle = DetalleOrden.objects.create(
            orden=self.orden,
            analito=self.analito,
            precio_momento=Decimal('150.00'),
        )
        self.client = Client()
        self.assertTrue(self.client.login(username='golden_quimico', password='golden-pass-99'))

    def _payload(self, accion: str) -> dict:
        return {
            'accion': accion,
            'resultados': {
                str(self.detalle.id): {
                    'resultado': '',
                    'observaciones': '',
                    'parametros': {str(self.analito.id): {'valor': '88'}},
                }
            },
        }

    def test_borrador_luego_validar_deja_orden_resultados_listos(self):
        url = f'/laboratorio/api/guardar-resultados/{self.orden.id}/'
        r1 = self.client.post(
            url,
            data=json.dumps(self._payload('borrador')),
            content_type='application/json',
        )
        self.assertEqual(r1.status_code, 200, r1.content[:800])
        self.assertEqual(r1.json().get('status'), 'success')
        r2 = self.client.post(
            url,
            data=json.dumps(self._payload('validar')),
            content_type='application/json',
        )
        self.assertEqual(r2.status_code, 200, r2.content[:800])
        body = r2.json()
        self.assertEqual(body.get('status'), 'success', body)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, 'RESULTADOS_LISTOS')
