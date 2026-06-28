import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0016_convenio_cuentaporcobrar_notacredito'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReglaNegocio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200, verbose_name='Nombre de la Regla')),
                ('codigo', models.CharField(max_length=100, unique=True, verbose_name='Codigo interno')),
                ('descripcion', models.TextField(blank=True)),
                ('categoria', models.CharField(choices=[('PAGO', 'Pagos y Cobranza'), ('LABORATORIO', 'Laboratorio'), ('FARMACIA', 'Farmacia'), ('SEGURIDAD', 'Seguridad'), ('ENVIO', 'Envio de Resultados'), ('INVENTARIO', 'Inventario'), ('GENERAL', 'General')], default='GENERAL', max_length=20)),
                ('tipo', models.CharField(choices=[('BLOQUEO', 'Bloquea accion'), ('ALERTA', 'Muestra alerta'), ('AUTOMATICA', 'Se ejecuta automaticamente')], default='BLOQUEO', max_length=20)),
                ('activa', models.BooleanField(default=True, verbose_name='Activa')),
                ('parametros', models.JSONField(blank=True, default=dict)),
                ('prioridad', models.IntegerField(default=10)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reglas_negocio', to='core.empresa')),
                ('modificado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Regla de Negocio',
                'verbose_name_plural': 'Reglas de Negocio',
                'ordering': ['categoria', 'prioridad'],
            },
        ),
        migrations.CreateModel(
            name='EjecucionRegla',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resultado', models.BooleanField(verbose_name='Paso la validacion')),
                ('mensaje', models.TextField(blank=True)),
                ('datos_contexto', models.JSONField(blank=True, default=dict)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('regla', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ejecuciones', to='reglas_negocio.reglanegocio')),
                ('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Ejecucion de Regla',
                'verbose_name_plural': 'Ejecuciones de Reglas',
                'ordering': ['-fecha'],
            },
        ),
    ]
