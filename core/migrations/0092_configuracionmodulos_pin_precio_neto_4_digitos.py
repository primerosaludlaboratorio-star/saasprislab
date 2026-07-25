from django.db import migrations, models
from django.core.validators import RegexValidator


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0091_venta_tipo_precio_especial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuracionmodulos',
            name='pin_precio_neto',
            field=models.CharField(
                blank=True,
                default='',
                help_text='PIN numérico de 4 dígitos para autorizar descuento a precio de costo. Debe configurarse manualmente.',
                max_length=4,
                validators=[RegexValidator(r'^$|^\d{4}$', 'El PIN debe contener exactamente 4 dígitos.')],
                verbose_name='PIN Precio Neto (Staff)',
            ),
        ),
    ]
