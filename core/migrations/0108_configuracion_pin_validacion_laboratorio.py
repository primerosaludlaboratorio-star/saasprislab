from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0107_consentimiento_folio'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionmodulos',
            name='pin_validacion_laboratorio',
            field=models.CharField(
                blank=True,
                default='',
                help_text=(
                    'Hash Django del PIN clínico de esta empresa (mínimo 8 caracteres). '
                    'Nunca se almacena el PIN en texto plano.'
                ),
                max_length=128,
                verbose_name='PIN de Validación de Laboratorio',
            ),
        ),
    ]
