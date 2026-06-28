# ACAYUCAN v7.5 — ResultadoParametro: parametro (legacy) -> analito LIMS
# SQLite y PostgreSQL: quita unique (orden, parametro), añade analito, backfill, elimina parametro.
# atomic=False: Postgres rechaza ALTER tras RunPython con UPDATE/DELETE en la misma transacción
# ("cannot ALTER TABLE ... pending trigger events"). Cada operación va en su propia transacción.

from collections import defaultdict

import django.db.models.deletion
from django.db import migrations, models


def _placeholder_analito(apps, schema_editor):
    """Un analito mínimo para desbloquear 0058 cuando prod aún no tiene catálogo LIMS."""
    Analito = apps.get_model('lims', 'Analito')
    obj, _ = Analito.objects.get_or_create(
        codigo='__PRISLAB_MIG_0058__',
        defaults={
            'abreviatura': 'MIG0058',
            'nombre': 'Placeholder migración 0058 — ejecutar import/ensamblaje LIMS y revisar resultados',
            'departamento': 'Sistema',
            'activo': True,
        },
    )
    return obj


def _fill_analito_from_parametro(apps, schema_editor):
    Analito = apps.get_model('lims', 'Analito')
    RP = apps.get_model('core', 'ResultadoParametro')
    Parametro = apps.get_model('core', 'Parametro')
    if not RP.objects.exists():
        return
    fallback = Analito.objects.filter(activo=True).order_by('pk').first()
    if not fallback:
        # BD sin catálogo previo: sin esto migrate aborta y el servicio nunca escucha :8080.
        fallback = _placeholder_analito(apps, schema_editor)
    for rp in RP.objects.all().iterator():
        param_id = getattr(rp, 'parametro_id', None)
        abrev = cod_int = None
        if param_id:
            p = Parametro.objects.filter(pk=param_id).first()
            if p:
                abrev = p.abreviatura
                cod_int = p.codigo_interfaz
        analito = None
        if param_id:
            analito = Analito.objects.filter(id_legacy=param_id).first()
        if analito is None and cod_int:
            c = (cod_int or '').strip()
            if c:
                analito = Analito.objects.filter(codigo=c).first()
        if analito is None and abrev:
            b = (abrev or '').strip()
            if b:
                analito = Analito.objects.filter(abreviatura__iexact=b).first()
        if analito is None:
            analito = fallback
        RP.objects.filter(pk=rp.pk).update(analito_id=analito.pk)

    # Varios Parametro legacy pueden mapear al mismo Analito → violaría unique (orden, analito).
    Hist = apps.get_model('core', 'HistorialResultados')
    groups = defaultdict(list)
    for row in RP.objects.all().values('id', 'orden_id', 'analito_id'):
        key = (row['orden_id'], row['analito_id'])
        groups[key].append(row['id'])
    for _key, ids in groups.items():
        if len(ids) <= 1:
            continue
        ids.sort()
        keeper, losers = ids[0], ids[1:]
        Hist.objects.filter(resultado_parametro_id__in=losers).update(
            resultado_parametro_id=keeper
        )
        RP.objects.filter(pk__in=losers).delete()


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('core', '0057_gastocaja_documento_adjunto_acayucan'),
        ('lims', '0006_escudo_clinico_v114'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='resultadoparametro',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='resultadoparametro',
            name='analito',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='resultados_core',
                to='lims.analito',
                verbose_name='Analito LIMS',
            ),
        ),
        migrations.RunPython(_fill_analito_from_parametro, _noop_reverse),
        migrations.RemoveField(
            model_name='resultadoparametro',
            name='parametro',
        ),
        migrations.AlterField(
            model_name='resultadoparametro',
            name='analito',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='resultados_core',
                to='lims.analito',
                verbose_name='Analito LIMS',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='resultadoparametro',
            unique_together={('orden', 'analito')},
        ),
    ]
