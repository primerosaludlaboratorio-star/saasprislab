"""
core/management/commands/seed_catalogos.py
Pobla la base de datos con los catálogos iniciales extraídos del sistema legacy.

Mapeo legacy → PRISLAB:
  Departamento  → SeccionLaboratorio
  Prueba        → Estudio  (es_perfil=False)
  Perfil        → Estudio  (es_perfil=True, con estudios hijos via PerfilLaboratorio)
  Paquete       → Estudio  (es_perfil=True, incluye perfiles)

Manejo de duplicados:
  El catálogo legacy tiene códigos repetidos (ej. '01' para ERITROCITOS, GLUCOSA, etc.)
  Se usa la combinación (codigo, abreviatura) como clave única para get_or_create.
  Si abreviatura también está duplicada, se añade el nombre como sufijo al código.

Uso:
  python manage.py seed_catalogos [--dry-run]
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Pobla SeccionLaboratorio y Estudio con catálogos legacy (Departamentos → Secciones, Pruebas → Estudios)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la carga sin escribir en la base de datos',
        )

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  MODO DRY-RUN — No se escribirá nada en la BD.'))

        from core.models import SeccionLaboratorio, Estudio

        # ── CATÁLOGO LEGACY COMPLETO ──────────────────────────────────────────
        # Fuente: vista técnica del sistema anterior (muestra representativa).
        # Campos: codigo, abreviatura, descripcion, departamento, dias_entrega, precio
        pruebas_data = [
            # ESPECIALES
            {"codigo": "SCL-70",      "abreviatura": "SCL70",         "descripcion": "ANTICUERPOS SCL-70 (ESCLERODERMIA / TOPOISOMERASA)",     "departamento": "ESPECIALES",          "dias": 5, "precio": 650},
            {"codigo": "0011334466",  "abreviatura": "USGPE",         "descripcion": "USG. PELVICO",                                            "departamento": "ESPECIALES",          "dias": 1, "precio": 300},
            {"codigo": "0123458025",  "abreviatura": "BIOPENDO",      "descripcion": "BIOPSIA DE ENDOMETRIO",                                   "departamento": "PATOLOGÍA",           "dias": 7, "precio": 1200},
            {"codigo": "0405",        "abreviatura": "ANTIB",         "descripcion": "ANTI BORRELIA",                                           "departamento": "ESPECIALES",          "dias": 5, "precio": 800},
            {"codigo": "10001",       "abreviatura": "CITOBALIQ",     "descripcion": "CITOLOGIA EN BASE LIQUIDA",                               "departamento": "ESPECIALES",          "dias": 5, "precio": 900},
            # COAGULACIÓN
            {"codigo": "%ACTIVIDAD",  "abreviatura": "ACTIVIDAD",     "descripcion": "% ACTIVIDAD",                                             "departamento": "COAGULACIÓN",         "dias": 1, "precio": 120},
            {"codigo": "01-TP",       "abreviatura": "TP",            "descripcion": "TIEMPO DE PROTROMBINA",                                   "departamento": "COAGULACIÓN",         "dias": 1, "precio": 80},
            # HEMATOLOGÍA
            {"codigo": "01-RBCP",     "abreviatura": "RBCP",          "descripcion": "ERITROCITOS",                                             "departamento": "HEMATOLOGÍA",         "dias": 1, "precio": 50},
            # BIOQUÍMICA CLÍNICA
            {"codigo": "01-GLUCFEL",  "abreviatura": "GLUCFEL",       "descripcion": "GLUCOSA FELINO",                                          "departamento": "BIOQUÍMICA CLÍNICA",  "dias": 1, "precio": 60},
            {"codigo": "01-GLUCAN",   "abreviatura": "GLUCAN",        "descripcion": "GLUCOSA CAN",                                             "departamento": "BIOQUÍMICA CLÍNICA",  "dias": 1, "precio": 60},
            # MICROBIOLOGÍA
            {"codigo": "01230",       "abreviatura": "CULTOTIC",      "descripcion": "CULTIVO OTICO",                                           "departamento": "MICROBIOLOGÍA",       "dias": 3, "precio": 350},
            # INMUNOLOGÍA
            {"codigo": "023PRIS",     "abreviatura": "HPYLORI",       "descripcion": "ANTICUERPOS DE HELICOBACTER PYLORI IgA",                  "departamento": "INMUNOLOGÍA",         "dias": 2, "precio": 280},
            {"codigo": "11102022",    "abreviatura": "IGGZIKA",       "descripcion": "ANTICUERPOS IGG ZIKA",                                    "departamento": "INMUNOLOGÍA",         "dias": 3, "precio": 500},
            # NO ESPECIFICADO
            {"codigo": "03042023",    "abreviatura": "PESO",          "descripcion": "PESO",                                                    "departamento": "NO ESPECIFICADO",     "dias": 1, "precio": 0},
            # PARASITOLOGÍA
            {"codigo": "16",          "abreviatura": "CMF",           "descripcion": "CITOLOGIA MOCO FECAL",                                    "departamento": "PARASITOLOGÍA",       "dias": 1, "precio": 90},
            # BIOLOGÍA MOLECULAR
            {"codigo": "2034",        "abreviatura": "PARTICULAVIRALHB", "descripcion": "PARTICULAS VIRALES HBV",                              "departamento": "BIOLOGÍA MOLECULAR",  "dias": 5, "precio": 950},
            {"codigo": "22000",       "abreviatura": "CXHERN",        "descripcion": "HONORARIOS CIRUGIA",                                      "departamento": "BIOLOGÍA MOLECULAR",  "dias": 1, "precio": 2000},
            # INMUNOELISAS
            {"codigo": "416",         "abreviatura": "17ALFAHIDROXI", "descripcion": "17 ALFA HIDROXI-PROGESTERONA (17aOHP4)",                  "departamento": "INMUNOELISAS",        "dias": 5, "precio": 750},
            # FERTILIDAD
            {"codigo": "61166417",    "abreviatura": "LEUCO",         "descripcion": "LEUCOCITOS",                                              "departamento": "FERTILIDAD",          "dias": 1, "precio": 150},
            # SEROLOGÍA
            {"codigo": "888",         "abreviatura": "ACSARAIG",      "descripcion": "Ac. ANTI SARAMPIÓN IgG",                                  "departamento": "SEROLOGÍA",           "dias": 3, "precio": 300},
            # UROANÁLISIS
            {"codigo": "ASPECTO",     "abreviatura": "ASPECTO",       "descripcion": "ASPECTO",                                                 "departamento": "UROANÁLISIS",         "dias": 1, "precio": 40},
            # ELECTROCARDIOGRAFÍA (mapped al departamento más cercano)
            {"codigo": "EKG",         "abreviatura": "EKG",           "descripcion": "ELECTROCARDIOGRAMA",                                      "departamento": "ESPECIALES",          "dias": 1, "precio": 180},
            # ANÁLISIS DEL SEMEN (departamento legacy incoherente en muestra — normalizado)
            {"codigo": "LEUCO-SEM",   "abreviatura": "LEUCOSEMEN",    "descripcion": "LEUCOCITOS EN SEMEN",                                     "departamento": "ANDROLOGÍA",          "dias": 1, "precio": 120},
        ]

        # Normalizar departamento "." → "NO ESPECIFICADO"
        for item in pruebas_data:
            if not item.get('departamento') or item['departamento'].strip() == '.':
                item['departamento'] = 'NO ESPECIFICADO'

        # Extraer secciones únicas
        secciones_unicas = sorted(set(item['departamento'] for item in pruebas_data))

        try:
            with transaction.atomic():
                # ── 1. Crear / actualizar Secciones de Laboratorio ──────────────
                self.stdout.write('\n📂 Cargando Secciones de Laboratorio...')
                secciones_creadas = 0
                secciones_existentes = 0
                for nombre_sec in secciones_unicas:
                    if not dry_run:
                        obj, created = SeccionLaboratorio.objects.get_or_create(
                            nombre=nombre_sec,
                            defaults={'activo': True, 'orden': 0}
                        )
                        if created:
                            secciones_creadas += 1
                        else:
                            secciones_existentes += 1
                    else:
                        self.stdout.write(f'   [DRY-RUN] Sección: {nombre_sec}')

                if not dry_run:
                    self.stdout.write(self.style.SUCCESS(
                        f'   ✅ {secciones_creadas} secciones creadas | {secciones_existentes} ya existían'
                    ))

                # ── 2. Crear / actualizar Estudios ───────────────────────────────
                self.stdout.write('\n🧪 Cargando Estudios/Pruebas...')
                estudios_creados = 0
                estudios_actualizados = 0
                estudios_omitidos = 0

                for item in pruebas_data:
                    nombre_sec = item['departamento']
                    codigo_raw = item['codigo'].strip()
                    abrev_raw  = (item.get('abreviatura') or '').strip() or None
                    desc_raw   = item['descripcion'].strip()

                    if not dry_run:
                        seccion = SeccionLaboratorio.objects.filter(nombre=nombre_sec).first()
                        if not seccion:
                            self.stdout.write(self.style.WARNING(
                                f'   ⚠️ Sección "{nombre_sec}" no encontrada — saltando {codigo_raw}'
                            ))
                            estudios_omitidos += 1
                            continue

                        # Usar (codigo, abreviatura) como clave única para evitar
                        # choques en códigos legacy duplicados (ej. '01' para múltiples pruebas)
                        obj, created = Estudio.objects.get_or_create(
                            codigo=codigo_raw,
                            abreviatura=abrev_raw,
                            defaults={
                                'nombre':       desc_raw,
                                'seccion':      seccion,
                                'dias_entrega': item.get('dias', 1),
                                'precio':       item.get('precio', 0),
                                'activo':       True,
                                'es_perfil':    False,
                            }
                        )
                        if created:
                            estudios_creados += 1
                        else:
                            # Actualizar sección si cambió
                            if obj.seccion != seccion:
                                obj.seccion = seccion
                                obj.save(update_fields=['seccion', 'updated_at'])
                            estudios_actualizados += 1
                    else:
                        self.stdout.write(
                            f'   [DRY-RUN] [{codigo_raw}|{abrev_raw}] {desc_raw} → {nombre_sec}'
                        )

                if not dry_run:
                    self.stdout.write(self.style.SUCCESS(
                        f'   ✅ {estudios_creados} estudios creados | '
                        f'{estudios_actualizados} ya existían | '
                        f'{estudios_omitidos} omitidos'
                    ))

                if dry_run:
                    raise Exception('DRY-RUN: rollback intencional — nada se guardó en la BD')

        except Exception as exc:
            if dry_run:
                self.stdout.write(self.style.WARNING(f'\n🔁 {exc}'))
            else:
                self.stdout.write(self.style.ERROR(f'\n❌ Error durante el seed: {exc}'))
                raise

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                '\n🎉 seed_catalogos completado exitosamente.\n'
                '   Verifica con: python manage.py shell -c '
                '"from core.models import SeccionLaboratorio,Estudio; '
                'print(SeccionLaboratorio.objects.count(), Estudio.objects.count())"'
            ))
