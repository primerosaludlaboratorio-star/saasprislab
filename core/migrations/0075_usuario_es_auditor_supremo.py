from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0074_pagoorden_empresa_tenant_guard"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="es_auditor_supremo",
            field=models.BooleanField(
                default=False,
                help_text="Flag adicional para superusuarios con auditoria total sobre Prisci y el sistema.",
                verbose_name="Auditor Supremo / Super Master",
            ),
        ),
    ]
