import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from laboratorio.models import CategoriaExamen, Estudio


class Command(BaseCommand):
    help = 'Importa catálogo de laboratorio desde CSV con redondeo'

    def handle(self, *args, **options):
        # 1. Busca el archivo tarifas.csv en la raíz del proyecto
        file_path = os.path.join(settings.BASE_DIR, 'tarifas.csv')
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR('[ERROR] No encuentro "tarifas.csv" en la carpeta raiz.'))
            return

        self.stdout.write(self.style.WARNING('[INFO] Iniciando carga masiva...'))
        
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as file:
                reader = csv.reader(file)
                
                # Tu archivo tiene basura al inicio, buscamos el header real
                header_found = False
                count = 0
                
                for row in reader:
                    # Buscamos la fila que empieza con "Tipo" y "Código"
                    if not header_found:
                        if len(row) > 1 and 'Tipo' in row[0] and 'Código' in row[1]:
                            header_found = True
                        continue

                    # Mapeo de columnas según tu archivo:
                    # 0: Tipo (Paquetes/Pruebas)
                    # 1: Código
                    # 3: Descripción (Nombre)
                    # 4: Importe (Precio)
                    # 5: Tiempo Proceso
                    # 6: Indicaciones
                    # 7: Estudios Incluidos
                    # 8: Tipo Muestra
                    
                    try:
                        tipo = row[0].strip() if len(row) > 0 else ""
                        codigo = row[1].strip() if len(row) > 1 else ""
                        nombre = row[3].strip() if len(row) > 3 else ""
                        precio_raw = row[4].strip() if len(row) > 4 else ""
                        tiempo = row[5].strip() if len(row) > 5 else ""
                        indicaciones = row[6].strip() if len(row) > 6 else ""
                        incluidos = row[7].strip() if len(row) > 7 else ""
                        muestra = row[8].strip() if len(row) > 8 else ""

                        if not codigo or not nombre:
                            continue

                        # LÓGICA DE REDONDEO A 0 o 5
                        precio_final = 0
                        if precio_raw:
                            try:
                                val = float(precio_raw.replace('$', '').replace(',', '').strip())
                                # Redondeo al múltiplo de 5 más cercano
                                precio_final = 5 * round(val / 5)
                            except:
                                precio_final = 0

                        # Categoría
                        cat_nombre = "PAQUETES" if "Paquetes" in tipo else "ESTUDIOS INDIVIDUALES"
                        categoria, _ = CategoriaExamen.objects.get_or_create(nombre=cat_nombre)

                        # Crear/Actualizar Estudio
                        Estudio.objects.update_or_create(
                            codigo=codigo,
                            defaults={
                                'nombre': nombre,
                                'categoria': categoria,
                                'precio_base': precio_final,
                                'dias_entrega': tiempo,  # Guardamos el texto completo ej: "2 días"
                                'indicaciones': indicaciones,
                                'muestra_requerida': muestra,
                                'descripcion_interna': incluidos,  # Aquí guardamos qué trae el paquete
                                'es_perfil': True if "Paquetes" in tipo else False
                            }
                        )
                        count += 1
                        
                        if count % 50 == 0:
                            self.stdout.write(f'  [PROGRESO] Procesados: {count} estudios...')
                        
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'[ADVERTENCIA] Error en fila {row}: {e}'))
                        continue

            self.stdout.write(self.style.SUCCESS(f'[EXITO] LISTO! {count} estudios importados/actualizados.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Error abriendo archivo: {e}'))
