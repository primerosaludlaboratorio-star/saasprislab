import re

from django.db import migrations, models
from django.core.validators import RegexValidator


def limpiar_pines_legacy(apps, schema_editor):
    ConfiguracionModulos = apps.get_model('core', 'ConfiguracionModulos')
    for configuracion in ConfiguracionModulos.objects.all().only('pk', 'pin_precio_neto').iterator():
        pin = (configuracion.pin_precio_neto or '').strip()
        if pin and not re.fullmatch(r'\d{4}', pin):
            ConfiguracionModulos.objects.filter(pk=configuracion.pk).update(pin_precio_neto='')


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0091_venta_tipo_precio_especial'),
    ]

    operations = [
        migrations.RunPython(limpiar_pines_legacy, noop_reverse),
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
