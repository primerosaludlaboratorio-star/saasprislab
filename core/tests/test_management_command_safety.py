import os
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from core.management.commands.backup_nocturno import Command as BackupCommand
from core.management.commands.resetear_personal_final import Command as ResetPersonalCommand
from core.management.commands.resetear_usuarios_acceso import Command as ResetUsersCommand
from core.management.commands.unificar_empresa_prislab import Command as MergeCommand
from core.management.commands.wipe_datos_operativos import Command as WipeCommand
from core.management.commands.sentinel_reset import Command as SentinelResetCommand


class ManagementCommandSafetyTests(SimpleTestCase):
    @override_settings(IS_PRODUCTION=True)
    @patch.dict(os.environ, {"PRISLAB_ACCESS_RESET_PASSWORD": ""}, clear=False)
    def test_user_reset_requires_explicit_password_in_production(self):
        with self.assertRaises(CommandError):
            ResetUsersCommand()._get_password("PRISLAB_ACCESS_RESET_PASSWORD")

    @override_settings(IS_PRODUCTION=True)
    @patch.dict(os.environ, {"PRISLAB_PERSONAL_RESET_PASSWORD": ""}, clear=False)
    def test_personal_reset_requires_explicit_password_in_production(self):
        with self.assertRaises(CommandError):
            ResetPersonalCommand().handle(dry_run=False, confirm_reset=True,
                                          password_env="PRISLAB_PERSONAL_RESET_PASSWORD")

    @override_settings(IS_PRODUCTION=True)
    def test_operational_wipe_is_blocked_in_production(self):
        with self.assertRaises(CommandError):
            WipeCommand().handle(media=False, yes=True)

    @override_settings(IS_PRODUCTION=True)
    def test_tenant_merge_is_blocked_in_production(self):
        with self.assertRaises(CommandError):
            MergeCommand().handle(dry_run=False, apply=True, confirm_merge=True)

    @patch.dict(os.environ, {"PRISLAB_BACKUP_ENCRYPTION_KEY": ""}, clear=False)
    def test_backup_requires_dedicated_fernet_key(self):
        with self.assertRaises(CommandError):
            BackupCommand()._generar_clave_encriptacion()

    @override_settings(IS_PRODUCTION=True)
    def test_sentinel_reset_requires_explicit_apply_and_scope(self):
        with self.assertRaises(CommandError):
            SentinelResetCommand().handle(
                dry_run=False, delete=False, apply=True,
                confirm_reset=False, confirm_delete=False,
                empresa_id=None, all_tenants=False,
            )

    @override_settings(IS_PRODUCTION=True)
    def test_sentinel_reset_blocks_global_scope_in_production(self):
        with self.assertRaises(CommandError):
            SentinelResetCommand().handle(
                dry_run=False, delete=False, apply=True,
                confirm_reset=True, confirm_delete=False,
                empresa_id=None, all_tenants=True,
            )
