"""v1.49: con gestion_inventario_activa=False en Sucursal no hay descuento FEFO al validar."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from core.models import Empresa, OrdenDeServicio, Paciente, ResultadoParametro, Sucursal
from inventario.models import (
    CatalogoReactivoLab,
    ConsumoEstudioReactivo,
    LoteReactivoLab,
    SalidaAnaliticaLab,
)
from lims.models import Analito

User = get_user_model()


class GestionInventarioBypassLabTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Emp Bypass Inv', rfc='BYP123456AAA')
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre='Suc Principal',
            codigo_sucursal='SUC-BYP-01',
            gestion_inventario_activa=False,
        )
        self.user = User.objects.create_user(
            username='bypass_inv_user',
            password='secret123',
            empresa=self.empresa,
            rol='ADMIN',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Pac Bypass',
            nombres='P',
            apellido_paterno='B',
            fecha_nacimiento=date(1990, 1, 1),
            sexo='M',
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            paciente=self.paciente,
            total=Decimal('50.00'),
            anticipo=Decimal('0'),
            estado='EN_PROCESO',
            estado_pago='PAGADO',
            responsable_ingreso=self.user,
        )
        self.analito = Analito.objects.create(
            empresa=self.empresa,
            codigo='BYP-GLU',
            abreviatura='BGLU',
            nombre='Glucosa bypass',
            departamento='Química',
            es_calculado=False,
        )
        self.reactivo = CatalogoReactivoLab.objects.create(
            empresa=self.empresa,
            codigo_interno='R-BYP',
            nombre='Reactivo bypass',
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
            numero_lote='L-BYP',
            fecha_caducidad=date(2030, 6, 1),
            cantidad_inicial=Decimal('200'),
            cantidad_actual=Decimal('200'),
            estado='ACTIVO',
        )

    def test_sin_gestion_inventario_no_crea_salida_ni_baja_stock(self):
        ResultadoParametro.objects.create(
            orden=self.orden,
            analito=self.analito,
            valor='90',
            capturado_por=self.user,
            validado=True,
            validado_por=self.user,
            aprobado_por_humano=True,
        )
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, Decimal('200'))
        self.assertFalse(
            SalidaAnaliticaLab.objects.filter(orden=self.orden, analito=self.analito).exists()
        )
