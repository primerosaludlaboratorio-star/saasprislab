from datetime import date

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.models import Empresa
from inventario.models import CatalogoReactivoLab, LoteReactivoLab


class TrazabilidadAdaptacionTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Laboratorio de Adaptacion')
        self.reactivo = CatalogoReactivoLab.objects.create(
            empresa=self.empresa,
            codigo_interno='TST-001',
            nombre='Reactivo de prueba',
            tipo='REACTIVO',
            unidad_medida='UNIDAD',
        )
        self.usuario = get_user_model().objects.create_user(
            username='trazabilidad_user', password='test123456789', rol='ADMIN', empresa=self.empresa,
        )
        self.client = Client()
        self.client.force_login(self.usuario)

    def test_lote_operativo_puede_nacer_en_adaptacion(self):
        lote = LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=self.reactivo,
            numero_lote='LOT-ADAPT-1',
            fecha_caducidad=date(2030, 1, 1),
            cantidad_inicial=10,
            cantidad_actual=10,
        )

        self.assertEqual(lote.trazabilidad_estado, 'ADAPTACION')
        self.assertIn('marca', lote.campos_pendientes)
        self.assertIn('factura', lote.campos_pendientes)
        self.assertIn('inserto', lote.campos_pendientes)
        self.assertEqual(lote.cantidad_actual, 10)

    def test_lote_pasa_a_completo_al_cerrar_datos_documentales(self):
        lote = LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=self.reactivo,
            marca='Marca de prueba',
            numero_lote='LOT-COMP-1',
            fecha_caducidad=date(2030, 1, 1),
            fecha_compra=date(2026, 7, 23),
            factura_numero='FAC-001',
            inserto_estado='NO_APLICA',
            cantidad_inicial=10,
            cantidad_actual=10,
        )

        self.assertEqual(lote.trazabilidad_estado, 'COMPLETA')
        self.assertEqual(lote.campos_pendientes, [])

    def test_ficha_permite_completar_datos_sin_alterar_stock(self):
        lote = LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=self.reactivo,
            numero_lote='LOT-EDIT-1',
            fecha_caducidad=date(2030, 1, 1),
            cantidad_inicial=10,
            cantidad_actual=7,
        )

        response = self.client.post(reverse('inventario:editar_lote', args=[lote.pk]), {
            'marca': 'Marca recuperada',
            'fecha_apertura': '2026-07-23',
            'fecha_compra': '2026-07-01',
            'factura_estado': 'NO_DISPONIBLE',
            'inserto_estado': 'NO_APLICA',
            'inserto_version': '',
            'trazabilidad_observaciones': 'Factura pendiente de recuperar del archivo físico.',
        })

        self.assertEqual(response.status_code, 302)
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, 7)
        self.assertEqual(lote.trazabilidad_estado, 'COMPLETA')
        self.assertEqual(lote.marca, 'Marca recuperada')

    def test_modo_estricto_rechaza_lote_sin_datos_documentales(self):
        self.empresa.inventario_modo_adaptacion = False
        self.empresa.save(update_fields=['inventario_modo_adaptacion'])

        response = self.client.post(reverse('inventario:crear_lote'), {
            'reactivo': self.reactivo.pk,
            'numero_lote': 'LOT-STRICT-1',
            'fecha_caducidad': '2030-01-01',
            'cantidad_inicial': '10',
            'precio_unitario_compra': '1',
            'inserto_estado': 'PENDIENTE',
            'factura_estado': 'PENDIENTE',
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(LoteReactivoLab.objects.filter(numero_lote='LOT-STRICT-1').exists())
