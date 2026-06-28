"""
Catálogo farmacia: carga masiva de productos y lotes con bulk_create/bulk_update (tenant explícito).
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.utils.dateparse import parse_date

from core.models import Lote, Producto

logger = logging.getLogger('core')

PRODUCTO_BULK_FIELDS = (
    'empresa_id',
    'sucursal_id',
    'nombre',
    'sustancia_activa',
    'marca_laboratorio',
    'forma_farmaceutica',
    'concentracion',
    'presentacion',
    'precio_compra',
    'precio_publico',
    'iva_porcentaje',
    'stock',
    'stock_minimo',
    'clasificacion_sanitaria',
    'categoria',
    'es_antibiotico',
    'es_servicio',
)

LOTE_BULK_UPDATE_FIELDS = (
    'cantidad',
    'fecha_caducidad',
    'fecha_fabricacion',
    'costo_adquisicion',
    'empresa_id',
)


class CatalogoFarmaciaService:
    """Importación masiva de productos/lotes por empresa (sin ORM en la vista)."""

    @staticmethod
    def _result(http_status: int, body: Dict[str, Any]) -> Dict[str, Any]:
        return {'http_status': http_status, 'body': body}

    @staticmethod
    def _defaults_desde_payload(
        p: dict,
        empresa,
        sucursal,
    ) -> Dict[str, Any]:
        return {
            'empresa_id': empresa.pk,
            'sucursal_id': sucursal.pk if sucursal else None,
            'nombre': (p.get('nombre') or '')[:255],
            'sustancia_activa': (p.get('descripcion') or '')[:255] or None,
            'marca_laboratorio': (p.get('marca') or 'GENÉRICO')[:150],
            'forma_farmaceutica': (p.get('unidad') or 'Unidad')[:100],
            'concentracion': (p.get('concentracion') or 'N/A')[:100],
            'presentacion': (p.get('presentacion') or '1')[:100],
            'precio_compra': Decimal(str(p.get('costo', 0) or 0)),
            'precio_publico': Decimal(str(p.get('precio_publico', 0) or 0)),
            'iva_porcentaje': Decimal(str(p.get('iva_porcentaje', 0) or 0)),
            'stock': int(p.get('stock', 0) or 0),
            'stock_minimo': int(p.get('stock_minimo', 0) or 0),
            'clasificacion_sanitaria': p.get('clasificacion', 'VI'),
            'categoria': p.get('categoria', 'GENERICO'),
            'es_antibiotico': bool(p.get('es_antibiotico', False)),
            'es_servicio': bool(p.get('es_servicio', False)),
        }

    @staticmethod
    def _limpiar_catalogo_empresa(empresa) -> None:
        for lote in Lote.objects.filter(producto__empresa=empresa).iterator(chunk_size=500):
            try:
                lote.delete()
            except ProtectedError:
                pass
        for prod in Producto.objects.filter(empresa=empresa).iterator(chunk_size=500):
            try:
                prod.delete()
            except ProtectedError:
                pass

    @classmethod
    def carga_masiva_productos(
        cls,
        empresa,
        sucursal,
        productos_data: List[dict],
        *,
        limpiar: bool,
    ) -> Dict[str, Any]:
        """
        Upsert masivo por codigo_barras (único global) + lotes asociados.
        Usa bulk_create/bulk_update en lotes dentro de transaction.atomic.
        """
        if not productos_data:
            return cls._result(200, {
                'status': 'success',
                'creados': 0,
                'actualizados': 0,
                'lotes_creados': 0,
                'errores': [],
            })

        creados = 0
        actualizados = 0
        lotes_creados = 0
        errores: List[str] = []

        try:
            with transaction.atomic():
                if limpiar:
                    cls._limpiar_catalogo_empresa(empresa)

                norm_rows: List[Tuple[str, dict, int]] = []
                all_cbs: List[str] = []
                for idx, p in enumerate(productos_data):
                    try:
                        cb = (p.get('codigo_barras') or '').strip()
                        if not cb:
                            cb = f"SIN-CB-{abs(hash(p.get('nombre', ''))) % 1000000:06d}"
                        d = cls._defaults_desde_payload(p, empresa, sucursal)
                        norm_rows.append((cb, p, idx))
                        all_cbs.append(cb)
                    except Exception as e:
                        logging.getLogger(__name__).exception("Error inesperado en carga_masiva_productos (catalogo_farmacia_service.py)")
                        errores.append(f'#{idx + 1}: {e}')
                        if len(errores) > 50:
                            break

                if not norm_rows:
                    return cls._result(200, {
                        'status': 'success',
                        'creados': 0,
                        'actualizados': 0,
                        'lotes_creados': 0,
                        'errores': errores,
                    })

                unique_cbs = list(dict.fromkeys(all_cbs))
                existing_qs = Producto.objects.filter(codigo_barras__in=unique_cbs)
                by_cb = {obj.codigo_barras: obj for obj in existing_qs}

                to_create: List[Producto] = []
                to_update_ids: Dict[int, Producto] = {}

                for cb, p, idx in norm_rows:
                    try:
                        d = cls._defaults_desde_payload(p, empresa, sucursal)
                        if cb in by_cb:
                            obj = by_cb[cb]
                            for field in PRODUCTO_BULK_FIELDS:
                                setattr(obj, field, d[field])
                            if obj.pk:
                                to_update_ids[obj.pk] = obj
                            actualizados += 1
                        else:
                            obj = Producto(
                                codigo_barras=cb,
                                empresa_id=d['empresa_id'],
                                sucursal_id=d['sucursal_id'],
                                nombre=d['nombre'],
                                sustancia_activa=d['sustancia_activa'],
                                marca_laboratorio=d['marca_laboratorio'],
                                forma_farmaceutica=d['forma_farmaceutica'],
                                concentracion=d['concentracion'],
                                presentacion=d['presentacion'],
                                precio_compra=d['precio_compra'],
                                precio_publico=d['precio_publico'],
                                iva_porcentaje=d['iva_porcentaje'],
                                stock=d['stock'],
                                stock_minimo=d['stock_minimo'],
                                clasificacion_sanitaria=d['clasificacion_sanitaria'],
                                categoria=d['categoria'],
                                es_antibiotico=d['es_antibiotico'],
                                es_servicio=d['es_servicio'],
                            )
                            to_create.append(obj)
                            by_cb[cb] = obj
                            creados += 1
                    except Exception as e:
                        logging.getLogger(__name__).exception("Error inesperado en carga_masiva_productos (catalogo_farmacia_service.py)")
                        errores.append(f'#{idx + 1}: {e}')
                        if len(errores) > 50:
                            break

                to_update = list(to_update_ids.values())

                batch = 400
                if to_create:
                    Producto.objects.bulk_create(to_create, batch_size=batch)
                if to_update:
                    Producto.objects.bulk_update(to_update, fields=list(PRODUCTO_BULK_FIELDS), batch_size=batch)

                by_cb = {
                    x.codigo_barras: x
                    for x in Producto.objects.filter(codigo_barras__in=unique_cbs)
                }

                prod_ids = [o.pk for o in by_cb.values() if o.pk]
                lot_map: Dict[Tuple[int, str], Lote] = {}
                if prod_ids:
                    for lt in Lote.objects.filter(producto_id__in=prod_ids).iterator(chunk_size=1000):
                        lot_map[(lt.producto_id, lt.numero_lote)] = lt

                lote_creates_by_key: Dict[Tuple[int, str], Lote] = {}
                lote_updates_by_key: Dict[Tuple[int, str], Lote] = {}

                for cb, p, idx in norm_rows:
                    if len(errores) > 50:
                        break
                    prod = by_cb.get(cb)
                    if not prod or not prod.pk:
                        continue
                    costo_lote = Decimal(str(p.get('costo', 0) or 0)) or Decimal('0.01')
                    for lote_data in p.get('lotes', []):
                        try:
                            lote_num = (lote_data.get('numero') or '').strip()
                            fecha_cad_str = lote_data.get('caducidad', '')
                            if not lote_num or not fecha_cad_str:
                                continue
                            fecha_cad = parse_date(str(fecha_cad_str)[:10]) if fecha_cad_str else None
                            if not fecha_cad:
                                continue
                            fecha_fab_str = lote_data.get('fabricacion', '')
                            fecha_fab = parse_date(str(fecha_fab_str)[:10]) if fecha_fab_str else None
                            cant = int(lote_data.get('stock', 0) or 0)
                            key = (prod.pk, lote_num)
                            exist = lot_map.get(key)
                            if exist:
                                exist.cantidad = cant
                                exist.fecha_caducidad = fecha_cad
                                exist.fecha_fabricacion = fecha_fab
                                exist.costo_adquisicion = costo_lote
                                exist.empresa_id = prod.empresa_id
                                lote_updates_by_key[key] = exist
                            elif key in lote_creates_by_key:
                                nu = lote_creates_by_key[key]
                                nu.cantidad = cant
                                nu.fecha_caducidad = fecha_cad
                                nu.fecha_fabricacion = fecha_fab
                                nu.costo_adquisicion = costo_lote
                                nu.ubicacion_fisica = (lote_data.get('ubicacion') or '')[:150] or None
                            else:
                                lote_creates_by_key[key] = Lote(
                                    empresa_id=prod.empresa_id,
                                    producto_id=prod.pk,
                                    numero_lote=lote_num,
                                    fecha_caducidad=fecha_cad,
                                    fecha_fabricacion=fecha_fab,
                                    cantidad=cant,
                                    costo_adquisicion=costo_lote,
                                    ubicacion_fisica=(lote_data.get('ubicacion') or '')[:150] or None,
                                )
                        except Exception as e:
                            logging.getLogger(__name__).exception("Error inesperado en carga_masiva_productos (catalogo_farmacia_service.py)")
                            errores.append(f'#{idx + 1} lote: {e}')
                            if len(errores) > 50:
                                break

                lotes_creados = len(lote_creates_by_key)
                if lote_creates_by_key:
                    Lote.objects.bulk_create(
                        list(lote_creates_by_key.values()),
                        batch_size=batch,
                    )
                if lote_updates_by_key:
                    Lote.objects.bulk_update(
                        list(lote_updates_by_key.values()),
                        fields=list(LOTE_BULK_UPDATE_FIELDS),
                        batch_size=batch,
                    )

        except Exception as e:
            logger.exception('carga_masiva_productos: %s', e)
            return cls._result(500, {
                'status': 'error',
                'mensaje': str(e),
                'creados': creados,
                'actualizados': actualizados,
                'lotes_creados': lotes_creados,
                'errores': errores,
            })

        return cls._result(200, {
            'status': 'success',
            'creados': creados,
            'actualizados': actualizados,
            'lotes_creados': lotes_creados,
            'errores': errores,
        })