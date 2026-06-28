# Solo BackupInmutableLog (WORM) — sin otros cambios de esquema.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0060_reparacion_grietas_blindaje"),
    ]

    operations = [
        migrations.CreateModel(
            name="BackupInmutableLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sha256_manifest", models.CharField(db_index=True, max_length=64, unique=True, verbose_name="SHA-256 (pre-cifrado, mismo que BackupRegistro.hash_verificacion)")),
                ("ruta_archivo", models.CharField(blank=True, default="", max_length=500, verbose_name="Ruta del .encrypted")),
                ("registrado_en", models.DateTimeField(auto_now_add=True, verbose_name="Registrado en")),
                (
                    "backup_registro",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="logs_inmutables",
                        to="core.backupregistro",
                        verbose_name="Backup asociado",
                    ),
                ),
            ],
            options={
                "verbose_name": "Log de backup inmutable",
                "verbose_name_plural": "Logs de backup inmutable",
                "ordering": ["-registrado_en"],
            },
        ),
    ]
