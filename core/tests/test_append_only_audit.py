from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import AuditLog, Empresa, ForenseAcceso


class AppendOnlyAuditTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Append Only Test')

    def test_audit_log_rejects_mutation_and_delete(self):
        log = AuditLog.objects.create(
            empresa=self.empresa,
            accion=AuditLog.ACCION_VIEW,
            modelo_afectado='Paciente',
            objeto_id='1',
        )

        log.modelo_afectado = 'PacienteAlterado'
        with self.assertRaises(ValidationError):
            log.save()
        with self.assertRaises(ValidationError):
            log.delete()
        with self.assertRaises(ValidationError):
            AuditLog.objects.filter(pk=log.pk).update(modelo_afectado='Otro')
        with self.assertRaises(ValidationError):
            AuditLog.objects.filter(pk=log.pk).delete()

    def test_forense_acceso_rejects_mutation_and_delete(self):
        acceso = ForenseAcceso.objects.create(
            empresa=self.empresa,
            accion=ForenseAcceso.ACCION_VALIDACION_TOKEN,
        )

        acceso.token_prefix = 'mutado'
        with self.assertRaises(ValidationError):
            acceso.save()
        with self.assertRaises(ValidationError):
            acceso.delete()
        with self.assertRaises(ValidationError):
            ForenseAcceso.objects.filter(pk=acceso.pk).update(token_prefix='otro')
        with self.assertRaises(ValidationError):
            ForenseAcceso.objects.filter(pk=acceso.pk).delete()
