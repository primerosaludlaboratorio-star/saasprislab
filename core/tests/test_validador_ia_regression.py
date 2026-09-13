from datetime import timedelta

from django.test import TestCase
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from core.models import Empresa, Sucursal, Paciente, Usuario, OrdenDeServicio, DetalleOrden, Producto
from core.services.validador_ia import generar_sugerencias_proceso
from core.services.prediccion_stock import predecir_agotamiento_critico


class ValidadorIAProcesoRegressionTests(TestCase):
    def test_sugerencias_usa_fecha_validacion_de_detalle(self):
        empresa = Empresa.objects.create(nombre="Empresa Validador", rfc="VAL010101AAA")
        sucursal = Sucursal.objects.create(
            empresa=empresa,
            nombre="Sucursal Validador",
            codigo_sucursal="VAL-001",
        )
        usuario = Usuario.objects.create_user(
            username="validador-regresion",
            password="test-password",
            empresa=empresa,
        )
        paciente = Paciente.objects.create(
            empresa=empresa,
            sucursal=sucursal,
            nombre_completo="Paciente Validador",
        )
        orden = OrdenDeServicio.objects.create(
            empresa=empresa,
            sucursal=sucursal,
            paciente=paciente,
            responsable_ingreso=usuario,
            total=100,
            hora_toma_muestra=timezone.now(),
        )
        detalle = DetalleOrden.objects.create(
            orden=orden,
            precio_momento=100,
            fecha_validacion=timezone.now() + timedelta(hours=5),
        )

        sugerencias = generar_sugerencias_proceso(empresa)

        self.assertTrue(any(item["severidad"] == "ALTA" for item in sugerencias))
        self.assertIsNotNone(detalle.pk)

    def test_prediccion_agrega_consumos_sin_n_plus_one(self):
        empresa = Empresa.objects.create(nombre="Empresa Stock", rfc="STK010101AAA")
        for index in range(3):
            Producto.objects.create(
                empresa=empresa,
                nombre=f"Producto Stock {index}",
                forma_farmaceutica="Pieza",
                concentracion="1",
                presentacion="1 pieza",
                stock=10,
            )

        with CaptureQueriesContext(connection) as queries:
            resultado = predecir_agotamiento_critico(empresa)

        self.assertEqual(resultado, [])
        self.assertLessEqual(len(queries), 5)
