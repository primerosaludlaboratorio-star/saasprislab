from django.db import migrations


class Migration(migrations.Migration):
    """Retira modelos legacy del estado Django sin borrar evidencia histórica."""

    dependencies = [
        ('consultorio', '0009_reporteultrasonido_imagenultrasonido_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='Somatometria'),
                migrations.DeleteModel(name='ConsultaMedica'),
            ],
        ),
    ]
