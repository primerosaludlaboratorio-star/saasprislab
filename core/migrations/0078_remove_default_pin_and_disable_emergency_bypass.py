from django.db import migrations, models


def scrub_insecure_pin(apps, schema_editor):
    ConfiguracionModulos = apps.get_model('core', 'ConfiguracionModulos')
    ConfiguracionModulos.objects.filter(pin_precio_neto='1234').update(pin_precio_neto='')


def noop_reverse(apps, schema_editor):
    # No restauramos el default inseguro.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0077_alter_medico_cedula_profesional_and_more'),
    ]

    operations = [
        migrations.RunPython(scrub_insecure_pin, noop_reverse),
        migrations.AlterField(
            model_name='configuracionmodulos',
            name='pin_precio_neto',
            field=models.CharField(blank=True, default='', help_text='PIN numérico para autorizar descuento a precio de costo. Debe configurarse manualmente.', max_length=10, verbose_name='PIN Precio Neto (Staff)'),
        ),
    ]
