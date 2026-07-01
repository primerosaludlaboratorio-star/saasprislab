from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0085_kpi_models_v1'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='iso15189_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Activa el módulo de cumplimiento progresivo para este laboratorio.',
                verbose_name='ISO 15189 habilitado',
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='iso15189_mode',
            field=models.CharField(
                choices=[
                    ('OPTIONAL', 'Flexible / opcional'),
                    ('GUIDED', 'Guiado / sugerencias'),
                    ('STRICT', 'Estricto / obligatorio'),
                ],
                default='OPTIONAL',
                help_text='OPTIONAL = no bloquea; GUIDED = guía y avisa; STRICT = bloquea liberación si faltan controles.',
                max_length=20,
                verbose_name='Modo ISO 15189',
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='iso15189_target_date',
            field=models.DateField(
                blank=True,
                null=True,
                help_text='Fecha meta declarada por el laboratorio para alcanzar el nivel objetivo.',
                verbose_name='Fecha objetivo ISO 15189',
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='iso15189_last_audit',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Fecha y hora de la última revisión formal de cumplimiento.',
                verbose_name='Última auditoría ISO 15189',
            ),
        ),
        migrations.AddField(
            model_name='empresa',
            name='iso15189_compliance_percent',
            field=models.DecimalField(
                default=0,
                decimal_places=2,
                help_text='Porcentaje consolidado de checkpoints verificados.',
                max_digits=5,
                verbose_name='% cumplimiento ISO 15189',
            ),
        ),
    ]
