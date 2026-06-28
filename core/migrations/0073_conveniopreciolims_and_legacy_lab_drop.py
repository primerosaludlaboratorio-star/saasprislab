# v1.51 — Paso 2/2: ConvenioPrecioLims, eliminación catálogo legacy (Estudio/Parametro/…)
# y ajustes asociados. Ejecutar después de 0072_sqlite_drop_legacy_unique_together.

import django.db.models.deletion
from django.db import migrations, models


def _drop_estudio_fk_column_if_exists(apps, schema_editor, table: str):
    """
    Quita estudio_id si sigue en BD. Idempotente: core.0069 ya pudo eliminarla en
    DetalleOrden; en producción evita ProgrammingError al repetir RemoveField.
    """
    conn = schema_editor.connection
    col = 'estudio_id'
    with conn.cursor() as cursor:
        if conn.vendor == 'postgresql':
            cursor.execute(
                f'ALTER TABLE {conn.ops.quote_name(table)} '
                f'DROP COLUMN IF EXISTS {conn.ops.quote_name(col)}'
            )
            return
        if conn.vendor == 'sqlite':
            cursor.execute(f'PRAGMA table_info({table})')
            names = [row[1] for row in cursor.fetchall()]
            if col not in names:
                return
            cursor.execute(f'PRAGMA index_list({table})')
            for row in cursor.fetchall():
                idx_name = row[1]
                cursor.execute(f'PRAGMA index_info({idx_name!r})')
                cols = [r[2] for r in cursor.fetchall()]
                if col in cols:
                    cursor.execute(f'DROP INDEX IF EXISTS {idx_name}')
            cursor.execute(f'ALTER TABLE {table} DROP COLUMN {col}')


def _drop_detalleorden_estudio_db(apps, schema_editor):
    _drop_estudio_fk_column_if_exists(apps, schema_editor, 'core_detalleorden')


def _drop_detallepreorden_estudio_db(apps, schema_editor):
    _drop_estudio_fk_column_if_exists(apps, schema_editor, 'core_detallepreorden')


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0072_sqlite_drop_legacy_unique_together'),
        ('lims', '0007_forense_acceso_cofepris'),
        # inventario.0001 crea FK a core.Estudio; 0004 la migra a lims.Analito y la quita.
        # Sin este enlace, el planificador puede aplicar core.0073 antes que inventario.0001
        # y falla: Related model 'core.estudio' cannot be resolved.
        ('inventario', '0007_notificacion_qc_westgard_tipo'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConvenioPrecioLims',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('precio_convenio', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Precio Convenio')),
            ],
            options={
                'verbose_name': 'Precio LIMS por Convenio',
                'verbose_name_plural': 'Precios LIMS por Convenio',
            },
        ),
        migrations.RemoveField(
            model_name='convenioprecioestudio',
            name='convenio',
        ),
        migrations.RemoveField(
            model_name='convenioprecioestudio',
            name='estudio',
        ),
        migrations.RemoveField(
            model_name='estudio',
            name='componentes',
        ),
        migrations.RemoveField(
            model_name='estudio',
            name='seccion',
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='detalleorden', name='estudio'),
            ],
            database_operations=[
                migrations.RunPython(_drop_detalleorden_estudio_db, _noop_reverse),
            ],
        ),
        migrations.RemoveField(
            model_name='parametro',
            name='estudio',
        ),
        migrations.RemoveField(
            model_name='parametro',
            name='desactivado_por',
        ),
        migrations.RemoveField(
            model_name='rangoreferencia',
            name='parametro',
        ),
        migrations.RemoveField(
            model_name='rangoreferencia',
            name='reemplazado_por',
        ),
        migrations.AlterModelOptions(
            name='resultadoparametro',
            options={'ordering': ['analito__nombre'], 'verbose_name': 'Resultado de Parámetro', 'verbose_name_plural': 'Resultados de Parámetros'},
        ),
        migrations.RemoveConstraint(
            model_name='cierrediaconsolidado',
            name='unique_cierre_dia_sucursal',
        ),
        migrations.RenameIndex(
            model_name='catalogocie10',
            new_name='core_catalo_codigo_77eb2b_idx',
            old_name='core_cie10_cod_act_idx',
        ),
        migrations.RenameIndex(
            model_name='catalogocie10',
            new_name='core_catalo_categor_deae11_idx',
            old_name='core_cie10_cat_act_idx',
        ),
        migrations.RenameIndex(
            model_name='expedientenotasha',
            new_name='core_expedi_empresa_e2455f_idx',
            old_name='core_exp_sha_emp_pac_idx',
        ),
        migrations.RenameIndex(
            model_name='expedientenotasha',
            new_name='core_expedi_hash_sh_7263d7_idx',
            old_name='core_exp_sha_hash_idx',
        ),
        migrations.RenameIndex(
            model_name='expedientenotasha',
            new_name='core_expedi_estado__2d446a_idx',
            old_name='core_exp_sha_est_fir_idx',
        ),
        migrations.RenameIndex(
            model_name='hashraizdiario',
            new_name='core_hashra_fecha_8da07a_idx',
            old_name='core_hash_raiz_fecha_idx',
        ),
        migrations.RenameIndex(
            model_name='hashraizdiario',
            new_name='core_hashra_año_74a24b_idx',
            old_name='core_hash_raiz_año_mes_idx',
        ),
        migrations.RenameIndex(
            model_name='hashraizdiario',
            new_name='core_hashra_timesta_752ad5_idx',
            old_name='core_hash_raiz_envio_idx',
        ),
        migrations.RenameIndex(
            model_name='notaclinicasellar',
            new_name='core_notacl_estado__18bcf0_idx',
            old_name='core_sello_est_ts_idx',
        ),
        migrations.RenameIndex(
            model_name='notaclinicasellar',
            new_name='core_notacl_token_v_8bdfe2_idx',
            old_name='core_sello_token_idx',
        ),
        migrations.RenameIndex(
            model_name='notaclinicasellar',
            new_name='core_notacl_folio_u_db440d_idx',
            old_name='core_sello_folio_idx',
        ),
        migrations.RenameIndex(
            model_name='notaclinicasellar',
            new_name='core_notacl_ip_orig_43415f_idx',
            old_name='core_sello_ip_ts_idx',
        ),
        migrations.AlterUniqueTogether(
            name='detallepreorden',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='detallepreorden',
            name='analito',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='detalles_preordenes_core', to='lims.analito', verbose_name='Analito'),
        ),
        migrations.AddField(
            model_name='detallepreorden',
            name='descripcion_linea',
            field=models.CharField(blank=True, default='', max_length=300),
        ),
        migrations.AddField(
            model_name='detallepreorden',
            name='paquete_lims',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='detalles_preordenes_core', to='lims.paquetelims', verbose_name='Paquete LIMS'),
        ),
        migrations.AddField(
            model_name='detallepreorden',
            name='perfil_lims',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='detalles_preordenes_core', to='lims.perfillims', verbose_name='Perfil LIMS'),
        ),
        migrations.AlterUniqueTogether(
            name='cierrediaconsolidado',
            unique_together={('empresa', 'sucursal', 'fecha')},
        ),
        migrations.AddField(
            model_name='conveniopreciolims',
            name='analito',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='precios_convenio', to='lims.analito'),
        ),
        migrations.AddField(
            model_name='conveniopreciolims',
            name='convenio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='precios_lims', to='core.convenio'),
        ),
        migrations.AddField(
            model_name='conveniopreciolims',
            name='paquete_lims',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='precios_convenio', to='lims.paquetelims'),
        ),
        migrations.AddField(
            model_name='conveniopreciolims',
            name='perfil_lims',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='precios_convenio', to='lims.perfillims'),
        ),
        migrations.DeleteModel(
            name='ConvenioPrecioEstudio',
        ),
        migrations.DeleteModel(
            name='SeccionLaboratorio',
        ),
        migrations.DeleteModel(
            name='Parametro',
        ),
        migrations.DeleteModel(
            name='RangoReferencia',
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='detallepreorden', name='estudio'),
            ],
            database_operations=[
                migrations.RunPython(_drop_detallepreorden_estudio_db, _noop_reverse),
            ],
        ),
        migrations.DeleteModel(
            name='Estudio',
        ),
    ]
