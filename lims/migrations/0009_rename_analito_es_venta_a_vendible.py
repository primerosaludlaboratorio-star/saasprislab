from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lims', '0007b_empresa_nullable_lims'),
    ]

    operations = [
        migrations.RenameField(
            model_name='analito',
            old_name='es_venta_directa',
            new_name='es_vendible_individualmente',
        ),
    ]
