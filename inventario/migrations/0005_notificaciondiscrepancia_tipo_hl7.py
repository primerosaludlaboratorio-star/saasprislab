# Punto 13 — tipos War Room para HL7

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0004_consumoestudioreactivo_analito_lims'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificaciondiscrepancia',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('OC_DISCREPANCIA', 'Discrepancia en Recepcion de OC'),
                    ('TRASPASO_DISCREPANCIA', 'Discrepancia en Traspaso Recibido'),
                    ('STOCK_CRITICO', 'Stock Critico Detectado'),
                    ('LOTE_CADUCADO', 'Lote Caducado en Almacen'),
                    ('HL7_MAPEO', 'HL7 — error de mapeo a LIMS'),
                    ('HL7_CUARENTENA', 'HL7 — cuarentena (unidad/valor)'),
                ],
                max_length=30,
                verbose_name='Tipo',
            ),
        ),
    ]
