"""
Blindaje de datos clínicos en consultorio: on_delete CASCADE → PROTECT.
Previene eliminación en cascada de registros de pacientes, consultas,
encuestas, seguimientos y cobros del módulo consultorio.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('consultorio', '0007_alter_consultamedica_options_and_more'),
        ('core', '0027_clinical_data_protection'),
    ]

    operations = [
        # =====================================================================
        # AGENDA Y CITAS
        # =====================================================================
        migrations.AlterField(
            model_name='agendacita',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='citas_consultorio',
                to='core.paciente',
            ),
        ),
        # =====================================================================
        # CONSULTA MÉDICA (LEGACY)
        # =====================================================================
        migrations.AlterField(
            model_name='consultamedica',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='consultas_medicas',
                to='core.paciente',
            ),
        ),
        # =====================================================================
        # NOTA MÉDICA
        # =====================================================================
        migrations.AlterField(
            model_name='notamedica',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='notas_medicas',
                to='core.paciente',
            ),
        ),
        # =====================================================================
        # ARCHIVOS ADJUNTOS
        # =====================================================================
        migrations.AlterField(
            model_name='archivoadjuntoconsulta',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='archivos_adjuntos',
                to='core.paciente',
                verbose_name='Paciente',
            ),
        ),
        # =====================================================================
        # LISTA DE ESPERA
        # =====================================================================
        migrations.AlterField(
            model_name='listaespera',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='espera_consultorio',
                to='core.paciente',
            ),
        ),
        # =====================================================================
        # ENCUESTA DE SATISFACCIÓN (NPS)
        # =====================================================================
        migrations.AlterField(
            model_name='encuestasatisfaccion',
            name='consulta',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='encuesta_satisfaccion_consultorio',
                to='core.consultamedica',
            ),
        ),
        migrations.AlterField(
            model_name='encuestasatisfaccion',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='core.paciente',
            ),
        ),
        # =====================================================================
        # SEGUIMIENTO DE TRATAMIENTO
        # =====================================================================
        migrations.AlterField(
            model_name='seguimientotratamiento',
            name='consulta',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='seguimientos_consultorio',
                to='core.consultamedica',
            ),
        ),
        migrations.AlterField(
            model_name='seguimientotratamiento',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='seguimientos_tratamiento',
                to='core.paciente',
            ),
        ),
        # =====================================================================
        # COBROS DE CONSULTORIO
        # =====================================================================
        migrations.AlterField(
            model_name='cobroconsulta',
            name='consulta',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='cobros_consultorio',
                to='core.consultamedica',
                verbose_name='Consulta vinculada',
            ),
        ),
        migrations.AlterField(
            model_name='cobroconsulta',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='cobros_consultorio',
                to='core.paciente',
            ),
        ),
    ]
