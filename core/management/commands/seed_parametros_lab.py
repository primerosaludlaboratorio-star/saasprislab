"""
PRISLAB — Sincronización de Parámetros de Laboratorio
======================================================
Este comando migra los parámetros del catálogo importado (laboratorio.Parametro)
hacia el modelo SaaS operativo (core.Parametro + core.RangoReferencia) que usa
la vista de captura de resultados.

También incluye el catálogo base de la CBC (Citometría Hemática Completa) como
seed fijo, en caso de que no existan datos en el modelo legacy.

Uso:
    python manage.py seed_parametros_lab
    python manage.py seed_parametros_lab --dry-run
    python manage.py seed_parametros_lab --solo-cbc
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import logging

# ---------------------------------------------------------------------------
# Catálogo base de parámetros de CBC (22 parámetros standard OMS/CLSI)
# Formato: (nombre, abreviatura, unidad, ref_m_min, ref_m_max, ref_f_min, ref_f_max, panico_min, panico_max, orden)
# ---------------------------------------------------------------------------
CBC_PARAMETROS = [
    # Nombre,                      Abrev,    Unidad,       M_min, M_max, F_min, F_max, pan_min, pan_max, orden
    ("Leucocitos",                 "WBC",    "10³/μL",     4.5,   11.0,  4.5,   11.0,  2.0,    30.0,    1),
    ("Eritrocitos",                "RBC",    "10⁶/μL",     4.7,   6.1,   4.2,   5.4,   None,   None,    2),
    ("Hemoglobina",                "HGB",    "g/dL",       13.5,  17.5,  12.0,  16.0,  6.0,    20.0,    3),
    ("Hematocrito",                "HCT",    "%",          41.0,  53.0,  36.0,  46.0,  18.0,   None,    4),
    ("V.C.M. (Volumen Corp. Medio)","VCM",   "fL",         80.0,  100.0, 80.0,  100.0, None,   None,    5),
    ("H.C.M. (Hemoglob. Corp. Media)","HCM","pg",         27.0,  31.0,  27.0,  31.0,  None,   None,    6),
    ("C.M.H.C.",                   "CMHC",   "g/dL",       32.0,  36.0,  32.0,  36.0,  None,   None,    7),
    ("R.D.W. (Amplitud Distrib. RBC)","RDW", "%",          11.5,  14.5,  11.5,  14.5,  None,   None,    8),
    ("Plaquetas",                  "PLT",    "10³/μL",     150.0, 400.0, 150.0, 400.0, 50.0,   1000.0,  9),
    ("V.P.M. (Vol. Plaquetario Medio)","VPM","fL",         7.5,   12.5,  7.5,   12.5,  None,   None,   10),
    ("P.D.W.",                     "PDW",    "%",          9.0,   17.0,  9.0,   17.0,  None,   None,   11),
    ("P.C.T.",                     "PCT",    "%",          0.108, 0.282, 0.108, 0.282, None,   None,   12),
    ("Neutrófilos %",              "NEU%",   "%",          50.0,  75.0,  50.0,  75.0,  None,   None,   13),
    ("Linfocitos %",               "LIN%",   "%",          20.0,  40.0,  20.0,  40.0,  None,   None,   14),
    ("Monocitos %",                "MON%",   "%",          2.0,   8.0,   2.0,   8.0,   None,   None,   15),
    ("Eosinófilos %",              "EOS%",   "%",          0.0,   5.0,   0.0,   5.0,   None,   None,   16),
    ("Basófilos %",                "BAS%",   "%",          0.0,   1.0,   0.0,   1.0,   None,   None,   17),
    ("Neutrófilos #",              "NEU#",   "10³/μL",     1.8,   7.0,   1.8,   7.0,   0.5,   20.0,   18),
    ("Linfocitos #",               "LIN#",   "10³/μL",     1.0,   4.8,   1.0,   4.8,   None,   None,   19),
    ("Monocitos #",                "MON#",   "10³/μL",     0.2,   1.0,   0.2,   1.0,   None,   None,   20),
    ("Eosinófilos #",              "EOS#",   "10³/μL",     0.0,   0.45,  0.0,   0.45,  None,   None,   21),
    ("Basófilos #",                "BAS#",   "10³/μL",     0.0,   0.2,   0.0,   0.2,   None,   None,   22),
]

# Catálogo base Química Sanguínea básica
QUIM_BASICA = [
    # Nombre,          Abrev,   Unidad,  M_min, M_max, F_min, F_max, pan_min, pan_max, orden
    ("Glucosa",        "GLU",   "mg/dL",  70.0,  99.0,  70.0,  99.0,   40.0,  500.0,  1),
    ("Urea",           "BUN",   "mg/dL",  7.0,   25.0,  7.0,   25.0,   None,  None,   2),
    ("Creatinina",     "CREA",  "mg/dL",  0.7,   1.2,   0.5,   1.0,    None,  15.0,   3),
    ("Ácido Úrico",    "UA",    "mg/dL",  3.4,   7.0,   2.4,   5.7,    None,  None,   4),
    ("Colesterol Total","CHOL", "mg/dL",  0.0,  200.0,  0.0,  200.0,  None,  None,    5),
    ("Triglicéridos",  "TRG",   "mg/dL",  0.0,  150.0,  0.0,  150.0,  None,  None,    6),
    ("HDL Colesterol", "HDL",   "mg/dL",  40.0,  None,  50.0,  None,  None,  None,    7),
    ("LDL Colesterol", "LDL",   "mg/dL",  0.0,  100.0,  0.0,  100.0, None,  None,    8),
    ("AST (TGO)",      "AST",   "U/L",    5.0,  40.0,   5.0,  40.0,   None,  None,    9),
    ("ALT (TGP)",      "ALT",   "U/L",    5.0,  40.0,   5.0,  40.0,   None,  None,   10),
    ("Bilirrubina Total","BTOT","mg/dL",  0.1,   1.0,   0.1,   1.0,   None,   20.0,  11),
    ("Bilirrubina Directa","BDIR","mg/dL",0.0,   0.25,  0.0,   0.25,  None,  None,   12),
    ("Bilirrubina Indirecta","BIND","mg/dL",0.1,  0.75, 0.1,   0.75,  None,  None,   13),
    ("Fosfatasa Alcalina","FAL", "U/L",   44.0, 147.0,  44.0, 147.0, None,  None,   14),
    ("Proteínas Totales","PROT","g/dL",   6.4,   8.3,   6.4,   8.3,  None,  None,   15),
    ("Albúmina",       "ALB",   "g/dL",   3.5,   5.0,   3.5,   5.0,  None,  None,   16),
    ("Calcio",         "CA",    "mg/dL",  8.4,  10.2,   8.4,  10.2,   6.0,  13.0,   17),
    ("Fósforo",        "PHOS",  "mg/dL",  2.5,   4.5,   2.5,   4.5,  None,  None,   18),
    ("Potasio",        "K",     "mEq/L",  3.5,   5.1,   3.5,   5.1,   2.5,   6.5,   19),
    ("Sodio",          "NA",    "mEq/L", 136.0, 145.0, 136.0, 145.0, 120.0, 160.0,  20),
    ("Cloro",          "CL",    "mEq/L",  98.0, 107.0,  98.0, 107.0,  None,  None,  21),
]

# Glucosa de ayuno simple
GLUCOSA_SIMPLE = [
    ("Glucosa",        "GLU",   "mg/dL",  70.0,  99.0,  70.0,  99.0,   40.0,  500.0,  1),
]

# Búsqueda de nombres alternativos de la CBC en la DB
CBC_NOMBRES_POSIBLES = [
    "CITOMETRIA HEMATICA COMPLETA",
    "CITOMETRÍA HEMÁTICA COMPLETA",
    "BIOMETRIA HEMATICA",
    "BIOMETRÍA HEMÁTICA",
    "BHC",
    "CBC",
    "HEMOGRAMA",
    "CITOMETRIA HEMATICA",
    "CITOMETRÍA HEMÁTICA",
]

QUIM_NOMBRES_POSIBLES = [
    "QUIMICA SANGUINEA BASICA",
    "QUÍMICA SANGUÍNEA BÁSICA",
    "QUIMICA SANGUINEA",
    "QUÍMICA SANGUÍNEA",
    "QUIMICA SERICA",
    "QUÍMICA SÉRICA",
    "PERFIL METABOLICO",
    "PERFIL METABÓLICO",
    "PERFIL BIOQUIMICO",
    "PERFIL BIOQUÍMICO",
    "QS6",
    "QS12",
    "QS20",
]

GLUCOSA_NOMBRES_POSIBLES = [
    "GLUCOSA",
    "GLUCOSA SERICA",
    "GLUCOSA SÉRICA",
    "GLUCOSA PLASMATICA",
    "GLUCOSA PLASMÁTICA",
    "GLUCOSA EN AYUNO",
    "GLICEMIA",
]


class Command(BaseCommand):
    help = (
        "Siembra parámetros clínicos en core.Parametro + core.RangoReferencia "
        "para estudios clave (CBC, Química Sanguínea, Glucosa). "
        "Idempotente: update_or_create, no duplica registros."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué haría pero no modifica la DB.',
        )
        parser.add_argument(
            '--solo-cbc',
            action='store_true',
            help='Solo siembra los parámetros de la CBC.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        dry = options.get('dry_run', False)
        solo_cbc = options.get('solo_cbc', False)

        from core.models import Estudio, Parametro, RangoReferencia

        modo = "SIMULACIÓN" if dry else "EJECUCIÓN"
        self.stdout.write(self.style.WARNING(
            f"\n{'='*60}\n  PRISLAB — Seed Parámetros Laboratorio [{modo}]\n{'='*60}\n"
        ))

        resultados = []

        # ── 1. CBC ────────────────────────────────────────────────────────────
        cbc_estudio = self._buscar_estudio(Estudio, CBC_NOMBRES_POSIBLES)
        if cbc_estudio:
            n = self._seed_estudio(cbc_estudio, CBC_PARAMETROS, Parametro, RangoReferencia, dry)
            resultados.append(f"CBC ({cbc_estudio.nombre}): {n} parámetros procesados")
        else:
            self.stdout.write(self.style.ERROR(
                "  ⚠  No se encontró la CBC en core.Estudio. "
                "Verifica que el estudio exista con alguno de estos nombres:\n"
                "  " + " | ".join(CBC_NOMBRES_POSIBLES[:4])
            ))
            resultados.append("CBC: estudio no encontrado en DB")

        if not solo_cbc:
            # ── 2. Química Sanguínea ──────────────────────────────────────────
            qs_estudio = self._buscar_estudio(Estudio, QUIM_NOMBRES_POSIBLES)
            if qs_estudio:
                n = self._seed_estudio(qs_estudio, QUIM_BASICA, Parametro, RangoReferencia, dry)
                resultados.append(f"Química Sanguínea ({qs_estudio.nombre}): {n} parámetros procesados")
            else:
                resultados.append("Química Sanguínea: estudio no encontrado (omitido)")

            # ── 3. Glucosa Simple ─────────────────────────────────────────────
            glu_estudio = self._buscar_estudio(Estudio, GLUCOSA_NOMBRES_POSIBLES)
            if glu_estudio:
                n = self._seed_estudio(glu_estudio, GLUCOSA_SIMPLE, Parametro, RangoReferencia, dry)
                resultados.append(f"Glucosa ({glu_estudio.nombre}): {n} parámetros procesados")
            else:
                resultados.append("Glucosa: estudio no encontrado (omitido)")

        # ── 4. Migración desde laboratorio.Parametro ─────────────────────────
        migrados = self._migrar_desde_legacy(Estudio, Parametro, RangoReferencia, dry)
        resultados.append(f"Migración legacy: {migrados} parámetros sincronizados")

        # Resumen
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}\n  RESUMEN\n{'='*60}"))
        for r in resultados:
            self.stdout.write(f"  ✓ {r}")
        if dry:
            self.stdout.write(self.style.WARNING(
                "\n  ℹ  Modo simulación: sin cambios en DB. "
                "Ejecuta sin --dry-run para aplicar.\n"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("\n  Parámetros sembrados exitosamente.\n"))

    # ─────────────────────────────────────────────────────────────────────────
    def _buscar_estudio(self, EstudioModel, nombres):
        """Busca un estudio por lista de nombres alternativos (case-insensitive)."""
        for nombre in nombres:
            est = EstudioModel.objects.filter(nombre__iexact=nombre).first()
            if est:
                return est
        # Segundo intento: búsqueda parcial
        for nombre in nombres:
            est = EstudioModel.objects.filter(nombre__icontains=nombre[:10]).first()
            if est:
                return est
        return None

    def _seed_estudio(self, estudio, parametros_data, ParaModel, RangoModel, dry):
        """Crea/actualiza parámetros y rangos para un estudio dado."""
        count = 0
        for row in parametros_data:
            nombre, abrev, unidad, m_min, m_max, f_min, f_max, pan_min, pan_max, orden = row
            # Garantizar abreviatura no vacía (unique_together requiere valor no NULL)
            abrev_safe = (abrev or '').strip() or nombre[:10].strip()
            self.stdout.write(
                f"  {'[DRY]' if dry else '    '} {estudio.codigo or '?'} | "
                f"{nombre} ({abrev_safe}) — {unidad}"
            )
            if not dry:
                # Lookup por (estudio, nombre) — más estable que abreviatura (puede ser NULL)
                param, _ = ParaModel.objects.update_or_create(
                    estudio=estudio,
                    nombre=nombre,
                    defaults={
                        'abreviatura': abrev_safe or None,
                        'unidad': unidad,
                        'orden_impresion': orden,
                        'activo': True,
                    }
                )
                # Rango Masculino (o indistinto si M==F)
                sexo_m = 'I' if (m_min == f_min and m_max == f_max) else 'M'
                if m_min is not None or m_max is not None:
                    RangoModel.objects.update_or_create(
                        parametro=param,
                        sexo=sexo_m,
                        edad_minima=None,
                        edad_maxima=None,
                        defaults={
                            'valor_minimo': m_min,
                            'valor_maximo': m_max,
                            'panico_minimo': pan_min,
                            'panico_maximo': pan_max,
                            'activo': True,
                        }
                    )
                # Rango Femenino (solo si difiere del masculino)
                if sexo_m == 'M' and (f_min is not None or f_max is not None):
                    RangoModel.objects.update_or_create(
                        parametro=param,
                        sexo='F',
                        edad_minima=None,
                        edad_maxima=None,
                        defaults={
                            'valor_minimo': f_min,
                            'valor_maximo': f_max,
                            'panico_minimo': pan_min,
                            'panico_maximo': pan_max,
                            'activo': True,
                        }
                    )
            count += 1
        return count

    def _migrar_desde_legacy(self, EstudioModel, ParaModel, RangoModel, dry):
        """
        Copia laboratorio.Parametro → core.Parametro para todos los estudios
        que ya existen en core.Estudio por código coincidente.
        """
        migrados = 0
        try:
            from laboratorio.models import Parametro as LegParam
            from laboratorio.models import Estudio as LegEstudio

            # Mapa codigo → core.Estudio
            core_estudios = {
                e.codigo.upper(): e
                for e in EstudioModel.objects.exclude(codigo__isnull=True).exclude(codigo='')
            }

            for leg_param in LegParam.objects.select_related('estudio').filter(activo=True):
                leg_est = leg_param.estudio
                codigo = (leg_est.codigo or '').strip().upper()
                core_est = core_estudios.get(codigo)
                if not core_est:
                    continue

                abrev = (leg_param.abreviatura or leg_param.nombre[:10]).strip() or leg_param.nombre[:10].strip()
                self.stdout.write(
                    f"  {'[DRY]' if dry else 'SYNC'} {codigo} | "
                    f"{leg_param.nombre} ({abrev})"
                )

                if not dry:
                    param, _ = ParaModel.objects.update_or_create(
                        estudio=core_est,
                        nombre=leg_param.nombre,
                        defaults={
                            'abreviatura': abrev or None,
                            'unidad': leg_param.unidades or leg_param.unidad or '',
                            'orden_impresion': getattr(leg_param, 'orden_impresion', 0) or 0,
                            'activo': True,
                        }
                    )
                    # Rangos del modelo legacy
                    for rango in leg_param.rangos_referencia.all()[:4]:
                        sexo = getattr(rango, 'sexo', 'I') or 'I'
                        if sexo not in ('M', 'F', 'I'):
                            sexo = 'I'
                        RangoModel.objects.update_or_create(
                            parametro=param,
                            sexo=sexo,
                            edad_minima=getattr(rango, 'edad_minima', None),
                            edad_maxima=getattr(rango, 'edad_maxima', None),
                            defaults={
                                'valor_minimo': getattr(rango, 'valor_minimo', None),
                                'valor_maximo': getattr(rango, 'valor_maximo', None),
                                'panico_minimo': getattr(rango, 'valor_critico_bajo', None)
                                                 or getattr(rango, 'panico_minimo', None),
                                'panico_maximo': getattr(rango, 'valor_critico_alto', None)
                                                 or getattr(rango, 'panico_maximo', None),
                                'activo': True,
                            }
                        )
                migrados += 1
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en _migrar_desde_legacy (seed_parametros_lab.py)")
            self.stdout.write(self.style.WARNING(
                f"  ⚠  Migración legacy saltada: {exc}"
            ))
        return migrados