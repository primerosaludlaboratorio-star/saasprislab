from django.test import TestCase

from core.models import AuditLog, Empresa, ForenseAcceso


class AuditAppendOnlyTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa Audit Test', rfc='AUT010101AAA')

    def test_auditlog_blocks_update_and_delete(self):
        log = AuditLog.objects.create(
            empresa=self.empresa,
            accion=AuditLog.ACCION_CREATE,
            modelo_afectado='Paciente',
            objeto_id='123',
        )

        log.modelo_afectado = 'OrdenDeServicio'
        with self.assertRaises(RuntimeError):
            log.save()

        with self.assertRaises(RuntimeError):
            log.delete()

    def test_forenseacceso_blocks_update_and_delete(self):
        acc = ForenseAcceso.objects.create(
            empresa=self.empresa,
            accion=ForenseAcceso.ACCION_VALIDACION_TOKEN,
            paciente_id=1,
            orden_id=1,
            es_publico=True,
        )

        acc.token_prefix = 'ABCD1234'
        with self.assertRaises(RuntimeError):
            acc.save()

        with self.assertRaises(RuntimeError):
            acc.delete()
