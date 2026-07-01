# Generated migration for Multi-Sucursal Architecture
# This migration converts Usuario.sucursal from FK (1-to-1) to M2M (many-to-many)
# via the Usuario_Sucursal through table, enabling users to access multiple branches.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0081_make_mensajeinterno_empresa_required'),
    ]

    operations = [
        # 1. Create Usuario_Sucursal model (through table)
        migrations.CreateModel(
            name='Usuario_Sucursal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activa', models.BooleanField(default=True, help_text='Si es False, el usuario no accede a esta sucursal aunque esté en M2M.', verbose_name='Asignación Activa')),
                ('fecha_asignacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Asignación')),
                ('fecha_vencimiento', models.DateTimeField(blank=True, help_text='Si se establece, la asignación vence automáticamente en esa fecha.', null=True, verbose_name='Fecha de Vencimiento')),
                ('sucursal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='asignaciones_usuario', to='core.sucursal', verbose_name='Sucursal')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='asignaciones_sucursal', to='core.usuario', verbose_name='Usuario')),
            ],
            options={
                'verbose_name': 'Asignación Usuario-Sucursal',
                'verbose_name_plural': 'Asignaciones Usuario-Sucursal',
                'app_label': 'core',
            },
        ),

        # 2. Add unique constraint on Usuario_Sucursal
        migrations.AlterUniqueTogether(
            name='usuario_sucursal',
            unique_together={('usuario', 'sucursal')},
        ),

        # 3. Add indexes on Usuario_Sucursal for performance
        migrations.AddIndex(
            model_name='usuario_sucursal',
            index=models.Index(fields=['usuario', 'activa'], name='core_usuari_usuario_idx'),
        ),
        migrations.AddIndex(
            model_name='usuario_sucursal',
            index=models.Index(fields=['sucursal', 'activa'], name='core_usuari_sucursa_idx'),
        ),

        # La remoción de la FK legacy y el alta del M2M se hacen en 0083,
        # después del backfill, para que la migración de datos tenga acceso
        # al campo histórico usuario.sucursal.
    ]
