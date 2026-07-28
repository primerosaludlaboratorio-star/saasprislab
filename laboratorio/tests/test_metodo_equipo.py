from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from core.models import Empresa
from lims.models import Analito
from laboratorio.models import Equipo, InterfazEquipo, MetodoEquipo
from core.services.lims.interfaces_lims_service import _resolver_equipo_por_ip


class MetodoEquipoFuenteTests(SimpleTestCase):
    def test_fuente_incca_se_simula_sin_escritura_y_mantiene_validacion_operativa(self):
        output = StringIO()
        call_command('cargar_metodos_incca', stdout=output)
        text = output.getvalue()
        self.assertIn('16 método(s) fuente', text)
        self.assertIn('16 mapeo(s) confirmado(s)', text)
        self.assertIn('No se modificó la base de datos', text)


class MetodoEquipoTenantTests(TestCase):
    def test_metodo_queda_aislado_por_empresa_y_inactivo_hasta_validacion(self):
        empresa = Empresa.objects.create(nombre='PRISLAB staging')
        equipo = Equipo.objects.create(nombre='INCCA staging', marca='Point Scientific')
        analito = Analito.objects.create(
            empresa=empresa,
            codigo='GLU-STAGING',
            abreviatura='GLU-STAGING',
            nombre='Glucosa staging',
            departamento='BIOQUIMICA CLINICA',
        )
        metodo = MetodoEquipo.objects.create(
            empresa=empresa,
            equipo=equipo,
            analito=analito,
            nombre_metodo_equipo='Glucosa Oxidasa',
            codigo_metodo_equipo='GLU',
            volumen_muestra='3',
            volumen_r1='300',
            volumen_r2='0',
            fuente_documental='fixture de prueba',
        )
        self.assertEqual(metodo.empresa_id, empresa.pk)
        self.assertFalse(metodo.activo)
        self.assertEqual(metodo.estado_validacion, 'PENDIENTE_MAPEO')

    def test_interfaz_y_resolucion_de_equipo_quedan_acotadas_al_tenant(self):
        empresa_a = Empresa.objects.create(nombre='PRISLAB interfaz')
        empresa_b = Empresa.objects.create(nombre='Otro laboratorio interfaz')
        equipo = Equipo.objects.create(
            empresa=empresa_a,
            nombre='Icon 3 staging',
            marca='Norma Instruments',
            ip_address='10.20.30.40',
            protocolo='HL7',
        )
        interfaz = InterfazEquipo.objects.create(
            empresa=empresa_a,
            equipo=equipo,
            tipo='ICON_HL7',
            estado='EN_PRUEBA',
            fuente_protocolaria='PROTOCOLO INTERFASE NORMA-3.pdf',
        )

        self.assertEqual(_resolver_equipo_por_ip('10.20.30.40', empresa_a), equipo)
        self.assertIsNone(_resolver_equipo_por_ip('10.20.30.40', empresa_b))
        self.assertEqual(interfaz.modo, 'SOMBRA')
        self.assertFalse(InterfazEquipo.objects.filter(empresa=empresa_b).exists())
