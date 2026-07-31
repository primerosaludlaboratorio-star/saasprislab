from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0102_alter_producto_codigo_barras_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='medico',
            name='lab_validation_pin_hash',
            field=models.CharField(
                blank=True,
                help_text='SHA256 del PIN de validación para firmar notas. NUNCA almacenar el PIN en texto plano.',
                max_length=128,
                verbose_name='Hash del PIN-LAB',
            ),
        ),
    ]
