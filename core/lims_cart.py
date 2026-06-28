"""
Utilidades de carrito / precios para catálogo LIMS v7.5 (Analito, PerfilLims, PaqueteLims).
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db.models import Q


SEARCH_ALIASES = {
    'BH': [
        'BH',
        'BIOMETRIA HEMATICA',
        'CITOMETRIA HEMATICA',
        'CITOMETRIA HEMATICA COMPLETA',
    ],
    'QS3': ['QS3', 'QUIMICA SANGUINEA 3'],
    'QS4': ['QS4', 'QUIMICA SANGUINEA 4'],
    'QS6': ['QS6', 'QUIMICA SANGUINEA 6'],
    'QS12': ['QS12', 'QUIMICA SANGUINEA 12'],
    'QS19': ['QS19', 'QUIMICA SANGUINEA 19'],
    'QS32': ['QS32', 'QUIMICA SANGUINEA 32'],
    'EGO': ['EGO', 'EXAMEN GENERAL DE ORINA'],
}


def _d(val) -> Decimal:
    if val is None:
        return Decimal('0')
    return Decimal(str(val))


def _precio_venta_o_lista(precio_venta, costo_lista) -> Decimal:
    """
    Si existe PrecioItem pero precio_venta quedó en 0 (default del modelo),
    usar costo_lista del catálogo para no cobrar $0 por error operativo.
    """
    pv = _d(precio_venta)
    cl = _d(costo_lista)
    if pv > 0:
        return pv
    return cl


def _precio_item_analito(a, empresa=None) -> Decimal:
    from lims.models import PrecioItem

    qs = PrecioItem.objects.filter(tipo='A', analito=a, activo=True)
    if empresa is not None:
        qs = qs.filter(empresa=empresa)
    pi = qs.order_by('-fecha_actualiz').first()
    if pi:
        return _precio_venta_o_lista(pi.precio_venta, a.costo_lista)
    return _d(a.costo_lista)


def _precio_item_perfil(p, empresa=None) -> Decimal:
    from lims.models import PrecioItem

    qs = PrecioItem.objects.filter(tipo='P', perfil=p, activo=True)
    if empresa is not None:
        qs = qs.filter(empresa=empresa)
    pi = qs.order_by('-fecha_actualiz').first()
    if pi:
        return _precio_venta_o_lista(pi.precio_venta, p.costo_lista)
    return _d(p.costo_lista)


def _precio_item_paquete(q, empresa=None) -> Decimal:
    from lims.models import PrecioItem

    qs = PrecioItem.objects.filter(tipo='Q', paquete=q, activo=True)
    if empresa is not None:
        qs = qs.filter(empresa=empresa)
    pi = qs.order_by('-fecha_actualiz').first()
    if pi:
        return _precio_venta_o_lista(pi.precio_venta, q.costo_lista)
    return _d(q.costo_lista)


def detalle_orden_etiqueta(d) -> str:
    if getattr(d, 'descripcion_linea', None):
        return (d.descripcion_linea or '').strip() or '?'
    if getattr(d, 'analito_id', None):
        return d.analito.nombre
    if getattr(d, 'perfil_lims_id', None):
        return d.perfil_lims.nombre
    if getattr(d, 'paquete_lims_id', None):
        return d.paquete_lims.nombre
    return '?'


def convenio_precio_map(convenio) -> dict[str, Decimal]:
    from core.models import ConvenioPrecioLims

    m: dict[str, Decimal] = {}
    for p in ConvenioPrecioLims.objects.filter(convenio=convenio):
        if p.analito_id:
            m[f'analito:{p.analito_id}'] = p.precio_convenio
        if p.perfil_lims_id:
            m[f'perfil:{p.perfil_lims_id}'] = p.precio_convenio
        if p.paquete_lims_id:
            m[f'paquete:{p.paquete_lims_id}'] = p.precio_convenio
    return m


def parse_lims_cart_token(raw: Any) -> tuple[str | None, int | None]:
    if isinstance(raw, dict):
        t = (raw.get('lims_tipo') or raw.get('tipo') or '').lower().strip()
        pid = raw.get('id')
        if t in ('analito', 'perfil', 'paquete') and pid is not None:
            try:
                return t, int(pid)
            except (TypeError, ValueError):
                return None, None
        return None, None
    if isinstance(raw, str):
        s = raw.strip()
        if ':' in s:
            t, _, rest = s.partition(':')
            t = t.lower().strip()
            if t in ('analito', 'perfil', 'paquete'):
                try:
                    return t, int(rest.strip())
                except ValueError:
                    return None, None
    if isinstance(raw, int):
        return None, raw
    if isinstance(raw, str) and raw.isdigit():
        try:
            return None, int(raw)
        except ValueError:
            return None, None
    return None, None


def _row_analito(a, empresa=None) -> dict[str, Any]:
    px = _precio_item_analito(a, empresa=empresa)
    return {
        'tipo': 'analito',
        'analito': a,
        'perfil_lims': None,
        'paquete_lims': None,
        'descripcion_linea': a.nombre,
        'precio_base': px,
        'precio_key': f'analito:{a.id}',
    }


def _row_perfil(p, empresa=None) -> dict[str, Any]:
    px = _precio_item_perfil(p, empresa=empresa)
    return {
        'tipo': 'perfil',
        'analito': None,
        'perfil_lims': p,
        'paquete_lims': None,
        'descripcion_linea': p.nombre,
        'precio_base': px,
        'precio_key': f'perfil:{p.id}',
    }


def _row_paquete(q, empresa=None) -> dict[str, Any]:
    px = _precio_item_paquete(q, empresa=empresa)
    return {
        'tipo': 'paquete',
        'analito': None,
        'perfil_lims': None,
        'paquete_lims': q,
        'descripcion_linea': q.nombre,
        'precio_base': px,
        'precio_key': f'paquete:{q.id}',
    }


def resolve_lims_line(tipo: str, pk: int, empresa=None) -> dict[str, Any] | None:
    from lims.models import Analito, PerfilLims, PaqueteLims

    if tipo == 'analito':
        qs = Analito.objects.filter(pk=pk, activo=True)
        if empresa is not None:
            qs = qs.filter(empresa=empresa)
        a = qs.first()
        return _row_analito(a, empresa=empresa) if a else None
    if tipo == 'perfil':
        qs = PerfilLims.objects.filter(pk=pk, activo=True)
        if empresa is not None:
            qs = qs.filter(empresa=empresa)
        p = qs.first()
        return _row_perfil(p, empresa=empresa) if p else None
    if tipo == 'paquete':
        qs = PaqueteLims.objects.filter(pk=pk, activo=True)
        if empresa is not None:
            qs = qs.filter(empresa=empresa)
        q = qs.first()
        return _row_paquete(q, empresa=empresa) if q else None
    return None


def resolve_lims_cart_ids(raw_list: list, empresa=None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in raw_list:
        tipo, pk = parse_lims_cart_token(raw)
        if tipo and pk:
            row = resolve_lims_line(tipo, pk, empresa=empresa)
            if row:
                out.append(row)
            continue
        if pk is not None:
            for cand in ('analito', 'perfil', 'paquete'):
                row = resolve_lims_line(cand, pk, empresa=empresa)
                if row:
                    out.append(row)
                    break
    return out


def search_lims_catalog(
    query: str,
    empresa=None,
    limit_analitos: int = 60,
    limit_otros: int = 20,
) -> list[dict[str, Any]]:
    from lims.models import Analito, PerfilLims, PaqueteLims

    q = (query or '').strip()
    resultados: list[dict[str, Any]] = []
    query_upper = q.upper()
    query_compact = ''.join(ch for ch in query_upper if ch.isalnum())

    terms: list[str] = []
    if q:
        terms.append(q)
    alias_terms = SEARCH_ALIASES.get(query_upper) or SEARCH_ALIASES.get(query_compact) or []
    for alias in alias_terms:
        if alias not in terms:
            terms.append(alias)

    def _build_filter(*fields: str):
        if not terms:
            return Q()
        filt = Q()
        for term in terms:
            term_filter = Q()
            for field in fields:
                term_filter |= Q(**{f'{field}__icontains': term})
            filt |= term_filter
        return filt

    def _score_item(*values: str) -> tuple[int, int, int]:
        haystack = ' '.join((v or '') for v in values)
        haystack_upper = haystack.upper()
        haystack_compact = ''.join(ch for ch in haystack_upper if ch.isalnum())
        score = 0
        if query_upper and query_upper in haystack_upper:
            score += 100
        if query_compact and query_compact in haystack_compact:
            score += 120
        for alias in alias_terms:
            alias_upper = alias.upper()
            alias_compact = ''.join(ch for ch in alias_upper if ch.isalnum())
            if alias_upper and alias_upper in haystack_upper:
                score += 80
            if alias_compact and alias_compact in haystack_compact:
                score += 90
        starts = 1 if any((v or '').upper().startswith(query_upper) for v in values if query_upper) else 0
        alias_starts = 1 if any(
            any((v or '').upper().startswith(alias.upper()) for alias in alias_terms)
            for v in values
        ) else 0
        return (score, starts, alias_starts)

    aq = Analito.objects.filter(activo=True, es_vendible_individualmente=True)
    if empresa is not None:
        aq = aq.filter(empresa=empresa)
    if q:
        aq = aq.filter(_build_filter('nombre', 'codigo', 'abreviatura'))
    analitos = list(aq.order_by('departamento', 'nombre')[:limit_analitos * 3 if q else limit_analitos])
    analitos.sort(
        key=lambda a: (
            _score_item(a.codigo, a.abreviatura, a.nombre),
            a.departamento or '',
            a.nombre or '',
        ),
        reverse=True,
    )
    for a in analitos[:limit_analitos]:
        px = float(_precio_item_analito(a, empresa=empresa))
        resultados.append({
            'id': f'analito:{a.id}',
            'source': 'lims_analito',
            'lims_tipo': 'analito',
            'text': f'{a.codigo} — {a.nombre}',
            'codigo': a.codigo or '',
            'nombre': a.nombre,
            'abreviatura': a.abreviatura or '',
            'precio': px,
            'precio_base': px,
            'indicaciones': a.indicaciones or '',
            'es_perfil': False,
            'descripcion_interna': a.notas or '',
            'muestra_requerida': a.tipo_muestra or '',
            'dias_entrega': 1,
            'seccion': a.departamento or '',
        })

    pq = PerfilLims.objects.filter(activo=True)
    if empresa is not None:
        pq = pq.filter(empresa=empresa)
    if q:
        pq = pq.filter(_build_filter('nombre', 'descripcion'))
    perfiles = list(pq.order_by('nombre')[:limit_otros * 3 if q else limit_otros])
    perfiles.sort(
        key=lambda p: (
            _score_item(p.nombre, p.descripcion),
            p.nombre or '',
        ),
        reverse=True,
    )
    for p in perfiles[:limit_otros]:
        px = float(_precio_item_perfil(p, empresa=empresa))
        resultados.append({
            'id': f'perfil:{p.id}',
            'source': 'lims_perfil',
            'lims_tipo': 'perfil',
            'text': f'[Perfil] {p.nombre}',
            'codigo': '',
            'nombre': p.nombre,
            'abreviatura': '',
            'precio': px,
            'precio_base': px,
            'indicaciones': '',
            'es_perfil': True,
            'descripcion_interna': p.descripcion or '',
            'muestra_requerida': '',
            'dias_entrega': 1,
            'seccion': 'Perfil',
        })

    kq = PaqueteLims.objects.filter(activo=True)
    if empresa is not None:
        kq = kq.filter(empresa=empresa)
    if q:
        kq = kq.filter(_build_filter('nombre', 'descripcion'))
    paquetes = list(kq.order_by('nombre')[:limit_otros * 3 if q else limit_otros])
    paquetes.sort(
        key=lambda k: (
            _score_item(k.nombre, k.descripcion),
            k.nombre or '',
        ),
        reverse=True,
    )
    for k in paquetes[:limit_otros]:
        px = float(_precio_item_paquete(k, empresa=empresa))
        resultados.append({
            'id': f'paquete:{k.id}',
            'source': 'lims_paquete',
            'lims_tipo': 'paquete',
            'text': f'[Paquete] {k.nombre}',
            'codigo': '',
            'nombre': k.nombre,
            'abreviatura': '',
            'precio': px,
            'precio_base': px,
            'indicaciones': '',
            'es_perfil': True,
            'descripcion_interna': k.descripcion or '',
            'muestra_requerida': '',
            'dias_entrega': 1,
            'seccion': 'Paquete',
        })

    return resultados


def aplicar_precio_convenio(
    precio_base: Decimal,
    precio_key: str,
    precios_especiales: dict[str, Decimal],
    descuento_pct: Decimal,
) -> Decimal:
    precio = precios_especiales.get(precio_key)
    if precio is not None:
        return Decimal(str(precio)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if descuento_pct and descuento_pct > 0:
        return (
            Decimal(str(precio_base)) * (Decimal('100.00') - descuento_pct) / Decimal('100.00')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return Decimal(str(precio_base)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def precio_publico_analito(a, empresa=None) -> Decimal:
    """Precio de venta público para un analito (PrecioItem o costo_lista)."""
    return _precio_item_analito(a, empresa=empresa)
