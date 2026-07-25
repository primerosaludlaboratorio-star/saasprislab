from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('farmacia', '0009_cierreturnofarmacia_cerrado_por'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='aperturacaja',
            constraint=models.UniqueConstraint(
                condition=models.Q(activa=True),
                fields=('empresa', 'sucursal'),
                name='unique_apertura_activa_empresa_sucursal',
                violation_error_message='Ya existe una caja activa para esta empresa y sucursal.',
            ),
        ),
    ]
