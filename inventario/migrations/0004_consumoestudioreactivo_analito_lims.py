# ConsumoEstudioReactivo: estudio (core) -> analito (lims).
#
# IMPORTANTE (Dia D): NO se asigna el primer Analito por PK como parche ciego.
# Se mapea core.Estudio (codigo, nombre) -> lims.Analito. Si quedan filas sin mapeo, FALLA.

import django.db.models.deletion
from django.db import connection
from django.db.models import Q
from django.db import migrations, models
import logging


def _estudio_meta_from_db(estudio_ids):
    if not estudio_ids:
        return {}
    ids = sorted({int(x) for x in estudio_ids if x is not None})
    if not ids:
        return {}
    table = 'core_estudio'
    placeholders = ','.join(['%s'] * len(ids))
    sql = f'SELECT id, codigo, nombre FROM {table} WHERE id IN ({placeholders})'
    out = {}
    with connection.cursor() as cur:
        try:
            cur.execute(sql, ids)
            for row in cur.fetchall():
                eid, codigo, nombre = row[0], row[1] or '', row[2] or ''
                out[int(eid)] = {'codigo': str(codigo).strip(), 'nombre': str(nombre).strip()}
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en _estudio_meta_from_db (0004_consumoestudioreactivo_analito_lims.py)")
            logging.getLogger(__name__).exception("Error inesperado en _estudio_meta_from_db (0004_consumoestudioreactivo_analito_lims.py)")
            return {}
    return out


def _resolver_analito(Analito, codigo, nombre):
    codigo = (codigo or '').strip()
    nombre = (nombre or '').strip()
    if codigo:
        aid = (
            Analito.objects.filter(Q(codigo__iexact=codigo) | Q(abreviatura__iexact=codigo))
            .values_list('pk', flat=True)
            .first()
        )
        if aid:
            return aid
    if nombre:
        aid = Analito.objects.filter(nombre__iexact=nombre).values_list('pk', flat=True).first()
        if aid:
            return aid
    return None


def _asignar_analito_desde_estudio(apps, schema_editor):
    Consumo = apps.get_model('inventario', 'ConsumoEstudioReactivo')
    Analito = apps.get_model('lims', 'Analito')

    if not Analito.objects.exists():
        if Consumo.objects.filter(analito_id__isnull=True).exists():
            raise RuntimeError(
                'inventario.0004: hay filas en ConsumoEstudioReactivo pero lims.Analito esta vacio. '
                'Poblar LIMS antes de migrar.'
            )
        return

    Estudio = None
    try:
        Estudio = apps.get_model('core', 'Estudio')
    except LookupError:
        Estudio = None

    pendientes = list(
        Consumo.objects.filter(analito_id__isnull=True).values_list('pk', 'estudio_id', 'empresa_id', 'reactivo_id')
    )
    if not pendientes:
        return

    estudio_ids = [t[1] for t in pendientes if t[1]]
    meta_sql = _estudio_meta_from_db(estudio_ids)

    unmapped = []

    for consumo_pk, estudio_id, empresa_id, reactivo_id in pendientes:
        codigo, nombre = '', ''
        if Estudio is not None and estudio_id:
            try:
                est = Estudio.objects.get(pk=estudio_id)
                codigo = (getattr(est, 'codigo', None) or '').strip()
                nombre = (getattr(est, 'nombre', None) or '').strip()
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en _asignar_analito_desde_estudio (0004_consumoestudioreactivo_analito_lims.py)")
                logging.getLogger(__name__).exception("Error inesperado en _asignar_analito_desde_estudio (0004_consumoestudioreactivo_analito_lims.py)")
                blob = meta_sql.get(int(estudio_id)) if estudio_id else None
                if blob:
                    codigo, nombre = blob['codigo'], blob['nombre']
        elif estudio_id:
            blob = meta_sql.get(int(estudio_id))
            if blob:
                codigo, nombre = blob['codigo'], blob['nombre']

        aid = _resolver_analito(Analito, codigo, nombre)
        if aid:
            Consumo.objects.filter(pk=consumo_pk).update(analito_id=aid)
        else:
            unmapped.append(
                {
                    'consumo_pk': consumo_pk,
                    'estudio_id': estudio_id,
                    'empresa_id': empresa_id,
                    'reactivo_id': reactivo_id,
                    'codigo_estudio': codigo or None,
                    'nombre_estudio': nombre or None,
                }
            )

    if unmapped:
        muestra = unmapped[:25]
        raise RuntimeError(
            'inventario.0004: no se pudo mapear estudio->lims.Analito para '
            f'{len(unmapped)} fila(s). Ajuste codigos/nombres en LIMS o core_estudio. Muestra: {muestra}'
        )


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0003_salidaanaliticalab_idempotency_key'),
        ('lims', '0006_escudo_clinico_v114'),
        ('core', '0048_auditoria_model_base_catalogo_resultados'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='consumoestudioreactivo',
            name='inventario_consumo_estudio_reactivo_uniq',
        ),
        migrations.AddField(
            model_name='consumoestudioreactivo',
            name='analito',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='consumos_reactivos',
                to='lims.analito',
                verbose_name='Analito LIMS',
            ),
        ),
        migrations.RunPython(_asignar_analito_desde_estudio, _noop),
        migrations.RemoveField(
            model_name='consumoestudioreactivo',
            name='estudio',
        ),
        migrations.AlterField(
            model_name='consumoestudioreactivo',
            name='analito',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='consumos_reactivos',
                to='lims.analito',
                verbose_name='Analito LIMS',
            ),
        ),
        migrations.AddConstraint(
            model_name='consumoestudioreactivo',
            constraint=models.UniqueConstraint(
                fields=['empresa', 'analito', 'reactivo'],
                name='inventario_consumo_estudio_reactivo_uniq',
            ),
        ),
    ]