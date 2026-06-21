import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import ConsentimientoInformado, Empresa, OrdenDeServicio, Paciente


Usuario = get_user_model()


class LabValidationPdfTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre='Empresa Lab PDF',
            rfc='PDF260507TST',
        )
        self.usuario = Usuario.objects.create_user(
            username='lab_pdf_user',
            password='test123456789',
            empresa=self.empresa,
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente PDF',
            sexo='M',
        )
        self.client.login(username='lab_pdf_user', password='test123456789')

    def _crear_orden(self, total='100.00', anticipo='100.00'):
        return OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            responsable_ingreso=self.usuario,
            total=Decimal(total),
            anticipo=Decimal(anticipo),
            estado='PAGADO',
        )

    @override_settings(LAB_VALIDATION_PIN='')
    def test_validar_pin_sin_configuracion_falla_seguro(self):
        orden = self._crear_orden()

        response = self.client.post(
            reverse('api_validar_pin', args=[orden.id]),
            data=json.dumps({'pin': '1234'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()['ok'])
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'PAGADO')

    @override_settings(LAB_VALIDATION_PIN='7777')
    def test_validar_pin_genera_pdf_antes_de_marcar_orden_pagada(self):
        orden = self._crear_orden()

        def guardar_mock(orden_arg, pdf_bytes):
            self.assertEqual(pdf_bytes, b'%PDF-1.4 mock')
            orden_arg.archivo_resultado.name = 'resultados_pdf/mock.pdf'
            orden_arg.save(update_fields=['archivo_resultado'])
            return '/media/resultados_pdf/mock.pdf'

        with patch('core.services.motor_reportes_lab.generar_reporte_pdf', return_value=b'%PDF-1.4 mock') as generar:
            with patch('core.services.motor_reportes_lab.guardar_reporte_en_storage', side_effect=guardar_mock):
                response = self.client.post(
                    reverse('api_validar_pin', args=[orden.id]),
                    data=json.dumps({'pin': '7777'}),
                    content_type='application/json',
                )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        generar.assert_called_once()
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'RESULTADOS_LISTOS')
        self.assertEqual(orden.archivo_resultado.name, 'resultados_pdf/mock.pdf')

    @override_settings(LAB_VALIDATION_PIN='7777')
    def test_validar_pin_no_genera_pdf_si_hay_saldo_pendiente(self):
        orden = self._crear_orden(total='100.00', anticipo='0.00')

        with patch('core.services.motor_reportes_lab.generar_reporte_pdf') as generar:
            response = self.client.post(
                reverse('api_validar_pin', args=[orden.id]),
                data=json.dumps({'pin': '7777'}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        generar.assert_not_called()
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'RESULTADOS_LISTOS')
        self.assertFalse(orden.archivo_resultado)

    def test_imprimir_resultados_formato_pdf_usa_consentimiento_real(self):
        orden = self._crear_orden()
        OrdenDeServicio.objects.filter(id=orden.id).update(estado='RESULTADOS_LISTOS')
        orden.refresh_from_db()
        ConsentimientoInformado.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            orden=orden,
            firma_digital='data:image/png;base64,abc',
            acepta_privacidad=True,
            acepta_procesamiento=True,
        )

        with patch('core.services.motor_reportes_lab.generar_reporte_pdf', return_value=b'%PDF-1.4 mock') as generar:
            with patch('core.services.motor_reportes_lab.guardar_reporte_en_storage', return_value='/media/resultados_pdf/mock.pdf'):
                response = self.client.get(
                    reverse('imprimir_resultados_pdf', args=[orden.id]) + '?formato=pdf'
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response.content, b'%PDF-1.4 mock')
        generar.assert_called_once()

    def test_imprimir_resultados_staff_bloquea_orden_no_validada(self):
        orden = self._crear_orden()

        with patch('core.views.laboratorio_reportes.generar_reporte_pdf') as generar:
            response = self.client.get(reverse('imprimir_resultados', args=[orden.id]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('captura_resultados', args=[orden.id]))
        generar.assert_not_called()

    def test_imprimir_resultados_staff_bloquea_sin_consentimiento_digital(self):
        orden = self._crear_orden()
        OrdenDeServicio.objects.filter(id=orden.id).update(estado='RESULTADOS_LISTOS')

        with patch('core.views.laboratorio_reportes.generar_reporte_pdf') as generar:
            response = self.client.get(reverse('imprimir_resultados', args=[orden.id]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('captura_resultados', args=[orden.id]))
        generar.assert_not_called()
