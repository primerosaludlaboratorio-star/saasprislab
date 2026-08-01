from unittest.mock import patch

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings

from core.fields import EncryptedTextField
from core.models import (
    AuditLog,
    ConfiguracionModulos,
    ExpedienteNotaSHA,
    Empresa,
    NotaClinicaSOAP,
    Paciente,
    Usuario,
    verificar_pin_farmacia,
)
from core.tenant import clear_current_empresa, set_current_empresa


class FarmaciaPinSecurityTests(TestCase):
    def test_pins_are_hashed_and_verifiable(self):
        config = ConfiguracionModulos.objects.create(
            empresa=Empresa.objects.create(nombre='PIN seguro'),
            pin_precio_neto='5938',
            pin_cancelacion_venta='2468',
        )
        config.refresh_from_db()

        self.assertNotEqual(config.pin_precio_neto, '5938')
        self.assertNotEqual(config.pin_cancelacion_venta, '2468')
        self.assertTrue(verificar_pin_farmacia(config.pin_precio_neto, '5938'))
        self.assertTrue(verificar_pin_farmacia(config.pin_cancelacion_venta, '2468'))
        self.assertFalse(verificar_pin_farmacia(config.pin_precio_neto, '0000'))


class EncryptedTextFieldSecurityTests(SimpleTestCase):
    @override_settings(FERNET_KEY=Fernet.generate_key().decode())
    def test_encrypt_returns_ciphertext(self):
        ciphertext = EncryptedTextField.encrypt('dato confidencial')
        self.assertNotEqual(ciphertext, 'dato confidencial')

    @patch('core.fields._get_fernet', return_value=None)
    def test_encrypt_fails_closed_when_fernet_unavailable(self, _mock_fernet):
        with self.assertRaises(ImproperlyConfigured):
            EncryptedTextField.encrypt('dato confidencial')

    @patch('core.fields._get_fernet', side_effect=ValueError('clave inválida'))
    def test_encrypt_fails_closed_when_fernet_errors(self, _mock_fernet):
        with self.assertRaises(ImproperlyConfigured):
            EncryptedTextField.encrypt('dato confidencial')


class ExpedienteNotaSHASecurityTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Cadena clínica')
        self.medico = Usuario.objects.create_user(
            username='medico_cadena',
            password='prueba-segura',
            empresa=self.empresa,
            rol='MEDICO',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente Cadena',
        )
        self.nota = NotaClinicaSOAP.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            medico=self.medico,
            subjetivo='S',
            objetivo='O',
            analisis='A',
            plan='P',
        )

    def test_new_snapshot_sets_timestamp_before_hashing(self):
        snapshot = {'nota': self.nota.pk, 'estado': 'BORRADOR'}
        expediente = ExpedienteNotaSHA.objects.create(
            nota_soap=self.nota,
            empresa=self.empresa,
            paciente=self.paciente,
            medico=self.medico,
            version=2,
            snapshot_jsonb=snapshot,
        )

        self.assertIsNotNone(expediente.timestamp_creacion)
        self.assertTrue(expediente.verificar_integridad())

    def test_second_snapshot_hash_uses_previous_hash(self):
        first = ExpedienteNotaSHA.objects.create(
            nota_soap=self.nota,
            empresa=self.empresa,
            paciente=self.paciente,
            medico=self.medico,
            version=2,
            snapshot_jsonb={'version': 2},
        )
        second = ExpedienteNotaSHA(
            nota_soap=self.nota,
            empresa=self.empresa,
            paciente=self.paciente,
            medico=self.medico,
            version=first.version + 1,
            snapshot_jsonb={'version': 3},
        )
        second.save()

        self.assertEqual(second.hash_anterior, first.hash_sha256)
        self.assertTrue(second.verificar_integridad())
        self.assertTrue(second.verificar_cadena())

    def test_snapshot_is_append_only(self):
        expediente = ExpedienteNotaSHA.objects.create(
            nota_soap=self.nota,
            empresa=self.empresa,
            paciente=self.paciente,
            medico=self.medico,
            version=2,
            snapshot_jsonb={'version': 1},
        )

        with self.assertRaises(ValidationError):
            expediente.save()
        with self.assertRaises(ValidationError):
            ExpedienteNotaSHA.objects.filter(pk=expediente.pk).update(estado_nota='SELLADA')
        with self.assertRaises(ValidationError):
            expediente.delete()


class TenantAppendOnlyManagerTests(TestCase):
    def test_audit_log_default_manager_is_tenant_scoped_and_immutable(self):
        empresa_a = Empresa.objects.create(nombre='Empresa A')
        empresa_b = Empresa.objects.create(nombre='Empresa B')
        AuditLog.objects_all.create(
            empresa=empresa_a,
            accion=AuditLog.ACCION_VIEW,
            modelo_afectado='Paciente',
            objeto_id='1',
        )
        AuditLog.objects_all.create(
            empresa=empresa_b,
            accion=AuditLog.ACCION_VIEW,
            modelo_afectado='Paciente',
            objeto_id='2',
        )

        set_current_empresa(empresa_a)
        self.addCleanup(clear_current_empresa)
        self.assertEqual(AuditLog.objects.count(), 1)
        with self.assertRaises(ValidationError):
            AuditLog.objects.filter(empresa=empresa_a).update(objeto_id='99')
