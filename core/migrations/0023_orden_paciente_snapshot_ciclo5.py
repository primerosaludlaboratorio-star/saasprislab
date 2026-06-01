# CICLO 5: Data integrity - snapshot de paciente al momento de la orden (auditoría forense)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_detalleventa_costo_unitario_momento'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordendeservicio',
            name='paciente_nombre_snapshot',
            field=models.CharField(
                blank=True,
                help_text='Copia al crear la orden; usado en PDF y reportes históricos',
                max_length=255,
                null=True,
                verbose_name='Nombre del paciente al momento de la orden',
            ),
        ),
        migrations.AddField(
            model_name='ordendeservicio',
            name='paciente_edad_snapshot',
            field=models.IntegerField(
                blank=True,
                help_text='Edad en años al crear la orden; usada para rangos de referencia',
                null=True,
                verbose_name='Edad al momento de la orden',
            ),
        ),
        migrations.AddField(
            model_name='ordendeservicio',
            name='paciente_sexo_snapshot',
            field=models.CharField(
                blank=True,
                choices=[('M', 'Masculino'), ('F', 'Femenino'), ('I', 'Indeterminado')],
                help_text='Sexo al crear la orden; usado para rangos de referencia',
                max_length=1,
                null=True,
                verbose_name='Sexo al momento de la orden',
            ),
        ),
    ]
