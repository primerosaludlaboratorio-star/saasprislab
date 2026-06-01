"""
LIMS v7.5 — Nivel 3: Paquetes (composicion hibrida)

  1) Paquetes.csv         → PaqueteLims (Abreviatura = id_paquete_legacy, Costo)
  2) Paquetes_Perfil.csv  → M2M: Tipo Prueba → Analito; Tipo Perfil → PerfilLims por codigo examen

Requiere Nivel 1 y 2 importados.

Uso:
  python manage.py importar_paquetes_perfil_lims
  python manage.py importar_paquetes_perfil_lims --dry-run
  python manage.py importar_paquetes_perfil_lims --limpiar-paquetes
"""
import csv
import os
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from lims.models import Analito, PaqueteLims, PerfilLims

BASE_DIR = getattr(settings, 'BASE_DIR', os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
))
CSV_PAQUETES = os.path.join(BASE_DIR, 'datos_lims', 'Paquetes.csv')
CSV_PAQUETES_PERFIL = os.path.join(BASE_DIR, 'datos_lims', 'Paquetes_Perfil.csv')


def _decimal_costo(valor) -> Decimal:
    if valor is None or valor == '':
        return Decimal('0.00')
    try:
        return Decimal(str(valor).strip().replace(',', '.')).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError):
        return Decimal('0.00')


def _buscar_analito(codigo: str):
    c = (codigo or '').strip()
    if not c:
        return None
    a = Analito.objects.filter(codigo__iexact=c).first()
    if a:
        return a
    return Analito.objects.filter(abreviatura__iexact=c).first()


def resolver_perfil_por_codigo_examen(codigo: str):
    """
    Paquetes_Perfil usa el Codigo del examen (ej. 45, QS3, PERFHEP).
    PerfilLims.id_perfil_legacy = 'Codigo|Abreviatura'.
    """
    c = (codigo or '').strip()
    if not c:
        return None
    candidatos = list(PerfilLims.objects.filter(id_perfil_legacy__startswith=c + '|'))
    if len(candidatos) == 1:
        return candidatos[0]
    uno = PerfilLims.objects.filter(id_perfil_legacy=c).first()
    if uno:
        return uno
    if len(candidatos) > 1:
        return None
    return None


def _nombre_paquete_unico(nombre_base: str, abrev: str) -> str:
    base = (nombre_base or abrev).strip()[:200]
    if not base:
        base = abrev[:200]
    qs = PaqueteLims.objects.filter(nombre=base)
    if abrev:
        qs = qs.exclude(id_paquete_legacy=abrev)
    if not qs.exists():
        return base
    suf = f' ({abrev})'[:50]
    return (base[: 200 - len(suf)] + suf)[:200]


class Command(BaseCommand):
    help = 'Nivel 3: Paquetes.csv + Paquetes_Perfil.csv → PaqueteLims y M2M.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--limpiar-paquetes', action='store_true',
            help='Eliminar todos los PaqueteLims antes de importar',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        limpiar = options['limpiar_paquetes']

        if not os.path.exists(CSV_PAQUETES):
            self.stdout.write(self.style.ERROR(f'No existe: {CSV_PAQUETES}'))
            return
        if not os.path.exists(CSV_PAQUETES_PERFIL):
            self.stdout.write(self.style.ERROR(f'No existe: {CSV_PAQUETES_PERFIL}'))
            return

        if limpiar and not dry:
            n = PaqueteLims.objects.count()
            PaqueteLims.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'  Eliminados {n} paquetes previos.\n'))

        if dry:
            self.stdout.write(self.style.WARNING('[DRY-RUN]\n'))

        # ── Fase 1: Paquetes.csv ────────────────────────────────────────────
        n_paq = 0
        with open(CSV_PAQUETES, newline='', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f)
            rows_p = list(reader)

        if not dry:
            with transaction.atomic():
                for row in rows_p:
                    ab = (row.get('Abreviatura') or '').strip()
                    if not ab:
                        continue
                    desc = (row.get('Descripcion') or ab).strip()
                    nombre = _nombre_paquete_unico(desc, ab)
                    costo = _decimal_costo(row.get('Costo'))
                    indic = (row.get('Indicaciones') or '').strip()
                    notas = (row.get('Notas_internas') or '').strip()
                    texto_desc = ' '.join(x for x in (indic, notas) if x).strip()

                    PaqueteLims.objects.update_or_create(
                        id_paquete_legacy=ab,
                        defaults={
                            'nombre': nombre,
                            'descripcion': texto_desc[:2000],
                            'costo_lista': costo,
                            'venta_publico': True,
                            'activo': True,
                        },
                    )
                    n_paq += 1
        else:
            for row in rows_p:
                if (row.get('Abreviatura') or '').strip():
                    n_paq += 1
            self.stdout.write(f'  [DRY] Fase 1 — paquetes en CSV: {n_paq}')

        if not dry:
            self.stdout.write(f'  Fase 1 — PaqueteLims desde Paquetes.csv: {n_paq}')

        # ── Fase 2: Paquetes_Perfil.csv ─────────────────────────────────────
        grupos = defaultdict(lambda: {'pruebas': set(), 'perfiles_cod': set()})

        with open(CSV_PAQUETES_PERFIL, newline='', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.reader(f)
            rows_pp = list(reader)

        for row in rows_pp[2:]:
            while len(row) < 5:
                row.append('')
            paq_ab, _paq_desc, tipo, cod_est, _ed = [(x or '').strip() for x in row[:5]]
            if not paq_ab:
                continue
            if paq_ab.lower() == 'abreviatura':
                continue
            t = (tipo or '').strip().lower()
            cod_est = (cod_est or '').strip()
            if not cod_est:
                continue
            if 'prueba' in t:
                grupos[paq_ab]['pruebas'].add(cod_est)
            elif 'perfil' in t:
                grupos[paq_ab]['perfiles_cod'].add(cod_est)

        self.stdout.write(f'  Fase 2 — paquetes con lineas de composicion: {len(grupos)}')

        sin_paq = ambiguo = no_an = no_pf = 0
        muestra = []

        with transaction.atomic():
            for paq_ab, data in grupos.items():
                paq = PaqueteLims.objects.filter(id_paquete_legacy=paq_ab).first()
                if not paq:
                    sin_paq += 1
                    continue

                analito_ids = []
                for cod in sorted(data['pruebas']):
                    a = _buscar_analito(cod)
                    if a:
                        analito_ids.append(a.pk)
                    else:
                        no_an += 1
                        if len(muestra) < 15:
                            muestra.append(('Prueba', paq_ab, cod))

                perfiles = []
                for cod in sorted(data['perfiles_cod']):
                    p = resolver_perfil_por_codigo_examen(cod)
                    if p:
                        perfiles.append(p)
                    else:
                        cands = PerfilLims.objects.filter(id_perfil_legacy__startswith=cod + '|').count()
                        if cands > 1:
                            ambiguo += 1
                            if len(muestra) < 18:
                                muestra.append(('Perfil_ambiguo', paq_ab, cod))
                        else:
                            no_pf += 1
                            if len(muestra) < 18:
                                muestra.append(('Perfil_no', paq_ab, cod))

                if dry:
                    self.stdout.write(
                        f'  [DRY] {paq_ab}: {len(analito_ids)} pruebas, {len(perfiles)} perfiles'
                    )
                    continue

                paq.analitos.set(analito_ids)
                paq.perfiles.set(perfiles)

        if dry:
            self.stdout.write(self.style.WARNING('\n[DRY-RUN] Sin escritura en BD.'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'\n=== Nivel 3 completado ===\n'
            f'  PaqueteLims en BD: {PaqueteLims.objects.count()}\n'
            f'  Lineas con abreviatura sin Paquetes.csv: {sin_paq}\n'
            f'  Pruebas (codigo) sin analito: {no_an}\n'
            f'  Perfiles no resueltos: {no_pf}\n'
            f'  Perfiles ambiguos (varios Codigo|Abrev): {ambiguo}\n'
        ))
        if muestra:
            self.stdout.write('  Muestra incidencias:')
            for item in muestra[:12]:
                self.stdout.write(f'    {item}')
