from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.db import close_old_connections
from django.test import TransactionTestCase

from core.models import Empresa
from inventario.models import CatalogoReactivoLab, LoteReactivoLab
from laboratorio.models import Equipo
from mantenimiento.models import ExpedienteEquipo, TicketMantenimientoCMMS, SalidaRefaccionMantenimiento
from mantenimiento.services.consumo_refacciones_service import (
    StockInsuficienteError,
    registrar_consumo_refaccion,
)


User = get_user_model()


class TestConcurrenciaCMMS(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre='PRISLAB CMMS Test',
            rfc='CMM123456AAA',
        )
        self.usuario = User.objects.create_user(
            username='cmms_tester',
            password='TestPass123!',
            empresa=self.empresa,
            rol='ADMIN',
        )
        self.reactivo = CatalogoReactivoLab.objects.create(
            empresa=self.empresa,
            codigo_interno='REF-CMMS-001',
            nombre='Filtro de reemplazo',
            tipo='REFACCION',
            unidad_medida='UNIDAD',
            stock_minimo=Decimal('0.0000'),
        )
        self.equipo = Equipo.objects.create(
            nombre='Analizador CMMS',
            marca='PRISLAB',
            protocolo=Equipo.PROTOCOLO_HL7,
            activo=True,
        )
        self.expediente = ExpedienteEquipo.objects.create(
            empresa=self.empresa,
            equipo=self.equipo,
            tipo_equipo='ANALIZADOR',
            silo_refacciones='LAB',
            numero_serie='SERIE-CMMS-001',
            modelo='MODEL-CMMS',
            fabricante='PRISLAB',
        )
        self.ticket = TicketMantenimientoCMMS.objects.create(
            empresa=self.empresa,
            expediente=self.expediente,
            tipo_origen='MANUAL',
            titulo='Cambio de filtro',
            descripcion='Prueba de concurrencia CMMS',
            estado='ABIERTO',
            nivel_escalamiento_actual='QUIMICO',
            creado_por=self.usuario,
            asignado_a=self.usuario,
        )
        self.lote = LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=self.reactivo,
            numero_lote='L-CMMS-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=Decimal('1.0000'),
            cantidad_actual=Decimal('1.0000'),
            precio_unitario_compra=Decimal('100.0000'),
            lote_aprobado_qc=True,
            estado='ACTIVO',
            recibido_por=self.usuario,
            aprobado_por=self.usuario,
        )

    def _intentar_consumo(self):
        close_old_connections()
        try:
            salida = registrar_consumo_refaccion(
                ticket=self.ticket,
                empresa=self.empresa,
                silo_origen='LAB',
                lote_object_id=self.lote.pk,
                cantidad_usada=Decimal('1.0000'),
                unidad='UNIDAD',
                registrado_por=self.usuario,
                observacion='Prueba concurrente',
                paso_reparacion=None,
            )
            return ('ok', salida.pk)
        except StockInsuficienteError as exc:
            return ('stock', str(exc))
        except Exception as exc:
            return ('error', type(exc).__name__)
        finally:
            close_old_connections()

    def test_solo_un_hilo_descuenta_y_congela_snapshot(self):
        if connection.vendor == 'sqlite':
            self.skipTest('SQLite no ofrece un escenario confiable para certificar select_for_update multi-hilo.')

        with ThreadPoolExecutor(max_workers=5) as executor:
            resultados = list(executor.map(lambda _: self._intentar_consumo(), range(5)))

        exitosos = [r for r in resultados if r[0] == 'ok']
        rechazados_stock = [r for r in resultados if r[0] == 'stock']
        errores = [r for r in resultados if r[0] == 'error']

        self.lote.refresh_from_db()

        self.assertEqual(len(exitosos), 1, resultados)
        self.assertEqual(len(errores), 0, resultados)
        self.assertEqual(len(rechazados_stock), 4, resultados)
        self.assertEqual(self.lote.cantidad_actual, Decimal('0.0000'))
        self.assertEqual(SalidaRefaccionMantenimiento.objects.filter(ticket=self.ticket).count(), 1)

        salida = SalidaRefaccionMantenimiento.objects.get(ticket=self.ticket)
        self.assertEqual(salida.cantidad_usada, Decimal('1.0000'))
        self.assertEqual(salida.costo_unitario_snapshot, Decimal('100.0000'))
        self.assertEqual(salida.costo_total_snapshot, Decimal('100.00'))
        self.assertEqual(salida.stock_anterior_snapshot, Decimal('1.0000'))
        self.assertEqual(salida.stock_resultante_snapshot, Decimal('0.0000'))
        self.assertEqual(salida.lote_object_id, self.lote.pk)
