"""
Blindaje de datos clínicos: on_delete CASCADE → PROTECT/SET_NULL.
Previene eliminación en cascada de registros médicos, financieros y de auditoría.
Agrega índices Meta pendientes en Paciente.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_signosvitales_nullable_optional'),
    ]

    operations = [
        # =====================================================================
        # VENTAS Y FINANZAS
        # =====================================================================
        migrations.AlterField(
            model_name='venta',
            name='usuario',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to=settings.AUTH_USER_MODEL,
                verbose_name='Cajero',
            ),
        ),
        migrations.AlterField(
            model_name='detalleventa',
            name='producto',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='core.producto',
            ),
        ),
        migrations.AlterField(
            model_name='pagoorden',
            name='orden',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pagos_realizados',
                to='core.ordendeservicio',
                verbose_name='Orden de Servicio',
            ),
        ),
        migrations.AlterField(
            model_name='devolucionventa',
            name='sucursal',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='devoluciones_forenses',
                to='core.sucursal',
            ),
        ),
        # =====================================================================
        # INVENTARIO
        # =====================================================================
        migrations.AlterField(
            model_name='ajusteinventario',
            name='producto',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='core.producto',
            ),
        ),
        migrations.AlterField(
            model_name='ajusteinventario',
            name='lote',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='core.lote',
            ),
        ),
        # =====================================================================
        # LABORATORIO: RESULTADOS Y TRAZABILIDAD
        # =====================================================================
        migrations.AlterField(
            model_name='resultadoparametro',
            name='orden',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='resultados',
                to='core.ordendeservicio',
                verbose_name='Orden de Servicio',
            ),
        ),
        migrations.AlterField(
            model_name='resultadoparametro',
            name='parametro',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='core.parametro',
                verbose_name='Parámetro',
            ),
        ),
        migrations.AlterField(
            model_name='historialresultados',
            name='resultado_parametro',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='historial_cambios',
                to='core.resultadoparametro',
                verbose_name='Resultado Modificado',
            ),
        ),
        # =====================================================================
        # AUDITORÍA FORENSE
        # =====================================================================
        migrations.AlterField(
            model_name='auditlog',
            name='empresa',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='logs_auditoria',
                to='core.empresa',
            ),
        ),
        # =====================================================================
        # EXPEDIENTE CLÍNICO: HISTORIA CLÍNICA Y ANTECEDENTES
        # =====================================================================
        migrations.AlterField(
            model_name='historiaclinica',
            name='paciente',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='historia_clinica',
                to='core.paciente',
            ),
        ),
        migrations.AlterField(
            model_name='antecedente',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='antecedentes',
                to='core.paciente',
            ),
        ),
        migrations.AlterField(
            model_name='notaclinicasoap',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='notas_clinicas',
                to='core.paciente',
            ),
        ),
        migrations.AlterField(
            model_name='logaccesoexpediente',
            name='historia_clinica',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='logs_acceso',
                to='core.historiaclinica',
            ),
        ),
        # =====================================================================
        # CITAS MÉDICAS
        # =====================================================================
        migrations.AlterField(
            model_name='citamedica',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='citas',
                to='core.paciente',
            ),
        ),
        migrations.AlterField(
            model_name='citamedica',
            name='medico',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='citas',
                to='core.medico',
            ),
        ),
        # =====================================================================
        # SIGNOS VITALES
        # =====================================================================
        migrations.AlterField(
            model_name='signosvitales',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='signos_vitales',
                to='core.paciente',
            ),
        ),
        # =====================================================================
        # CONSULTA MÉDICA (SOAP)
        # =====================================================================
        migrations.AlterField(
            model_name='consultamedica',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='consultas',
                to='core.paciente',
            ),
        ),
        migrations.AlterField(
            model_name='consultamedica',
            name='medico',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='consultas',
                to='core.medico',
            ),
        ),
        migrations.AlterField(
            model_name='historialcambiosconsulta',
            name='consulta',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='historial_cambios',
                to='core.consultamedica',
            ),
        ),
        # =====================================================================
        # CERTIFICADOS MÉDICOS
        # =====================================================================
        migrations.AlterField(
            model_name='certificadomedico',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='certificados',
                to='core.paciente',
            ),
        ),
        migrations.AlterField(
            model_name='certificadomedico',
            name='medico',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='certificados',
                to='core.medico',
            ),
        ),
        # =====================================================================
        # ESTUDIOS DE IMAGEN
        # =====================================================================
        migrations.AlterField(
            model_name='estudioimagen',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='estudios_imagen',
                to='core.paciente',
            ),
        ),
        # =====================================================================
        # CONSENTIMIENTO INFORMADO
        # =====================================================================
        migrations.AlterField(
            model_name='consentimientoinformado',
            name='paciente',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='consentimientos',
                to='core.paciente',
            ),
        ),
        migrations.AlterField(
            model_name='consentimientoinformado',
            name='orden',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='consentimiento',
                to='core.ordendeservicio',
            ),
        ),
        # =====================================================================
        # ÍNDICES DE BÚSQUEDA EN PACIENTE (Meta.indexes)
        # =====================================================================
        migrations.AddIndex(
            model_name='paciente',
            index=models.Index(fields=['nombre_completo'], name='core_pacien_nombre__3dc2ec_idx'),
        ),
        migrations.AddIndex(
            model_name='paciente',
            index=models.Index(fields=['telefono'], name='core_pacien_telefon_357674_idx'),
        ),
        migrations.AddIndex(
            model_name='paciente',
            index=models.Index(fields=['nombres'], name='core_pacien_nombres_a2350b_idx'),
        ),
        migrations.AddIndex(
            model_name='paciente',
            index=models.Index(fields=['apellido_paterno'], name='core_pacien_apellid_950393_idx'),
        ),
    ]
