# Blindaje: calibración Equipo + protocolo JSON en ResultadoHL7

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0011_add_performance_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipo",
            name="fecha_vencimiento_calibracion",
            field=models.DateField(
                blank=True,
                help_text="Fecha límite de validez metrológica/calibración. Si vence, el receptor HL7 puede bloquear integración.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="resultadohl7",
            name="protocolo",
            field=models.CharField(
                choices=[
                    ("HL7", "HL7 v2.x"),
                    ("ASTM", "ASTM E1394"),
                    ("JSON", "JSON / API"),
                ],
                default="HL7",
                max_length=10,
            ),
        ),
    ]
