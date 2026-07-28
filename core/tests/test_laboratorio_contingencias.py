from decimal import Decimal
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import DetalleOrden, Empresa, EnvioMaquila, OrdenDeServicio, Paciente
from core.utils.paths import generar_ruta_drive_laboratorio
from laboratorio.models import Equipo
from lims.models import Analito


Usuario = get_user_model()


class LaboratorioContingenciasTest(TestCase):
    def test_ruta_pdf_laboratorio_respeta_limite_de_filefield(self):
        paciente = type('PacienteLargo', (), {
            'nombre_completo': 'Paciente ' + ('Nombre Muy Largo ' * 12),
        })()
        orden = type('OrdenLarga', (), {
            'fecha_creacion': timezone.now(),
            'paciente': paciente,
            'folio_orden': 'LAB-20260728-ORDEN-DE-PRUEBA-LARGA',
            'id': 999,
            'prioridad': 'NORMAL',
        })()

        ruta = generar_ruta_drive_laboratorio(orden, 'resultado.pdf')

        self.assertLessEqual(len(ruta), 96)
        self.assertTrue(ruta.endswith('.pdf'))

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='PRISLAB contingencias', rfc='CON260728A1')
        self.otra_empresa = Empresa.objects.create(nombre='Otro laboratorio', rfc='CON260728B2')
        self.usuario = Usuario.objects.create_user(
            username='quimico_contingencias', password='Test2026!PRIS',
            empresa=self.empresa, rol='QUIMICO',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa, nombre_completo='Paciente Contingencia',
            nombres='Paciente', apellido_paterno='Contingencia', sexo='M',
        )
        self.analito = Analito.objects.create(
            empresa=self.empresa, codigo='CON-GLU', abreviatura='GLU',
            nombre='Glucosa contingencia', departamento='QUIMICA',
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa, paciente=self.paciente,
            responsable_ingreso=self.usuario, total=Decimal('100.00'),
            anticipo=Decimal('100.00'), estado='PAGADO', estado_pago='PAGADO',
            estado_clinico='EN_PROCESO', requiere_maquila=True,
        )
        self.detalle = DetalleOrden.objects.create(
            orden=self.orden, analito=self.analito,
            descripcion_linea=self.analito.nombre, precio_momento=Decimal('100.00'),
        )
        self.client.force_login(self.usuario)

    def test_error_de_rango_no_deja_transaccion_rota_ni_libera_resultado(self):
        payload = {
            'resultados': {
                str(self.detalle.pk): {
                    'resultado': '95',
                    'parametros': {str(self.analito.pk): {'valor': '95'}},
                },
            },
            'accion': 'validar',
        }
        with patch.object(
            __import__('core.models', fromlist=['ResultadoParametro']).ResultadoParametro,
            'validar_contra_rango',
            side_effect=DatabaseError('rango de prueba no disponible'),
        ):
            response = self.client.post(
                reverse('laboratorio:api_guardar_resultados', args=[self.orden.pk]),
                data=json.dumps(payload),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['codigo'], 'LIMS_RANGO_VALIDACION')
        self.orden.refresh_from_db()
        self.assertNotEqual(self.orden.estado, 'RESULTADOS_LISTOS')

    def test_maquila_se_recibe_una_sola_vez_y_retorna_a_captura(self):
        envio = EnvioMaquila.objects.create(
            empresa=self.empresa, laboratorio_externo='Laboratorio externo',
        )
        envio.ordenes.add(self.orden)
        self.orden.estado = 'EN_MAQUILA'
        self.orden.save(update_fields=['estado'])

        url = reverse('recibir_de_maquila', args=[envio.pk])
        response = self.client.post(url, {'notas_recepcion': 'Informe recibido'})
        self.assertEqual(response.status_code, 302)
        envio.refresh_from_db()
        self.orden.refresh_from_db()
        self.assertEqual(envio.estado, EnvioMaquila.ESTADO_RECIBIDA)
        self.assertEqual(self.orden.estado, 'EN_PROCESO')
        self.assertEqual(self.orden.estado_clinico, 'EN_PROCESO')

        self.client.post(url, {'notas_recepcion': 'Intento duplicado'})
        envio.refresh_from_db()
        self.assertEqual(envio.notas_recepcion, 'Informe recibido')

    def test_recepcion_maquila_no_cruza_empresa(self):
        envio = EnvioMaquila.objects.create(
            empresa=self.otra_empresa, laboratorio_externo='Externo ajeno',
        )
        response = self.client.post(reverse('recibir_de_maquila', args=[envio.pk]))
        self.assertEqual(response.status_code, 404)
        envio.refresh_from_db()
        self.assertEqual(envio.estado, EnvioMaquila.ESTADO_ENVIADA)

    def test_captura_solo_muestra_equipos_del_tenant(self):
        propio = Equipo.objects.create(empresa=self.empresa, nombre='INCCA PRISLAB', activo=True)
        ajeno = Equipo.objects.create(empresa=self.otra_empresa, nombre='INCCA ajeno', activo=True)
        response = self.client.get(reverse('captura_resultados', args=[self.orden.pk]))
        self.assertEqual(response.status_code, 200)
        ids = {equipo.pk for equipo in response.context['equipos_laboratorio']}
        self.assertIn(propio.pk, ids)
        self.assertNotIn(ajeno.pk, ids)
