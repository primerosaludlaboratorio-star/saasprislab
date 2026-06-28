# TransaccionHL7 (idempotencia HL7)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("iot", "0001_initial"),
        ("laboratorio", "0012_blindaje_hl7_admin_worm"),
        ("core", "0060_reparacion_grietas_blindaje"),
    ]

    operations = [
        migrations.CreateModel(
            name="TransaccionHL7",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hash_mensaje", models.CharField(db_index=True, help_text="SHA-256 hex del mensaje canonico (orden + analito + valor + IP).", max_length=64, unique=True)),
                ("analito_id", models.PositiveIntegerField(blank=True, null=True)),
                ("codigo_equipo", models.CharField(blank=True, default="", max_length=80)),
                ("ip_origen", models.GenericIPAddressField(blank=True, null=True)),
                ("creado", models.DateTimeField(auto_now_add=True)),
                (
                    "equipo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="transacciones_hl7",
                        to="laboratorio.equipo",
                    ),
                ),
                (
                    "orden_de_servicio",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="transacciones_hl7",
                        to="core.ordendeservicio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Transaccion HL7 (idempotencia)",
                "verbose_name_plural": "Transacciones HL7 (idempotencia)",
                "ordering": ["-creado"],
            },
        ),
        migrations.AddIndex(
            model_name="transaccionhl7",
            index=models.Index(fields=["-creado"], name="iot_txhl7_creado_idx"),
        ),
    ]
