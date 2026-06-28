"""
LIMS v7.5 — Nivel 4: PrecioItem

1) Si existe `datos_lims/Tarifa_estudios de laboratorio.csv`, actualiza
   `costo_lista` de Analito / PerfilLims / PaqueteLims desde la tarifa
   original de PRISLAB.
2) Puebla / actualiza `PrecioItem` desde `costo_lista` de cada entidad:

   - Analito con es_vendible_individualmente=True y activo
   - Todos los PerfilLims activos
   - Todos los PaqueteLims activos

Uso:
  python manage.py sincronizar_precios_lims
  python manage.py sincronizar_precios_lims --dry-run
"""
import csv
import os
import re
import unicodedata
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Empresa
from core.tenant import clear_current_empresa, set_current_empresa, tenant_bypass
from core.utils.default_empresa import resolve_default_empresa_sistema
from lims.models import Analito, PaqueteLims, PerfilLims, PrecioItem
import logging


BASE_DIR = getattr(
    settings,
    'BASE_DIR',
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ),
)
CSV_TARIFA = os.path.join(BASE_DIR, 'datos_lims', 'Tarifa_estudios de laboratorio.csv')


def _clean(value) -> str:
    if value is None:
        return ''
    s = str(value).strip()
    return '' if s.lower() in ('nan', 'none') else s


def _d(val) -> Decimal:
    if val is None:
        return Decimal('0.00')
    try:
        return Decimal(str(val)).quantize(Decimal('0.01'))
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _d (sincronizar_precios_lims.py)")
        return Decimal('0.00')


def _parse_price(raw) -> Decimal:
    txt = _clean(raw)
    if not txt:
        return Decimal('0.00')
    txt = txt.replace('$', '').replace(',', '').strip()
    try:
        return Decimal(txt).quantize(Decimal('0.01'))
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _parse_price (sincronizar_precios_lims.py)")
        return Decimal('0.00')


def _norm_text(text: str) -> str:
    t = _clean(text).upper()
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _read_tarifa_rows():
    if not os.path.isfile(CSV_TARIFA):
        return []
    rows = []
    for encoding in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            with open(CSV_TARIFA, encoding=encoding, newline='') as fh:
                reader = csv.reader(fh)
                for line in reader:
                    if line and _clean(line[0]).lower() == 'tipo':
                        break
                for line in reader:
                    if not line or len(line) < 5:
                        continue
                    rows.append({
                        'tipo': _clean(line[0]),
                        'codigo': _clean(line[1]),
                        'abreviatura': _clean(line[2]),
                        'descripcion': _clean(line[3]),
                        'importe': _parse_price(line[4]),
                    })
            return rows
        except (UnicodeError, OSError):
            rows = []
    return rows


def _match_analito(row, codigo_map, abrev_map, nombre_map):
    code = _norm_text(row['codigo'])
    abrev = _norm_text(row['abreviatura'])
    desc = _norm_text(row['descripcion'])

    for key in (code, abrev):
        if key and key in codigo_map:
            return codigo_map[key]
    if desc and desc in nombre_map:
        return nombre_map[desc]
    return None


def _match_perfil(row, legacy_map, nombre_map):
    code = _norm_text(row['codigo'])
    abrev = _norm_text(row['abreviatura'])
    desc = _norm_text(row['descripcion'])

    for key in (code, abrev):
        if key and key in legacy_map:
            return legacy_map[key]
    if desc and desc in nombre_map:
        return nombre_map[desc]
    return None


def _match_paquete(row, legacy_map, nombre_map):
    code = _norm_text(row['codigo'])
    abrev = _norm_text(row['abreviatura'])
    desc = _norm_text(row['descripcion'])

    for key in (code, abrev):
        if key and key in legacy_map:
            return legacy_map[key]
    if desc and desc in nombre_map:
        return nombre_map[desc]
    return None


class Command(BaseCommand):
    help = 'Nivel 4: sincroniza PrecioItem desde tarifa original + costo_lista.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--empresa-id', type=int, default=None,
            help='Empresa destino para fijar contexto tenant durante la importación.',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        empresa = self._resolver_empresa(options.get('empresa_id'))
        if dry:
            self.stdout.write(self.style.WARNING('[DRY-RUN]\n'))
        if empresa:
            self.stdout.write(self.style.NOTICE(
                f'Empresa contexto: {empresa.pk} — {empresa.nombre}'
            ))

        try:
            with tenant_bypass():
                if empresa:
                    set_current_empresa(empresa)

                tarifa_rows = _read_tarifa_rows()
                if tarifa_rows:
                    self.stdout.write(self.style.NOTICE(
                        f'Tarifa original detectada: {len(tarifa_rows)} filas en {CSV_TARIFA}'
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f'No se pudo leer la tarifa original en {CSV_TARIFA}. '
                        'Se continuará solo con costo_lista actual.'
                    ))

                na = np = nq = 0
                tarifa_a = tarifa_p = tarifa_q = 0
                sin_match = []

                analitos = list(
                    Analito.objects.all().only('id', 'codigo', 'abreviatura', 'nombre', 'costo_lista')
                )
                perfiles = list(
                    PerfilLims.objects.all().only('id', 'id_perfil_legacy', 'nombre', 'costo_lista')
                )
                paquetes = list(
                    PaqueteLims.objects.all().only('id', 'id_paquete_legacy', 'nombre', 'costo_lista')
                )

                analito_codigo_map = {}
                analito_abrev_map = {}
                analito_nombre_map = {}
                for a in analitos:
                    if a.codigo:
                        analito_codigo_map[_norm_text(a.codigo)] = a
                    if a.abreviatura:
                        analito_abrev_map[_norm_text(a.abreviatura)] = a
                    if a.nombre:
                        analito_nombre_map[_norm_text(a.nombre)] = a

                perfil_legacy_map = {}
                perfil_nombre_map = {}
                for p in perfiles:
                    if p.id_perfil_legacy:
                        legacy_norm = _norm_text(p.id_perfil_legacy)
                        perfil_legacy_map[legacy_norm] = p
                        if '|' in legacy_norm:
                            perfil_legacy_map.setdefault(legacy_norm.split('|', 1)[0], p)
                    if p.nombre:
                        perfil_nombre_map[_norm_text(p.nombre)] = p

                paquete_legacy_map = {}
                paquete_nombre_map = {}
                for q in paquetes:
                    if q.id_paquete_legacy:
                        paquete_legacy_map[_norm_text(q.id_paquete_legacy)] = q
                    if q.nombre:
                        paquete_nombre_map[_norm_text(q.nombre)] = q

                with transaction.atomic():
                    # Paso 1: ajustar costo_lista desde la tarifa original cuando exista.
                    if tarifa_rows:
                        for row in tarifa_rows:
                            precio = row['importe']
                            if precio <= 0:
                                continue
                            tipo_raw = _norm_text(row['tipo'])
                            if 'PAQUETE' in tipo_raw:
                                obj = _match_paquete(row, paquete_legacy_map, paquete_nombre_map)
                                if obj:
                                    if not dry and _d(obj.costo_lista) != precio:
                                        obj.costo_lista = precio
                                        obj.save(update_fields=['costo_lista', 'fecha_actualiz'])
                                    tarifa_q += 1
                                else:
                                    sin_match.append(('Q', row['codigo'], row['abreviatura'], row['descripcion'], str(precio)))
                            elif 'PERFIL' in tipo_raw:
                                obj = _match_perfil(row, perfil_legacy_map, perfil_nombre_map)
                                if obj:
                                    if not dry and _d(obj.costo_lista) != precio:
                                        obj.costo_lista = precio
                                        obj.save(update_fields=['costo_lista', 'fecha_actualiz'])
                                    tarifa_p += 1
                                else:
                                    sin_match.append(('P', row['codigo'], row['abreviatura'], row['descripcion'], str(precio)))
                            else:
                                obj = _match_analito(row, analito_codigo_map, analito_abrev_map, analito_nombre_map)
                                if obj:
                                    if not dry and _d(obj.costo_lista) != precio:
                                        obj.costo_lista = precio
                                        obj.save(update_fields=['costo_lista', 'fecha_actualiz'])
                                    tarifa_a += 1
                                else:
                                    sin_match.append(('A', row['codigo'], row['abreviatura'], row['descripcion'], str(precio)))

                    def precio_de(obj) -> Decimal:
                        v = getattr(obj, 'costo_lista', None)
                        if v is None:
                            return Decimal('0.00')
                        return Decimal(v).quantize(Decimal('0.01'))

                    for a in Analito.objects.filter(es_vendible_individualmente=True, activo=True):
                        co = precio_de(a)
                        if dry:
                            na += 1
                            continue
                        PrecioItem.objects.update_or_create(
                            analito=a,
                            defaults={
                                'tipo': 'A',
                                'precio_venta': co,
                                'activo': True,
                                'perfil': None,
                                'paquete': None,
                            },
                        )
                        na += 1

                    for p in PerfilLims.objects.filter(activo=True):
                        co = precio_de(p)
                        if dry:
                            np += 1
                            continue
                        PrecioItem.objects.update_or_create(
                            perfil=p,
                            defaults={
                                'tipo': 'P',
                                'precio_venta': co,
                                'activo': True,
                                'analito': None,
                                'paquete': None,
                            },
                        )
                        np += 1

                    for q in PaqueteLims.objects.filter(activo=True):
                        co = precio_de(q)
                        if dry:
                            nq += 1
                            continue
                        PrecioItem.objects.update_or_create(
                            paquete=q,
                            defaults={
                                'tipo': 'Q',
                                'precio_venta': co,
                                'activo': True,
                                'analito': None,
                                'perfil': None,
                            },
                        )
                        nq += 1

                if dry:
                    self.stdout.write(
                        f'  [DRY] Tarifa aplicada: A={tarifa_a} | P={tarifa_p} | Q={tarifa_q}\n'
                        f'  [DRY] Analitos PDV: {na} | Perfiles: {np} | Paquetes: {nq}\n'
                    )
                    self.stdout.write(self.style.WARNING('[DRY-RUN] Sin cambios.'))
                    return

                self.stdout.write(self.style.SUCCESS(
                    f'\n=== Nivel 4 (precios) ===\n'
                    f'  Tarifa aplicada: A={tarifa_a} | P={tarifa_p} | Q={tarifa_q}\n'
                    f'  PrecioItem tipo A (analito venta directa): {na}\n'
                    f'  PrecioItem tipo P (perfil): {np}\n'
                    f'  PrecioItem tipo Q (paquete): {nq}\n'
                    f'  Total filas PrecioItem: {PrecioItem.objects.count()}\n'
                ))
                if sin_match:
                    self.stdout.write(self.style.WARNING(
                        f'  Advertencia: {len(sin_match)} filas de tarifa no encontraron coincidencia exacta.'
                    ))
        finally:
            clear_current_empresa()

    def _resolver_empresa(self, empresa_id):
        if empresa_id:
            return Empresa.objects.filter(pk=empresa_id, activa=True).first()
        return resolve_default_empresa_sistema()