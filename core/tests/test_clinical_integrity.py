import hashlib

from django.test import TestCase

from core.models import (
    ConsultaMedica,
    Empresa,
    HistorialCambiosConsulta,
    Medico,
    Paciente,
    Usuario,
)


class ClinicalHistoryIntegrityTests(TestCase):
    def test_hash_uses_persisted_creation_timestamp(self):
        empresa = Empresa.objects.create(nombre='Historial íntegro')
        usuario = Usuario.objects.create_user(username='historial_test', empresa=empresa)
        paciente = Paciente.objects.create(empresa=empresa, nombre_completo='Paciente')
        medico = Medico.objects.create(
            empresa=empresa,
            nombre_completo='Médico',
            cedula_profesional='HIST-1',
        )
        consulta = ConsultaMedica.objects.create(
            empresa=empresa,
            paciente=paciente,
            medico=medico,
            folio_consulta='HIST-1',
        )
        historial = HistorialCambiosConsulta.objects.create(
            consulta=consulta,
            campo_modificado='plan',
            valor_anterior='A',
            valor_nuevo='B',
            razon_cambio='Prueba',
            usuario_modificador=usuario,
        )

        payload = f'{consulta.id}planAB{historial.timestamp}'.encode()
        self.assertEqual(historial.hash_integridad, hashlib.sha256(payload).hexdigest())
