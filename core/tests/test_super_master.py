from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.test import TestCase

from core.models import AuditLog, Empresa, Usuario
from core.services.super_master_audit import es_super_master, obtener_logs_auditoria_global


class SuperMasterTest(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre="Audit A")
        self.empresa_b = Empresa.objects.create(nombre="Audit B")
        self.super_master = Usuario.objects.create_superuser(
            username="super_master",
            password="x",
            empresa=self.empresa_a,
            es_auditor_supremo=True,
        )
        self.admin_normal = Usuario.objects.create_user(
            username="admin_normal",
            password="x",
            empresa=self.empresa_a,
            is_staff=True,
            is_superuser=True,
            es_auditor_supremo=False,
        )
        self.log_a = AuditLog.objects.create(
            empresa=self.empresa_a,
            usuario=self.admin_normal,
            accion=AuditLog.ACCION_VIEW,
            modelo_afectado="Paciente",
            objeto_id="A-1",
        )
        self.log_b = AuditLog.objects.create(
            empresa=self.empresa_b,
            usuario=self.admin_normal,
            accion=AuditLog.ACCION_VIEW,
            modelo_afectado="Paciente",
            objeto_id="B-1",
        )

    def test_super_master_flag_requires_superuser_and_auditor_flag(self):
        self.assertTrue(es_super_master(self.super_master))
        self.assertFalse(es_super_master(self.admin_normal))

    def test_super_master_can_read_audit_logs_across_tenants(self):
        logs = obtener_logs_auditoria_global(self.super_master)

        self.assertIn(self.log_a, logs)
        self.assertIn(self.log_b, logs)

    def test_regular_admin_cannot_read_global_audit_logs(self):
        with self.assertRaises(PermissionDenied):
            obtener_logs_auditoria_global(self.admin_normal)

    def test_seed_super_master_role_marks_existing_superuser(self):
        target = Usuario.objects.create_superuser(
            username="seed_target",
            password="x",
            empresa=self.empresa_a,
        )

        call_command("seed_super_master_role", username="seed_target", verbosity=0)
        target.refresh_from_db()

        self.assertTrue(target.es_auditor_supremo)
        self.assertTrue(Group.objects.get(name="Super Master").user_set.filter(pk=target.pk).exists())
