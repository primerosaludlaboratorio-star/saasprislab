import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import DetalleOrden, Empresa, OrdenDeServicio, Paciente
from lims.models import Analito


Usuario = get_user_model()


class MonitorProduccionWorkflowTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre='Empresa Monitor Lab',
            rfc='MON260621TST',
        )
        self.usuario = Usuario.objects.create_user(
            username='monitor_lab_user',
            password='test123456789',
            empresa=self.empresa,
            rol='ADMIN',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente Monitor',
            nombres='Paciente',
            apellido_paterno='Monitor',
            sexo='M',
        )
        self.analito = Analito.objects.create(
            empresa=self.empresa,
            codigo='GLU-MON',
            abreviatura='GLU',
            nombre='GLUCOSA MONITOR',
            departamento='BIOQUIMICA',
            tipo_muestra='SUERO',
            es_vendible_individualmente=True,
            costo_lista=Decimal('85.00'),
        )
        self.client.login(username='monitor_lab_user', password='test123456789')

    def test_avanzar_validado_parcial_a_completo_no_exige_estudio_legacy(self):
        """El Kanban debe aceptar detalles LIMS puros sin FK legacy estudio."""
        orden = self._crear_orden_lims(estado_clinico='VALIDADO_PARCIAL')

        with patch('core.services.validador_ia.validar_orden_completa', return_value=[]):
            with patch('core.services.motor_reportes_lab.generar_reporte_pdf', return_value=b'%PDF-1.4 mock'):
                with patch('core.services.motor_reportes_lab.guardar_reporte_en_storage', return_value='/media/resultados/mock.pdf'):
                    response = self.client.post(
                        reverse('laboratorio:api_avanzar_estado'),
                        data=json.dumps({'orden_id': orden.id}),
                        content_type='application/json',
                    )

        data = response.json()
        self.assertEqual(response.status_code, 200, data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['estado_anterior'], 'VALIDADO_PARCIAL')
        self.assertEqual(data['estado_nuevo'], 'COMPLETO')

        orden.refresh_from_db()
        self.assertEqual(orden.estado_clinico, 'COMPLETO')
        self.assertEqual(orden.estado, 'RESULTADOS_LISTOS')

    def test_toma_muestra_renderiza_detalles_lims_sin_estudio_legacy(self):
        orden = self._crear_orden_lims()

        response = self.client.get(reverse('toma_muestra_index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, orden.folio_orden)
        self.assertContains(response, self.analito.nombre)

    def test_impresion_raw_renderiza_detalles_lims_sin_estudio_legacy(self):
        orden = self._crear_orden_lims()

        ticket = self.client.get(reverse('imprimir_ticket_raw', args=[orden.id]))
        etiquetas = self.client.get(reverse('imprimir_etiquetas_raw', args=[orden.id]))

        self.assertEqual(ticket.status_code, 200)
        self.assertContains(ticket, self.analito.nombre)
        self.assertEqual(etiquetas.status_code, 200)
        self.assertContains(etiquetas, self.analito.abreviatura)

    def _crear_orden_lims(self, estado_clinico='PENDIENTE_TOMA'):
        orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            responsable_ingreso=self.usuario,
            total=Decimal('85.00'),
            anticipo=Decimal('0.00'),
            estado='PAGADO',
            estado_pago='PENDIENTE',
            estado_clinico=estado_clinico,
        )
        DetalleOrden.objects.create(
            orden=orden,
            analito=self.analito,
            descripcion_linea=self.analito.nombre,
            precio_momento=Decimal('85.00'),
            resultado='90',
            validado_por=self.usuario,
        )
        return orden
