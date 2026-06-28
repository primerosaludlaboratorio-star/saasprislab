"""
Agrega campos separados nombres, apellido_paterno, apellido_materno al modelo Paciente.
Permite mejor control al ingresar datos de pacientes.
nombre_completo se mantiene para retrocompatibilidad y se auto-genera en save().
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_consentimientoinformado'),
    ]

    operations = [
        migrations.AddField(
            model_name='paciente',
            name='nombres',
            field=models.CharField(blank=True, default='', help_text='Nombre(s) de pila del paciente', max_length=150, verbose_name='Nombre(s)'),
        ),
        migrations.AddField(
            model_name='paciente',
            name='apellido_paterno',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='Apellido Paterno'),
        ),
        migrations.AddField(
            model_name='paciente',
            name='apellido_materno',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='Apellido Materno'),
        ),
    ]
