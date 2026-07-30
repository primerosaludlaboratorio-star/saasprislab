import re

from django.contrib.auth.hashers import make_password
from django.db import migrations, models


PIN_FIELDS = ('pin_precio_neto', 'pin_cancelacion_venta')


def hash_legacy_pins(apps, schema_editor):
    ConfiguracionModulos = apps.get_model('core', 'ConfiguracionModulos')
    for configuracion in ConfiguracionModulos.objects.all().only('pk', *PIN_FIELDS).iterator():
        updates = {}
        for field_name in PIN_FIELDS:
            value = getattr(configuracion, field_name, '') or ''
            if re.fullmatch(r'\d{4}', value):
                updates[field_name] = make_password(value)
        if updates:
            ConfiguracionModulos.objects.filter(pk=configuracion.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0097_alter_ordendeservicio_archivo_resultado'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuracionmodulos',
            name='pin_precio_neto',
            field=models.CharField(
                blank=True,
                default='',
                help_text='PIN de 4 dígitos almacenado como hash; debe configurarse manualmente.',
                max_length=128,
                verbose_name='PIN Precio Neto (Staff)',
            ),
        ),
        migrations.AlterField(
            model_name='configuracionmodulos',
            name='pin_cancelacion_venta',
            field=models.CharField(
                blank=True,
                default='',
                help_text='PIN de 4 dígitos almacenado como hash; debe configurarse manualmente.',
                max_length=128,
                verbose_name='PIN Cancelación de Venta',
            ),
        ),
        migrations.RunPython(hash_legacy_pins, migrations.RunPython.noop),
    ]
