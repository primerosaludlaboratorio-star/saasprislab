from django.core.validators import RegexValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0093_gastocaja_sucursal_pago_monto_vales_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionmodulos',
            name='pin_cancelacion_venta',
            field=models.CharField(
                blank=True,
                default='',
                help_text='PIN temporal o individual de 4 dígitos para autorizar cancelaciones de ventas.',
                max_length=4,
                validators=[RegexValidator(r'^$|^\d{4}$', 'El PIN debe contener exactamente 4 dígitos.')],
                verbose_name='PIN Cancelación de Venta',
            ),
        ),
    ]
