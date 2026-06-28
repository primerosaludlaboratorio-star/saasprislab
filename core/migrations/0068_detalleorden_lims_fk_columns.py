# DetalleOrden: columnas LIMS v7.5 (analito / perfil / paquete / descripcion_linea) en SQLite y Postgres.
# Algunas bases creadas solo con estudio_id legacy carecían de estos campos; el ORM y el motor PDF
# usan select_related('analito', ...) y fallaban con OperationalError.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lims', '0007_forense_acceso_cofepris'),
        ('core', '0067_resultadoparametro_ia_ethics_p18'),
    ]

    operations = [
        migrations.AddField(
            model_name='detalleorden',
            name='descripcion_linea',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Texto mostrado en ticket/PDF si el item es perfil o paquete.',
                max_length=300,
                verbose_name='Descripcion (snapshot)',
            ),
        ),
        migrations.AddField(
            model_name='detalleorden',
            name='analito',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='detalles_ordenes_core',
                to='lims.analito',
                verbose_name='Analito',
            ),
        ),
        migrations.AddField(
            model_name='detalleorden',
            name='perfil_lims',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='detalles_ordenes_core',
                to='lims.perfillims',
                verbose_name='Perfil LIMS',
            ),
        ),
        migrations.AddField(
            model_name='detalleorden',
            name='paquete_lims',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='detalles_ordenes_core',
                to='lims.paquetelims',
                verbose_name='Paquete LIMS',
            ),
        ),
    ]
