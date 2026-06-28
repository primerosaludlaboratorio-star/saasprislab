# CICLO 7: Stress Test, Concurrencia e Índices - Índices de rendimiento
# Mejora consultas por fecha, estado, búsqueda por nombre/código y PEPS.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_orden_paciente_snapshot_ciclo5'),
    ]

    operations = [
        # Producto: búsqueda por nombre (PDV, listados)
        migrations.AlterField(
            model_name='producto',
            name='nombre',
            field=models.CharField(db_index=True, max_length=255, verbose_name='Nombre Comercial'),
        ),
        # Lote: orden PEPS por fecha_caducidad
        migrations.AlterField(
            model_name='lote',
            name='fecha_caducidad',
            field=models.DateField(db_index=True, verbose_name='Fecha de Caducidad'),
        ),
        # Paciente: búsqueda por nombres y apellido
        migrations.AddIndex(
            model_name='paciente',
            index=models.Index(fields=['nombres'], name='core_pacien_nombres_idx'),
        ),
        migrations.AddIndex(
            model_name='paciente',
            index=models.Index(fields=['apellido_paterno'], name='core_pacien_apellido_idx'),
        ),
        # OrdenDeServicio: filtros por fecha y estado (worklist, dashboards, cortes)
        migrations.AddIndex(
            model_name='ordendeservicio',
            index=models.Index(fields=['fecha_creacion'], name='core_ordend_fecha_c_idx'),
        ),
        migrations.AddIndex(
            model_name='ordendeservicio',
            index=models.Index(fields=['estado'], name='core_ordend_estado_idx'),
        ),
        migrations.AddIndex(
            model_name='ordendeservicio',
            index=models.Index(fields=['empresa', 'fecha_creacion'], name='core_ordend_empresa_f_idx'),
        ),
        migrations.AddIndex(
            model_name='ordendeservicio',
            index=models.Index(fields=['empresa', 'estado'], name='core_ordend_empresa_e_idx'),
        ),
        # Venta: filtros por fecha (corte, dashboards)
        migrations.AddIndex(
            model_name='venta',
            index=models.Index(fields=['fecha'], name='core_venta_fecha_idx'),
        ),
        migrations.AddIndex(
            model_name='venta',
            index=models.Index(fields=['empresa', 'fecha'], name='core_venta_empresa_f_idx'),
        ),
        migrations.AddIndex(
            model_name='venta',
            index=models.Index(fields=['empresa', 'estado', 'fecha'], name='core_venta_empresa_e_idx'),
        ),
        # PagoOrden: corte por fecha
        migrations.AddIndex(
            model_name='pagoorden',
            index=models.Index(fields=['fecha_pago'], name='core_pagoord_fecha_p_idx'),
        ),
        migrations.AddIndex(
            model_name='pagoorden',
            index=models.Index(fields=['orden', '-fecha_pago'], name='core_pagoord_orden_f_idx'),
        ),
    ]
