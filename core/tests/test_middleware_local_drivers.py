import socket

from django.test import SimpleTestCase

from middleware_local.drivers.fuji_nx600 import FujiNX600Driver
from middleware_local.drivers.incca_chem import InCCAChemDriver
from middleware_local.drivers.mission_u120 import MissionU120Driver
from middleware_local.drivers.norma_icon import NormaIconDriver
from middleware_local.drivers.wondfo_finecare import WondfoFinecareDriver


class FakeSerial:
    def __init__(self, data=b''):
        self._data = bytearray(data)
        self.is_open = True
        self.written = []

    @property
    def in_waiting(self):
        return len(self._data)

    def read(self, size):
        chunk = bytes(self._data[:size])
        del self._data[:size]
        return chunk

    def write(self, data):
        self.written.append(data)
        return len(data)


class FakeSocket:
    def __init__(self, data=b''):
        self._data = bytearray(data)
        self.sent = []

    def recv(self, size):
        if not self._data:
            raise socket.timeout()
        chunk = bytes(self._data[:size])
        del self._data[:size]
        return chunk

    def sendall(self, data):
        self.sent.append(data)


def build_astm_frame(body: bytes) -> bytes:
    checksum = f"{sum(body + InCCAChemDriver.ETX) & 0xFF:02X}".encode("ascii")
    return InCCAChemDriver.STX + body + InCCAChemDriver.ETX + checksum


class MiddlewareLocalDriversTests(SimpleTestCase):
    def test_fuji_procesar_drena_trama_y_mapea_codigo(self):
        driver = FujiNX600Driver({'nombre': 'Fuji Test'})
        driver.serial_port = FakeSerial(b'\x02GLU-P,95.5,mg/dL,NORMAL\x03')
        recibidos = []
        driver.on_result = recibidos.append

        estado = driver.procesar()

        self.assertEqual(estado['bytes_leidos'], 25)
        self.assertEqual(len(recibidos), 1)
        resultado = recibidos[0]['resultados'][0]
        self.assertEqual(resultado['codigo_prislab'], 'GLU')
        self.assertEqual(resultado['valor'], 95.5)

    def test_incca_procesar_valida_checksum_astm_y_envia_ack(self):
        body = (
            b'H|\\^&|||INCCA\r'
            b'P|1|PAC123|||Doe^Ana\r'
            b'O|1|ORD123\r'
            b'R|1|GLU|95|mg/dL|70-110\r'
            b'L|1'
        )
        driver = InCCAChemDriver({'nombre': 'InCCA Test'})
        driver.serial_port = FakeSerial(build_astm_frame(body))
        recibidos = []
        driver.on_result = recibidos.append

        estado = driver.procesar()

        self.assertGreater(estado['bytes_leidos'], 0)
        self.assertEqual(len(recibidos), 1)
        self.assertEqual(recibidos[0]['paciente']['id'], 'PAC123')
        self.assertEqual(recibidos[0]['registros'][0]['codigo_prueba'], 'GLU')
        self.assertIn(driver.ACK, driver.serial_port.written)

    def test_mission_procesar_linea_texto(self):
        driver = MissionU120Driver({'nombre': 'Mission Test'})
        driver.serial_port = FakeSerial(b'PAC123,GLU,95,mg/dL\r\n')
        recibidos = []
        driver.on_result = recibidos.append

        estado = driver.procesar()

        self.assertEqual(estado['bytes_leidos'], 21)
        self.assertEqual(recibidos[0]['paciente_id'], 'PAC123')
        self.assertEqual(recibidos[0]['codigo_prueba'], 'GLU')

    def test_wondfo_procesar_mensaje_generico_serial(self):
        driver = WondfoFinecareDriver({'nombre': 'Wondfo Test', 'tipo': 'serial'})
        driver.serial_port = FakeSerial(b'PAC123|CRP|5|mg/L\r\n')
        recibidos = []
        driver.on_result = recibidos.append

        estado = driver.procesar()

        self.assertEqual(estado['bytes_leidos'], 19)
        self.assertEqual(recibidos[0]['paciente_id'], 'PAC123')
        self.assertEqual(recibidos[0]['codigo_prueba'], 'CRP')

    def test_norma_procesar_hl7_mllp_y_envia_ack(self):
        hl7 = (
            'MSH|^~\\&|NORMA|LAB|PRISLAB|SUC|20260504120000||ORU^R01|MSG123|P|2.5\r'
            'OBR|1||ORD123\r'
            'OBX|1|NM|GLU^Glucosa||95|mg/dL\r'
        )
        socket_fake = FakeSocket(b'\x0b' + hl7.encode('utf-8') + b'\x1c\x0d')
        driver = NormaIconDriver({'nombre': 'Norma Test', 'mllp': True})
        driver.cliente_socket = socket_fake
        recibidos = []
        driver.on_result = recibidos.append

        estado = driver.procesar()

        self.assertGreater(estado['bytes_leidos'], 0)
        self.assertEqual(recibidos[0]['hl7_raw'], hl7)
        self.assertTrue(any(b'MSA|AA|MSG123' in ack for ack in socket_fake.sent))
