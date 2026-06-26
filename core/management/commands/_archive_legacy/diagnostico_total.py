"""
Diagnóstico Total: Forzado de precios + Auditoría de rangos.

 PARTE 1 – Fuerza la actualización de precios desde tarifas.csv
           en AMBAS tablas (core.Estudio Y laboratorio.Estudio).
 PARTE 2 – Simula selección de rangos para HGB y leuct (mujer, 25 años).

Uso:
    python manage.py diagnostico_total
"""
import csv
import os
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
import logging


def _c(val):
    if val is None:
        return ''
    s = str(val).strip()
    return '' if s.lower() in ('nan', 'none') else s


class Command(BaseCommand):
    help = 'Diagnóstico total: forzar precios + auditar rangos'

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        self._parte1_precios()
        self._parte2_rangos()

    # ══════════════════════════════════════════════════════════
    # PARTE 1: FORZADO DE PRECIOS
    # ══════════════════════════════════════════════════════════
    def _parte1_precios(self):
        self.stdout.write(self.style.WARNING('\n' + '=' * 70))
        self.stdout.write(self.style.WARNING('PARTE 1: FORZADO DE PRECIOS DESDE tarifas.csv'))
        self.stdout.write(self.style.WARNING('=' * 70))

        ruta = os.path.join(settings.BASE_DIR, 'tarifas.csv')
        if not os.path.isfile(ruta):
            self.stderr.write(self.style.ERROR(f'No se encontró: {ruta}'))
            return

        # ── Leer CSV ──
        rows = []
        for enc in ('latin-1', 'utf-8-sig', 'cp1252'):
            try:
                with open(ruta, encoding=enc, newline='') as f:
                    reader = csv.reader(f)
                    for line in reader:
                        if line and line[0].strip().lower() == 'tipo':
                            break
                    for line in reader:
                        if line and len(line) >= 5:
                            rows.append(line)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        self.stdout.write(f'Filas leídas: {len(rows)}')

        # ── Construir índices de AMBAS tablas ──
        # core.Estudio
        core_by_cod = {}
        core_by_abr = {}
        core_by_name = {}
        for e in CoreEstudio.objects.all():
            if e.codigo:
                core_by_cod[e.codigo.strip()] = e
                core_by_cod[e.codigo.strip().upper()] = e
                core_by_cod[e.codigo.strip().lower()] = e
            if e.abreviatura:
                core_by_abr[e.abreviatura.strip()] = e
                core_by_abr[e.abreviatura.strip().upper()] = e
                core_by_abr[e.abreviatura.strip().lower()] = e
            if e.nombre:
                core_by_name[e.nombre.strip().upper()] = e

        # laboratorio.Estudio
        lab_by_cod = {}
        lab_by_name = {}
        try:
            from laboratorio.models import Estudio as LabEstudio
            for e in LabEstudio.objects.all():
                if e.codigo:
                    lab_by_cod[e.codigo.strip()] = e
                    lab_by_cod[e.codigo.strip().upper()] = e
                    lab_by_cod[e.codigo.strip().lower()] = e
                if e.nombre:
                    lab_by_name[e.nombre.strip().upper()] = e
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en _parte1_precios (diagnostico_total.py)")
            LabEstudio = None

        core_ok = 0
        lab_ok = 0
        no_match = []

        for line in rows:
            tipo = _c(line[0])
            codigo = _c(line[1])
            abreviatura = _c(line[2])
            descripcion = _c(line[3])
            importe_raw = _c(line[4])

            if not codigo and not abreviatura:
                continue

            precio = Decimal('0.00')
            if importe_raw:
                try:
                    limpio = importe_raw.replace(',', '').replace('$', '').strip()
                    if limpio:
                        precio = Decimal(limpio)
                except (InvalidOperation, ValueError):
                    pass

            if precio <= 0:
                continue

            # ── Buscar en core.Estudio (búsqueda robusta) ──
            core_est = (
                core_by_cod.get(codigo)
                or core_by_cod.get(codigo.upper())
                or core_by_cod.get(codigo.lower())
                or core_by_abr.get(abreviatura)
                or core_by_abr.get(abreviatura.upper())
                or core_by_abr.get(abreviatura.lower())
                or core_by_abr.get(codigo)
                or core_by_abr.get(codigo.upper())
                or core_by_cod.get(abreviatura)
                or core_by_cod.get(abreviatura.upper())
                or core_by_name.get(descripcion.upper())
            )

            if core_est and core_est.precio != precio:
                old = core_est.precio
                core_est.precio = precio
                try:
                    core_est.save(update_fields=['precio'])
                    core_ok += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  [CORE] {core_est.codigo} | ${old} -> ${precio}')
                    )
                except Exception as e:
                    logging.getLogger(__name__).exception("Error inesperado en _parte1_precios (diagnostico_total.py)")
                    self.stderr.write(f'  Error core {codigo}: {e}')

            # ── Buscar en laboratorio.Estudio ──
            lab_est = (
                lab_by_cod.get(codigo)
                or lab_by_cod.get(codigo.upper())
                or lab_by_cod.get(codigo.lower())
                or lab_by_cod.get(abreviatura)
                or lab_by_cod.get(abreviatura.upper())
                or lab_by_name.get(descripcion.upper())
            )

            if lab_est:
                old_lab = getattr(lab_est, 'precio_base', None)
                if old_lab != precio:
                    lab_est.precio_base = precio
                    try:
                        lab_est.save(update_fields=['precio_base'])
                        lab_ok += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  [LAB]  {lab_est.codigo} | ${old_lab} -> ${precio}')
                        )
                    except Exception as e:
                        logging.getLogger(__name__).exception("Error inesperado en _parte1_precios (diagnostico_total.py)")
                        self.stderr.write(f'  Error lab {codigo}: {e}')

            if not core_est and not lab_est:
                no_match.append(f'{tipo} | {codigo} | {abreviatura} | {descripcion} | ${importe_raw}')

        self.stdout.write(self.style.SUCCESS(f'\ncore.Estudio actualizados: {core_ok}'))
        self.stdout.write(self.style.SUCCESS(f'lab.Estudio  actualizados: {lab_ok}'))

        if no_match:
            self.stdout.write(self.style.WARNING(f'\nSin match en NINGUNA tabla ({len(no_match)}):'))
            for item in no_match[:20]:
                self.stdout.write(f'  {item}')
            if len(no_match) > 20:
                self.stdout.write(f'  ... y {len(no_match) - 20} más')

    # ══════════════════════════════════════════════════════════
    # PARTE 2: AUDITORÍA DE RANGOS
    # ══════════════════════════════════════════════════════════
    def _parte2_rangos(self):
        self.stdout.write(self.style.WARNING('\n' + '=' * 70))
        self.stdout.write(self.style.WARNING('PARTE 2: AUDITORÍA DE RANGOS DE REFERENCIA'))
        self.stdout.write(self.style.WARNING('=' * 70))

        # Simular: Mujer de 25 años
        sexo_paciente = 'F'
        edad_paciente = 25
        self.stdout.write(f'Simulando paciente: Sexo={sexo_paciente}, Edad={edad_paciente} años\n')

        # Buscar parámetros HGB y leuct
        for param_buscar in ['HGB', 'leuct', 'RBC']:
            self.stdout.write(self.style.WARNING(f'\n── Parámetro: {param_buscar} ──'))

            parametros = Parametro.objects.filter(
                Q(abreviatura__iexact=param_buscar) |
                Q(nombre__icontains=param_buscar)
            ).select_related('estudio')[:5]

            if not parametros.exists():
                self.stdout.write(self.style.ERROR(f'  No se encontró parámetro "{param_buscar}" en BD'))
                continue

            for param in parametros:
                self.stdout.write(f'\n  Param ID={param.id} | Nombre="{param.nombre}" | Abr="{param.abreviatura}"')
                self.stdout.write(f'  Estudio: {param.estudio.codigo} - {param.estudio.nombre}')
                self.stdout.write(f'  Unidad: {param.unidad} | Tipo: {param.tipo_dato}')

                rangos = RangoReferencia.objects.filter(
                    parametro=param
                ).order_by('sexo', 'edad_minima')

                if not rangos.exists():
                    self.stdout.write(self.style.ERROR('  ⚠ NO HAY RANGOS DE REFERENCIA para este parámetro'))
                    continue

                self.stdout.write(f'  Total rangos: {rangos.count()}')
                rango_elegido = None

                for rango in rangos:
                    edad_min = rango.edad_minima or 0
                    edad_max = rango.edad_maxima or 999

                    # Evaluar si coincide
                    sexo_ok = rango.sexo in (sexo_paciente, 'I')
                    edad_ok = edad_min <= edad_paciente <= edad_max

                    coincide = sexo_ok and edad_ok
                    marca = 'SI' if coincide else 'NO'
                    icon = '>>>' if coincide else '   '

                    self.stdout.write(
                        f'  {icon} Rango ID={rango.id}: '
                        f'Sexo={rango.sexo} (ok={sexo_ok}), '
                        f'Edad=[{edad_min}-{edad_max}] (ok={edad_ok}), '
                        f'Ref=[{rango.valor_minimo}-{rango.valor_maximo}] '
                        f'Texto="{rango.texto_referencia or ""}" '
                        f'=> Coincide? {marca}'
                    )

                    if coincide and not rango_elegido:
                        rango_elegido = rango

                if rango_elegido:
                    self.stdout.write(self.style.SUCCESS(
                        f'\n  RANGO SELECCIONADO: {rango_elegido.valor_minimo} - {rango_elegido.valor_maximo} '
                        f'(Sexo={rango_elegido.sexo}, Edad={rango_elegido.edad_minima}-{rango_elegido.edad_maxima})'
                    ))
                else:
                    self.stdout.write(self.style.ERROR(
                        f'\n  ⚠ NINGÚN RANGO COINCIDIÓ para Sexo={sexo_paciente}, Edad={edad_paciente}'
                    ))

        # ── Estadísticas generales de rangos ──
        self.stdout.write(self.style.WARNING('\n── Estadísticas Generales ──'))
        total_params = Parametro.objects.count()
        total_rangos = RangoReferencia.objects.count()
        params_sin_rango = Parametro.objects.filter(rangos_referencia__isnull=True).count()
        self.stdout.write(f'  Total Parámetros:         {total_params}')
        self.stdout.write(f'  Total Rangos Referencia:  {total_rangos}')
        self.stdout.write(f'  Params SIN ningún rango:  {params_sin_rango}')

        # Verificar edades almacenadas
        rangos_muestra = RangoReferencia.objects.filter(
            edad_maxima__isnull=False
        ).values_list('edad_minima', 'edad_maxima')[:20]
        self.stdout.write(f'\n  Muestra de rangos edad (primeros 20):')
        for emin, emax in rangos_muestra:
            unidad = 'AÑOS' if (emax or 0) <= 200 else '¿DÍAS?'
            self.stdout.write(f'    [{emin} - {emax}] {unidad}')

        self.stdout.write(self.style.SUCCESS('\n=== DIAGNÓSTICO COMPLETADO ===\n'))