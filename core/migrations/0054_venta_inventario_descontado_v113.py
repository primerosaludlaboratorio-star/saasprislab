# Generated manually for CIERRE DE INTEGRIDAD FARMACIA v1.13
# Añade campo de idempotencia persistente a Venta para prevenir doble descuento de inventario

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0053_repoint_ia_iot_fk_ordendeservicio'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='inventario_descontado',
            field=models.BooleanField(
                default=False,
                verbose_name='Inventario Descontado',
                help_text='True si el Kardex ya descontó el stock. Previene doble descuento en reconexiones de signal.',
            ),
        ),
    ]
