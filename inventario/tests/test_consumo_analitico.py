from datetime import date
from decimal import Decimal

from django.test import TestCase

from core.models import Empresa, OrdenDeServicio, Paciente, ResultadoParametro, Usuario
from inventario.models import (
    CatalogoReactivoLab,
    ConsumoEstudioReactivo,
    LoteReactivoLab,
    RepeticionAnaliticaLab,
    SalidaAnaliticaLab,
)
from laboratorio.models import Equipo
from lims.models import Analito


class ConsumoAnaliticoPersistenteTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa consumo analitico")
        self.usuario = Usuario.objects.create_user(
            username="qfb_consumo",
            password="test123456789",
            empresa=self.empresa,
            rol="ADMIN",
        )
        paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo="Paciente consumo",
            nombres="Paciente",
            apellido_paterno="Consumo",
            fecha_nacimiento=date(1990, 1, 1),
            sexo="M",
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=paciente,
            total=Decimal("100"),
            estado="EN_PROCESO",
            estado_pago="PAGADO",
            responsable_ingreso=self.usuario,
        )
        self.analito = Analito.objects.create(
            empresa=self.empresa,
            codigo="HBA1C-QA",
            abreviatura="HBA1C",
            nombre="Hemoglobina glucosilada QA",
            departamento="Quimica",
            es_calculado=False,
        )
        self.equipo = Equipo.objects.create(nombre="Analizador HbA1c QA", marca="Wondfo")

    def _reactivo(self, codigo, nombre):
        return CatalogoReactivoLab.objects.create(
            empresa=self.empresa,
            codigo_interno=codigo,
            nombre=nombre,
            tipo="REACTIVO",
            unidad_medida="UNIDAD",
        )

    def _lote(self, reactivo, numero, cantidad):
        return LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=reactivo,
            numero_lote=numero,
            fecha_caducidad=date(2030, 1, 1),
            cantidad_inicial=Decimal(cantidad),
            cantidad_actual=Decimal(cantidad),
            estado="ACTIVO",
        )

    def test_descuenta_una_unidad_de_caja_de_24_y_es_idempotente(self):
        reactivo = self._reactivo("HBA1C-W-01", "Kit HbA1c Wondfo")
        lote = self._lote(reactivo, "W-24", "24")
        ConsumoEstudioReactivo.objects.create(
            empresa=self.empresa,
            analito=self.analito,
            reactivo=reactivo,
            equipo=self.equipo,
            grupo_consumo="REACTIVO_PRINCIPAL",
            cantidad_por_prueba=Decimal("1"),
            unidad="UNIDAD",
        )

        resultado = ResultadoParametro.objects.create(
            orden=self.orden,
            analito=self.analito,
            equipo=self.equipo,
            valor="6.1",
            capturado_por=self.usuario,
            validado=True,
            validado_por=self.usuario,
            aprobado_por_humano=True,
        )
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, Decimal("23"))
        self.assertEqual(
            SalidaAnaliticaLab.objects.filter(orden=self.orden, analito=self.analito).count(),
            1,
        )

        resultado.save()
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, Decimal("23"))

    def test_solo_alternativa_seleccionada_descuenta_y_cambio_persiste(self):
        wondfo = self._reactivo("HBA1C-W-02", "HbA1c Wondfo alternativo")
        otro = self._reactivo("HBA1C-O-02", "HbA1c otra marca")
        lote_w = self._lote(wondfo, "W-A", "10")
        lote_o = self._lote(otro, "O-A", "10")
        formula_w = ConsumoEstudioReactivo.objects.create(
            empresa=self.empresa,
            analito=self.analito,
            reactivo=wondfo,
            equipo=self.equipo,
            grupo_consumo="REACTIVO_PRINCIPAL",
            es_alternativa=True,
            seleccionada=True,
            cantidad_por_prueba=Decimal("1"),
            unidad="UNIDAD",
        )
        formula_o = ConsumoEstudioReactivo.objects.create(
            empresa=self.empresa,
            analito=self.analito,
            reactivo=otro,
            equipo=self.equipo,
            grupo_consumo="REACTIVO_PRINCIPAL",
            es_alternativa=True,
            seleccionada=False,
            cantidad_por_prueba=Decimal("1"),
            unidad="UNIDAD",
        )
        resultado = ResultadoParametro.objects.create(
            orden=self.orden,
            analito=self.analito,
            equipo=self.equipo,
            valor="6.2",
            capturado_por=self.usuario,
            validado=True,
            validado_por=self.usuario,
            aprobado_por_humano=True,
        )
        lote_w.refresh_from_db()
        lote_o.refresh_from_db()
        self.assertEqual(lote_w.cantidad_actual, Decimal("9"))
        self.assertEqual(lote_o.cantidad_actual, Decimal("10"))

        formula_w.seleccionada = False
        formula_w.save(update_fields=["seleccionada"])
        formula_o.seleccionada = True
        formula_o.save(update_fields=["seleccionada"])
        resultado2 = ResultadoParametro.objects.create(
            orden=OrdenDeServicio.objects.create(
                empresa=self.empresa,
                paciente=self.orden.paciente,
                total=Decimal("100"),
                estado="EN_PROCESO",
                estado_pago="PAGADO",
                responsable_ingreso=self.usuario,
            ),
            analito=self.analito,
            equipo=self.equipo,
            valor="6.3",
            capturado_por=self.usuario,
            validado=True,
            validado_por=self.usuario,
            aprobado_por_humano=True,
        )
        self.assertIsNotNone(resultado2.pk)
        lote_w.refresh_from_db()
        lote_o.refresh_from_db()
        self.assertEqual(lote_w.cantidad_actual, Decimal("9"))
        self.assertEqual(lote_o.cantidad_actual, Decimal("9"))

    def test_repeticion_descuenta_prueba_adicional_y_no_duplica(self):
        reactivo = self._reactivo("RF-01", "Factor reumatoide")
        lote = self._lote(reactivo, "RF-A", "10")
        ConsumoEstudioReactivo.objects.create(
            empresa=self.empresa,
            analito=self.analito,
            reactivo=reactivo,
            equipo=self.equipo,
            grupo_consumo="REACTIVO_PRINCIPAL",
            cantidad_por_prueba=Decimal("1"),
            unidad="UNIDAD",
        )
        resultado = ResultadoParametro.objects.create(
            orden=self.orden,
            analito=self.analito,
            equipo=self.equipo,
            valor="6.0",
            capturado_por=self.usuario,
            validado=True,
            validado_por=self.usuario,
            aprobado_por_humano=True,
        )
        repeticion = RepeticionAnaliticaLab.objects.create(
            resultado=resultado,
            cantidad_pruebas=1,
            motivo="Control de repetibilidad",
            registrada_por=self.usuario,
        )
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, Decimal("8"))
        self.assertEqual(
            SalidaAnaliticaLab.objects.filter(orden=self.orden, analito=self.analito).count(),
            2,
        )
        repeticion.save()
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, Decimal("8"))
