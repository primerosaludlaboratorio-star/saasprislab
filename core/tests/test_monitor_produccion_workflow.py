import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.template.loader import render_to_string
from django.urls import reverse

from core.models import DetalleOrden, Empresa, OrdenDeServicio, Paciente
from core.services.resultados_impresion_presentacion import construir_detalles_procesados_orden
from core.utils.detalle_orden import attach_detalle_display_attrs
from core.utils.estandares_industriales import obtener_resultados_anteriores_paciente
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

    def test_templates_resultados_renderizan_detalle_lims_puro(self):
        orden = self._crear_orden_lims()
        OrdenDeServicio.objects.filter(id=orden.id).update(estado='RESULTADOS_LISTOS')
        orden.refresh_from_db()

        detalles, _ = construir_detalles_procesados_orden(orden)
        contexto = {
            'orden': orden,
            'detalles': detalles,
            'paciente': self.paciente,
            'empresa': self.empresa,
            'fecha_entrega': orden.fecha_creacion,
            'ultimo_validador': self.usuario,
            'fecha_impresion': orden.fecha_creacion,
            'modo_impresion': True,
            'qr_image': None,
            'url_verificacion': '',
            'solo_deuda': False,
            'paciente_nombre_documento': self.paciente.nombre_completo,
        }

        html_print = render_to_string('core/resultados_print.html', contexto)
        html_portal = render_to_string('core/resultados_portal_paciente.html', contexto)

        self.assertIn(self.analito.nombre, html_print)
        self.assertIn(self.analito.nombre, html_portal)

    def test_captura_y_consultorio_renderizan_display_lims(self):
        orden = self._crear_orden_lims()
        detalle = orden.detalles.select_related('analito').first()
        attach_detalle_display_attrs([detalle])
        item = {
            'detalle': detalle,
            'estudio': SimpleNamespace(
                nombre=detalle.display_nombre,
                codigo=detalle.display_codigo,
                es_perfil=False,
            ),
            'parametros': [],
        }

        html_captura = render_to_string('core/captura_resultados.html', {
            'orden': orden,
            'paciente': self.paciente,
            'detalles': [item],
            'triple_llave_completa': False,
            'puede_imprimir': False,
        })
        orden_consultorio = OrdenDeServicio.objects.prefetch_related(
            'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
        ).get(id=orden.id)
        attach_detalle_display_attrs(list(orden_consultorio.detalles.all()))
        html_consultorio = render_to_string('consultorio/resultados_lab_consulta.html', {
            'consulta': SimpleNamespace(
                paciente=self.paciente,
                fecha_creacion=orden.fecha_creacion,
            ),
            'ordenes_lab': [orden_consultorio],
        })

        self.assertIn(self.analito.nombre, html_captura)
        self.assertIn(self.analito.nombre, html_consultorio)

    def test_delta_check_lims_no_usa_prefetch_estudio_legacy(self):
        orden = self._crear_orden_lims()
        OrdenDeServicio.objects.filter(id=orden.id).update(estado='RESULTADOS_LISTOS')

        resultados = obtener_resultados_anteriores_paciente(
            self.paciente,
            self.empresa,
            codigo_estudio=self.analito.codigo,
        )

        self.assertIn(self.analito.codigo, resultados)

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
