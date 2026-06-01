"""
LIMS v7.5 — Nivel 2: Perfiles (orden estricto)

  1) Examenes.csv        → crea PerfilLims (Codigo|Abreviatura, Descripcion, Costo, Id_examen)
  2) Examenes_Perfil.csv → compone M2M Analito por la misma llave (col0|col1)

Requiere analitos (importar_catalogo_lims).

Uso:
  python manage.py importar_examenes_perfil_lims
  python manage.py importar_examenes_perfil_lims --dry-run
  python manage.py importar_examenes_perfil_lims --limpiar-perfiles
"""
import csv
import os
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from lims.models import Analito, PerfilLims

BASE_DIR = getattr(settings, 'BASE_DIR', os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
))
CSV_EXAMENES = os.path.join(BASE_DIR, 'datos_lims', 'Examenes.csv')
CSV_EXAMENES_PERFIL = os.path.join(BASE_DIR, 'datos_lims', 'Examenes_Perfil.csv')


def _perfil_legacy_key(codigo: str, abrev: str) -> str:
    c = (codigo or '').strip()
    a = (abrev or '').strip()
    return f'{c}|{a}' if a else c


def _int_o_none(valor):
    try:
        return int(str(valor).strip())
    except (ValueError, TypeError):
        return None


def _decimal_costo(valor) -> Decimal:
    if valor is None or valor == '':
        return Decimal('0.00')
    try:
        return Decimal(str(valor).strip().replace(',', '.')).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError):
        return Decimal('0.00')


def _buscar_analito(codigo_estudio: str):
    c = (codigo_estudio or '').strip()
    if not c:
        return None
    a = Analito.objects.filter(codigo__iexact=c).first()
    if a:
        return a
    return Analito.objects.filter(abreviatura__iexact=c).first()


def _nombre_perfil_unico(desc: str, abrev: str, pkey: str) -> str:
    base = (desc or abrev or pkey).strip()[:200]
    if not base:
        base = pkey[:200]
    qs = PerfilLims.objects.filter(nombre=base)
    if pkey:
        qs = qs.exclude(id_perfil_legacy=pkey)
    if not qs.exists():
        return base
    pref = (abrev or pkey.split('|')[0] or 'perfil')[:40]
    extra = f' ({pref})'[:50]
    return (base[: 200 - len(extra)] + extra)[:200]


class Command(BaseCommand):
    help = 'Nivel 2: Examenes.csv + Examenes_Perfil.csv → PerfilLims y M2M analitos.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Simular sin guardar')
        parser.add_argument(
            '--limpiar-perfiles', action='store_true',
            help='Eliminar todos los PerfilLims antes de importar',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        limpiar = options['limpiar_perfiles']

        if not os.path.exists(CSV_EXAMENES):
            self.stdout.write(self.style.ERROR(f'No existe: {CSV_EXAMENES}'))
            return
        if not os.path.exists(CSV_EXAMENES_PERFIL):
            self.stdout.write(self.style.ERROR(f'No existe: {CSV_EXAMENES_PERFIL}'))
            return

        if limpiar and not dry:
            n = PerfilLims.objects.count()
            PerfilLims.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'  Eliminados {n} perfiles previos.\n'))

        if dry:
            self.stdout.write(self.style.WARNING('[DRY-RUN]\n'))

        # ── Fase 1: Examenes.csv ─────────────────────────────────────────────
        def_f1 = 0
        with open(CSV_EXAMENES, newline='', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f)
            rows_ex = list(reader)

        if not dry:
            with transaction.atomic():
                for row in rows_ex:
                    cod = (row.get('Codigo') or '').strip()
                    abrev = (row.get('Abreviatura') or '').strip()
                    if not cod:
                        continue
                    pkey = _perfil_legacy_key(cod, abrev)
                    desc = (row.get('Descripcion') or cod).strip()
                    nombre = _nombre_perfil_unico(desc, abrev, pkey)
                    id_ex = _int_o_none(row.get('Id_examen', ''))
                    costo = _decimal_costo(row.get('Costo'))
                    titulo = (row.get('Titulo') or '').strip()
                    meta = (row.get('Metodo') or '').strip()
                    descripcion = ' '.join(x for x in (f'Abrev: {abrev}', titulo, meta) if x).strip()

                    PerfilLims.objects.update_or_create(
                        id_perfil_legacy=pkey,
                        defaults={
                            'nombre': nombre,
                            'descripcion': descripcion[:2000],
                            'costo_lista': costo,
                            'id_examen_legacy': id_ex,
                            'activo': True,
                        },
                    )
                    def_f1 += 1
        else:
            for row in rows_ex:
                cod = (row.get('Codigo') or '').strip()
                if not cod:
                    continue
                def_f1 += 1
            self.stdout.write(f'  [DRY] Fase 1 — filas Examenes.csv con codigo: {def_f1}')

        if not dry:
            self.stdout.write(f'  Fase 1 — definiciones desde Examenes.csv: {def_f1} perfiles')

        # ── Fase 2: Examenes_Perfil.csv (por posicion) ──────────────────────
        grupos = defaultdict(lambda: {'codigos_analito': set()})

        with open(CSV_EXAMENES_PERFIL, newline='', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.reader(f)
            rows_ep = list(reader)

        for row in rows_ep[2:]:
            while len(row) < 5:
                row.append('')
            ec, ea, _ed, sc, _sd = [(x or '').strip() for x in row[:5]]
            if not ec and not ea:
                continue
            if ec.lower() == 'codigo' and ea.lower() == 'abreviatura':
                continue
            pkey = _perfil_legacy_key(ec, ea)
            if not pkey.strip('|'):
                continue
            if sc:
                grupos[pkey]['codigos_analito'].add(sc)

        self.stdout.write(f'  Fase 2 — grupos en Examenes_Perfil.csv: {len(grupos)}')

        sin_def = sin_analitos = no_encontrados = 0
        muestra_nf = []
        comp_ok = 0

        with transaction.atomic():
            for pkey, info in grupos.items():
                codigos = info['codigos_analito']
                analito_ids = []
                for cod in sorted(codigos):
                    a = _buscar_analito(cod)
                    if a:
                        analito_ids.append(a.pk)
                    else:
                        no_encontrados += 1
                        if len(muestra_nf) < 20:
                            muestra_nf.append((pkey, cod))

                perfil = PerfilLims.objects.filter(id_perfil_legacy=pkey).first()
                if not perfil:
                    sin_def += 1
                    if dry:
                        self.stdout.write(self.style.WARNING(f'  [DRY] Sin Examenes.csv: {pkey}'))
                    continue

                if dry:
                    self.stdout.write(
                        f'  [DRY] {pkey} -> {perfil.nombre[:40]}... | {len(analito_ids)} analitos'
                    )
                    if not analito_ids:
                        sin_analitos += 1
                    continue

                perfil.analitos.set(analito_ids)
                comp_ok += 1
                if not analito_ids:
                    sin_analitos += 1

        if dry:
            self.stdout.write(self.style.WARNING('\n[DRY-RUN] Fase 2 sin escritura (solo simulacion composicion).'))
            self.stdout.write(f'  Grupos sin fila en Examenes.csv: {sin_def}')
            return

        vacios_m2m = (
            PerfilLims.objects.annotate(_nac=Count('analitos'))
            .filter(_nac=0)
            .count()
        )
        self.stdout.write(self.style.SUCCESS(
            f'\n=== Nivel 2 completado ===\n'
            f'  Perfiles definidos (Examenes.csv): {PerfilLims.objects.count()}\n'
            f'  Perfiles compuestos (Examenes_Perfil): {comp_ok}\n'
            f'  Claves en Perfil sin definicion en Examenes.csv: {sin_def}\n'
            f'  Grupos Perfil con lista de estudios vacia: {sin_analitos}\n'
            f'  Perfiles en BD sin ningun analito (M2M): {vacios_m2m}\n'
            f'  Codigos de estudio no encontrados en Analito: {no_encontrados}\n'
        ))
        if muestra_nf:
            self.stdout.write('  Muestra (perfil|codigo estudio no resuelto):')
            for pk, cod in muestra_nf[:12]:
                self.stdout.write(f'    {pk}  ->  {cod}')
