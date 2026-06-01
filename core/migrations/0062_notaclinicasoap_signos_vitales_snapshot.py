# H-009: snapshot JSON de signos vitales en nota SOAP (cadena SHA expediente)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0061_backupinmutablelog'),
    ]

    operations = [
        migrations.AddField(
            model_name='notaclinicasoap',
            name='signos_vitales_snapshot',
            field=models.JSONField(
                blank=True,
                help_text='JSON inmutable enlazado a la cadena SHA del expediente (H-009).',
                null=True,
                verbose_name='Snapshot signos vitales (triage)',
            ),
        ),
    ]
