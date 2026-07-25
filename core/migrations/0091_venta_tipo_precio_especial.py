from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0090_empresa_nombre_asistente_ia'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='tipo_precio_especial',
            field=models.CharField(
                blank=True,
                choices=[
                    ('PERSONAL', 'Precio de costo: personal'),
                    ('FAMILIAR', 'Precio de costo: familiar de personal'),
                ],
                default='',
                help_text='Distingue precio de costo autorizado de una cortesía gratuita.',
                max_length=20,
                verbose_name='Tipo de precio especial',
            ),
        ),
        migrations.AlterField(
            model_name='venta',
            name='motivo_cortesia',
            field=models.CharField(
                blank=True,
                choices=[
                    ('MEDICO', 'Médico / Personal de Salud'),
                    ('PACIENTE', 'Cortesía a paciente'),
                    ('COLABORADOR', 'Colaborador Interno'),
                    ('VULNERABILIDAD', 'Vulnerabilidad Alta'),
                    ('OTRO', 'Otro'),
                ],
                max_length=50,
                null=True,
                verbose_name='Motivo de Cortesía',
            ),
        ),
    ]
