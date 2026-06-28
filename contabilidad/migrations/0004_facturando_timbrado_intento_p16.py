# Punto 16: estados FACTURANDO / PENDIENTE + timbrado_intento_en (ancla core.0065)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contabilidad", "0003_blindaje_fiscal_cupon_enfermeria"),
        ("core", "0065_forense_acceso_cofepris"),
    ]

    operations = [
        migrations.AddField(
            model_name="facturacfdi",
            name="timbrado_intento_en",
            field=models.DateTimeField(
                blank=True,
                help_text="Marca al entrar en FACTURANDO; usado por reconciliar_facturas_pendientes.",
                null=True,
                verbose_name="Inicio intento timbrado",
            ),
        ),
        migrations.AlterField(
            model_name="facturacfdi",
            name="estado",
            field=models.CharField(
                choices=[
                    ("BORRADOR", "Borrador"),
                    ("PENDIENTE", "Pendiente de timbrar"),
                    ("FACTURANDO", "Timbrado en curso (PAC)"),
                    ("TIMBRADO", "Timbrado"),
                    ("CANCELADO", "Cancelado"),
                    ("ERROR", "Error"),
                ],
                db_index=True,
                default="BORRADOR",
                max_length=20,
            ),
        ),
    ]
