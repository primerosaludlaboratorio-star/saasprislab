"""
Importación lógica de catálogos legacy (PRISLAB).

Fases:
1) Áreas (departamentos) y tipos de muestra
2) Estudios base + configuración técnica desde Parametros.csv
3) Parámetros clínicos y rangos desde Valores_normalidad.csv
4) Armado de perfiles/paquetes y vínculos de componentes

Uso:
    python manage.py importar_catalogos_legacy
    python manage.py importar_catalogos_legacy --legacy-dir legacy
    python manage.py importar_catalogos_legacy --legacy-dir datos_lims
"""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


BOOL_TRUE = {"1", "SI", "SÍ", "TRUE", "YES", "Y", "ON"}


def clean(val) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() in {"nan", "none"} else s


def as_bool(val) -> bool:
    return clean(val).upper() in BOOL_TRUE


def as_int(val, default=None):
    s = clean(val)
    if not s:
        return default
    try:
        return int(float(s))
    except Exception:
        return default


def as_decimal(val):
    s = clean(val).replace(",", "").replace("$", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def map_tipo_dato(tipo_resultado: str, resultado_opciones: str) -> str:
    t = clean(tipo_resultado).upper()
    op = clean(resultado_opciones)
    if "POSITIVO" in t or "NEGATIVO" in t:
        return "POSITIVO_NEGATIVO"
    if "PRESENTE" in t or "AUSENTE" in t:
        return "PRESENTE_AUSENTE"
    if "LISTA" in t or "DESPLEG" in t or op:
        return "TEXTO_PREDEFINIDO"
    if "NUM" in t:
        return "NUMERICO"
    return "TEXTO"


def map_sexo(val: str) -> str:
    s = clean(val).upper()
    if s in {"F", "FEMENINO"} or "FEM" in s:
        return "F"
    if s in {"M", "MASCULINO"} or "MASC" in s:
        return "M"
    return "I"


def edad_a_anios(edad_val, unidad_raw: str, es_min: bool):
    edad = as_int(edad_val)
    if edad is None:
        return None

    u = clean(unidad_raw).lower()
    if "dia" in u:
        years = edad / 365.0
    elif "mes" in u:
        years = edad / 12.0
    else:
        years = float(edad)

    return int(math.floor(years) if es_min else math.ceil(years))


def read_csv(path: Path) -> "pd.DataFrame":
    return pd.read_csv(path, encoding="latin1", dtype=str).fillna("")


def read_double_header_rows(path: Path):
    """
    CSVs con doble encabezado (Examenes_Perfil / Paquetes_Perfil).
    Regresa filas de datos crudas (saltando 2 filas de header).
    """
    df = pd.read_csv(path, encoding="latin1", dtype=str, header=None).fillna("")
    if len(df.index) <= 2:
        return []
    return df.iloc[2:].values.tolist()


class Command(BaseCommand):
    help = "Importa catálogos legacy (parametros/examenes/perfiles/paquetes/valores de normalidad)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--legacy-dir",
            type=str,
            default="legacy",
            help="Directorio con CSVs legacy. Si no existe, se intenta datos_lims.",
        )

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        if pd is None:
            raise CommandError(
                "Falta pandas. Instala con: pip install pandas"
            )

        base = Path(settings.BASE_DIR) / options["legacy_dir"]
        if not base.exists():
            fallback = Path(settings.BASE_DIR) / "datos_lims"
            if fallback.exists():
                base = fallback
            else:
                raise CommandError(f"No existe {base} ni {fallback}")

        path_param = base / "Parametros.csv"
        path_exam = base / "Examenes.csv"
        path_perfiles = base / "Perfiles.csv"  # opcional
        path_paq = base / "Paquetes.csv"
        path_val = base / "Valores_normalidad.csv"
        path_exam_perfil = base / "Examenes_Perfil.csv"
        path_paq_perfil = base / "Paquetes_Perfil.csv"

        required = [path_param, path_exam, path_paq, path_val, path_exam_perfil, path_paq_perfil]
        missing = [p.name for p in required if not p.exists()]
        if missing:
            raise CommandError(f"Faltan archivos requeridos en {base}: {', '.join(missing)}")

        self.stdout.write(self.style.WARNING(f"Importando desde: {base}"))

        df_param = read_csv(path_param)
        df_exam = read_csv(path_exam)
        df_paq = read_csv(path_paq)
        df_val = read_csv(path_val)
        rows_exam_perfil = read_double_header_rows(path_exam_perfil)
        rows_paq_perfil = read_double_header_rows(path_paq_perfil)
        df_perfiles = read_csv(path_perfiles) if path_perfiles.exists() else None

        stats = {
            "areas": 0,
            "muestras": 0,
            "estudios_base": 0,
            "parametros": 0,
            "rangos": 0,
            "perfiles": 0,
            "paquetes": 0,
            "vinculos_perfiles": 0,
            "vinculos_paquetes": 0,
            "faltantes_vinculo": 0,
        }

        with transaction.atomic():
            # ==========================================================
            # FASE 1: Áreas del laboratorio + catálogo de tipos de muestra
            # ==========================================================
            areas = sorted({clean(v).upper() for v in df_param.get("Departamento", []) if clean(v)})
            for idx, area in enumerate(areas):
                SeccionLaboratorio.objects.get_or_create(
                    nombre=area,
                    defaults={"descripcion": f"Área legacy: {area}", "orden": idx, "activo": True},
                )
            stats["areas"] = len(areas)

            # No existe modelo dedicado de "Tipo de muestra" en este esquema.
            # Se consolida catálogo con valores únicos y se aplica en Estudio.muestra_requerida.
            muestras_catalogo = sorted({clean(v).upper() for v in df_param.get("Tipo_muestra", []) if clean(v)})
            stats["muestras"] = len(muestras_catalogo)

            secciones = {s.nombre.upper(): s for s in SeccionLaboratorio.objects.all()}

            # ==========================================================
            # FASE 2: Estudios base + configuración técnica (Parametros.csv)
            # ==========================================================
            parametro_por_id = {}
            estudio_base_por_codigo = {}

            for _, row in df_param.iterrows():
                codigo = clean(row.get("Codigo"))
                if not codigo:
                    continue

                abreviatura = clean(row.get("Abreviatura")) or codigo
                nombre = clean(row.get("Descripcion")) or abreviatura
                departamento = clean(row.get("Departamento")).upper()
                tipo_muestra = clean(row.get("Tipo_muestra")) or "Suero"
                metodo = clean(row.get("Metodo"))
                unidades = clean(row.get("Unidades"))
                tipo_resultado = clean(row.get("Tipo_resultado"))
                resultado_opciones = clean(row.get("Resultado_opciones"))
                tiempo_proceso = as_int(row.get("Tiempo_proceso"))
                permite_venta_directa = as_bool(row.get("Permite_venta_directa"))
                imprimir_metodo_resultado = as_bool(row.get("Imprimir_metodo_resultado"))
                costo = as_decimal(row.get("Costo")) or Decimal("0")
                texto_normalidad = clean(row.get("Valor de normalidad (texto libre)"))
                id_param = clean(row.get("Id_parametro"))

                seccion = secciones.get(departamento)
                tipo_dato = map_tipo_dato(tipo_resultado, resultado_opciones)

                metadata_legacy = (
                    f"legacy.permite_venta_directa={permite_venta_directa};"
                    f"legacy.imprimir_metodo_resultado={imprimir_metodo_resultado};"
                    f"legacy.tiempo_proceso={tiempo_proceso or ''}"
                )

                estudio, _ = Estudio.objects.update_or_create(
                    codigo=codigo,
                    defaults={
                        "abreviatura": abreviatura,
                        "nombre": nombre,
                        "seccion": seccion,
                        "es_perfil": False,
                        "muestra_requerida": tipo_muestra[:100],
                        "metodologia": metodo[:200] if metodo else "",
                        "unidad": unidades[:20] if unidades else "",
                        "tiempo_entrega_horas": tiempo_proceso,
                        "costo_operativo": costo,
                        "activo": True,
                        "descripcion_interna": metadata_legacy,
                    },
                )
                estudio_base_por_codigo[codigo.upper()] = estudio

                # Parámetro principal asociado a la prueba base.
                param_abrev = abreviatura[:50] if abreviatura else codigo[:50]
                parametro, _ = Parametro.objects.update_or_create(
                    estudio=estudio,
                    abreviatura=param_abrev,
                    defaults={
                        "nombre": nombre[:200],
                        "unidad": unidades[:50] if unidades else "",
                        "tipo_dato": tipo_dato,
                        "opciones_predefinidas": resultado_opciones[:5000] if resultado_opciones else "",
                        "orden_impresion": 0,
                        "metodologia": metodo[:200] if metodo else "",
                        "valor_default": clean(row.get("Resultado_default"))[:100],
                        "decimales_reporte": as_int(row.get("Decimales"), default=2) or 2,
                        "codigo_interfaz": codigo[:50],
                        "activo": True,
                    },
                )
                parametro_por_id[id_param] = parametro
                stats["parametros"] += 1

                # Referencia cualitativa directa desde Parametros.csv
                if texto_normalidad:
                    RangoReferencia.objects.update_or_create(
                        parametro=parametro,
                        sexo="I",
                        edad_minima=None,
                        edad_maxima=None,
                        defaults={
                            "texto_referencia": texto_normalidad[:5000],
                            "valor_minimo": None,
                            "valor_maximo": None,
                            "activo": True,
                        },
                    )
                    stats["rangos"] += 1

            stats["estudios_base"] = len(estudio_base_por_codigo)

            # ==========================================================
            # FASE 3: Rangos y referencias clínicas (Valores_normalidad.csv)
            # ==========================================================
            for _, row in df_val.iterrows():
                id_param = clean(row.get("Id_parametro"))
                codigo = clean(row.get("Codigo")).upper()
                parametro = parametro_por_id.get(id_param)

                # Fallback por código_interfaz cuando no coincide el Id.
                if not parametro and codigo:
                    parametro = Parametro.objects.filter(codigo_interfaz__iexact=codigo).first()
                if not parametro:
                    continue

                sexo = map_sexo(row.get("Sexo"))
                unidad_edad = clean(row.get("Unidad"))
                edad_min = edad_a_anios(row.get("Edad_min"), unidad_edad, es_min=True)
                edad_max = edad_a_anios(row.get("Edad_max"), unidad_edad, es_min=False)
                ref_min = as_decimal(row.get("Ref_min"))
                ref_max = as_decimal(row.get("Ref_max"))

                if ref_min is None and ref_max is None:
                    continue

                RangoReferencia.objects.update_or_create(
                    parametro=parametro,
                    sexo=sexo,
                    edad_minima=edad_min,
                    edad_maxima=edad_max,
                    defaults={
                        "valor_minimo": ref_min,
                        "valor_maximo": ref_max,
                        "texto_referencia": "",
                        "activo": True,
                    },
                )
                stats["rangos"] += 1

            # ==========================================================
            # FASE 4: Armado de perfiles y paquetes (solo vínculo, sin crear base)
            # ==========================================================
            perfil_por_codigo = {}

            # Examenes.csv -> perfiles multiestudio
            for _, row in df_exam.iterrows():
                codigo = clean(row.get("Codigo"))
                abreviatura = clean(row.get("Abreviatura")) or codigo
                nombre = clean(row.get("Titulo")) or clean(row.get("Descripcion")) or abreviatura
                if not abreviatura:
                    continue

                perfil, _ = Estudio.objects.update_or_create(
                    codigo=abreviatura,
                    defaults={
                        "abreviatura": abreviatura,
                        "nombre": nombre[:200],
                        "metodologia": clean(row.get("Metodo"))[:200],
                        "indicaciones": clean(row.get("Indicaciones"))[:5000],
                        "descripcion_interna": "TIPO_LIMS=PERFIL",
                        "es_perfil": True,
                        "activo": True,
                    },
                )
                perfil_por_codigo[codigo.upper()] = perfil
                perfil_por_codigo[abreviatura.upper()] = perfil
                stats["perfiles"] += 1

            # Perfiles.csv (opcional) -> también perfiles
            if df_perfiles is not None:
                for _, row in df_perfiles.iterrows():
                    codigo = clean(row.get("Codigo")) or clean(row.get("Abreviatura"))
                    nombre = clean(row.get("Titulo")) or clean(row.get("Descripcion")) or codigo
                    if not codigo:
                        continue
                    perfil, _ = Estudio.objects.update_or_create(
                        codigo=codigo,
                        defaults={
                            "abreviatura": clean(row.get("Abreviatura")) or codigo,
                            "nombre": nombre[:200],
                            "descripcion_interna": "TIPO_LIMS=PERFIL",
                            "es_perfil": True,
                            "activo": True,
                        },
                    )
                    perfil_por_codigo[codigo.upper()] = perfil
                    stats["perfiles"] += 1

            # Paquetes.csv -> paquetes comerciales
            paquete_por_codigo = {}
            for _, row in df_paq.iterrows():
                codigo = clean(row.get("Abreviatura"))
                if not codigo:
                    continue
                nombre = clean(row.get("Descripcion")) or codigo
                paquete, _ = Estudio.objects.update_or_create(
                    codigo=codigo,
                    defaults={
                        "abreviatura": codigo,
                        "nombre": nombre[:200],
                        "indicaciones": clean(row.get("Indicaciones"))[:5000],
                        "descripcion_interna": (
                            (clean(row.get("Notas_internas"))[:4800] + "\nTIPO_LIMS=PAQUETE").strip()
                        ),
                        "es_perfil": True,
                        "activo": True,
                    },
                )
                paquete_por_codigo[codigo.upper()] = paquete
                stats["paquetes"] += 1

            # Examenes_Perfil.csv: perfil -> pruebas base
            for row in rows_exam_perfil:
                if len(row) < 4:
                    continue
                codigo_examen = clean(row[0]).upper()
                codigo_prueba = clean(row[3]).upper()
                if not codigo_examen or not codigo_prueba:
                    continue

                perfil = perfil_por_codigo.get(codigo_examen)
                prueba = estudio_base_por_codigo.get(codigo_prueba)
                if not perfil or not prueba:
                    stats["faltantes_vinculo"] += 1
                    continue
                if perfil.id != prueba.id:
                    perfil.componentes.add(prueba)
                    stats["vinculos_perfiles"] += 1

            # Paquetes_Perfil.csv: paquete -> (perfil o prueba)
            for row in rows_paq_perfil:
                if len(row) < 4:
                    continue
                codigo_paq = clean(row[0]).upper()
                tipo_comp = clean(row[2]).upper()  # PERFIL / PRUEBA
                codigo_comp = clean(row[3]).upper()
                if not codigo_paq or not codigo_comp:
                    continue

                paquete = paquete_por_codigo.get(codigo_paq)
                if not paquete:
                    stats["faltantes_vinculo"] += 1
                    continue

                if "PERFIL" in tipo_comp:
                    componente = perfil_por_codigo.get(codigo_comp)
                else:
                    componente = estudio_base_por_codigo.get(codigo_comp) or perfil_por_codigo.get(codigo_comp)

                if not componente:
                    stats["faltantes_vinculo"] += 1
                    continue
                if paquete.id != componente.id:
                    paquete.componentes.add(componente)
                    stats["vinculos_paquetes"] += 1

        self.stdout.write(self.style.SUCCESS("=" * 72))
        self.stdout.write(self.style.SUCCESS("IMPORTACIÓN LEGACY COMPLETADA"))
        self.stdout.write(self.style.SUCCESS(f"Áreas creadas/aseguradas: {stats['areas']}"))
        self.stdout.write(self.style.SUCCESS(f"Tipos de muestra detectados: {stats['muestras']}"))
        self.stdout.write(self.style.SUCCESS(f"Estudios base: {stats['estudios_base']}"))
        self.stdout.write(self.style.SUCCESS(f"Parámetros procesados: {stats['parametros']}"))
        self.stdout.write(self.style.SUCCESS(f"Rangos procesados: {stats['rangos']}"))
        self.stdout.write(self.style.SUCCESS(f"Perfiles procesados: {stats['perfiles']}"))
        self.stdout.write(self.style.SUCCESS(f"Paquetes procesados: {stats['paquetes']}"))
        self.stdout.write(self.style.SUCCESS(f"Vínculos perfil->prueba: {stats['vinculos_perfiles']}"))
        self.stdout.write(self.style.SUCCESS(f"Vínculos paquete->componente: {stats['vinculos_paquetes']}"))
        self.stdout.write(self.style.WARNING(f"Vínculos con componentes faltantes: {stats['faltantes_vinculo']}"))
        self.stdout.write(self.style.SUCCESS("=" * 72))
