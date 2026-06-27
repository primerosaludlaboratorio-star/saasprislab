"""
Comando de Management: Crear Perfiles de Química Clínica

Este comando agrupa los estudios de Química Clínica en perfiles estándar:
- Química Básica (6 estudios)
- Perfil Hepático
- Perfil de Lípidos
- Perfil Renal
- Perfil de Electrolitos

Utiliza los códigos y nombres del catálogo maestro cargado.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from laboratorio.models import CategoriaExamen, Estudio, PerfilLaboratorio


class Command(BaseCommand):
    help = 'Crea perfiles estándar de Química Clínica agrupando estudios del catálogo maestro'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización de perfiles existentes',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        try:
            # Obtener categoría de Química Clínica
            categoria_quimica = CategoriaExamen.objects.get(nombre='Química Clínica')
        except CategoriaExamen.DoesNotExist:
            self.stdout.write(self.style.ERROR('[ERROR] La categoría "Química Clínica" no existe. Ejecuta primero: python manage.py cargar_catalogo_pruebas'))
            return
        
        # Definir perfiles estándar
        perfiles_config = {
            'Química Básica': {
                'descripcion': 'Perfil básico de química clínica con 6 estudios fundamentales',
                'codigos_estudios': ['QUI-001', 'QUI-002', 'QUI-003', 'QUI-004', 'QUI-005', 'QUI-006'],
                'precio': Decimal('350.00'),
            },
            'Perfil Hepático': {
                'descripcion': 'Perfil completo de función hepática',
                'codigos_estudios': ['QUI-010', 'QUI-011', 'QUI-012', 'QUI-013', 'QUI-014', 'QUI-015', 'QUI-016', 'QUI-017'],
                'precio': Decimal('450.00'),
            },
            'Perfil de Lípidos': {
                'descripcion': 'Perfil completo de lípidos séricos',
                'codigos_estudios': ['QUI-006', 'QUI-007', 'QUI-008', 'QUI-009'],
                'precio': Decimal('300.00'),
            },
            'Perfil Renal': {
                'descripcion': 'Perfil completo de función renal',
                'codigos_estudios': ['QUI-002', 'QUI-003', 'QUI-004', 'QUI-005'],
                'precio': Decimal('250.00'),
            },
            'Perfil de Electrolitos': {
                'descripcion': 'Perfil completo de electrolitos séricos',
                'codigos_estudios': ['QUI-018', 'QUI-019', 'QUI-020', 'QUI-021'],
                'precio': Decimal('200.00'),
            },
        }
        
        self.stdout.write(self.style.SUCCESS(f'\n[INICIO] Creando Perfiles de {categoria_quimica.nombre}...\n'))
        
        perfiles_creados = 0
        perfiles_actualizados = 0
        errores = 0
        
        try:
            with transaction.atomic():
                for nombre_perfil, config in perfiles_config.items():
                    try:
                        # Obtener estudios por código
                        estudios = []
                        codigos_no_encontrados = []
                        
                        for codigo in config['codigos_estudios']:
                            try:
                                estudio = Estudio.objects.get(codigo=codigo, categoria=categoria_quimica)
                                estudios.append(estudio)
                            except Estudio.DoesNotExist:
                                codigos_no_encontrados.append(codigo)
                        
                        if codigos_no_encontrados:
                            self.stdout.write(self.style.WARNING(f'  [ADVERTENCIA] {nombre_perfil}: No se encontraron estudios: {", ".join(codigos_no_encontrados)}'))
                        
                        if not estudios:
                            self.stdout.write(self.style.ERROR(f'  [ERROR] {nombre_perfil}: No se encontraron estudios válidos, omitiendo...'))
                            errores += 1
                            continue
                        
                        # Crear o actualizar perfil
                        perfil, creado = PerfilLaboratorio.objects.get_or_create(
                            nombre=nombre_perfil,
                            defaults={
                                'descripcion': config['descripcion'],
                                'precio': config['precio'],
                                'area_pertenencia': categoria_quimica,
                                'activo': True,
                            }
                        )
                        
                        if creado:
                            # Asignar estudios al perfil
                            perfil.pruebas.set(estudios)
                            perfiles_creados += 1
                            precio_individual = sum(e.precio_base for e in estudios)
                            ahorro = precio_individual - perfil.precio
                            self.stdout.write(self.style.SUCCESS(f'  [OK] Perfil creado: {nombre_perfil} - {len(estudios)} estudios - Precio: ${perfil.precio} (Individual: ${precio_individual}, Ahorro: ${ahorro:.2f})'))
                        else:
                            if force:
                                perfil.descripcion = config['descripcion']
                                perfil.precio = config['precio']
                                perfil.area_pertenencia = categoria_quimica
                                perfil.activo = True
                                perfil.pruebas.set(estudios)
                                perfil.save()
                                perfiles_actualizados += 1
                                precio_individual = sum(e.precio_base for e in estudios)
                                ahorro = precio_individual - perfil.precio
                                self.stdout.write(self.style.WARNING(f'  [ACTUALIZADO] Perfil: {nombre_perfil} - {len(estudios)} estudios - Precio: ${perfil.precio} (Individual: ${precio_individual}, Ahorro: ${ahorro:.2f})'))
                            else:
                                self.stdout.write(self.style.WARNING(f'  [EXISTE] Perfil: {nombre_perfil} (usa --force para actualizar)'))
                        
                    except django.core.exceptions.ValidationError as e:
                        self.stdout.write(self.style.ERROR(f'  [ERROR] {nombre_perfil}: Error de validación - {str(e)}'))
                        errores += 1
                        continue
                    except IntegrityError as e:
                        self.stdout.write(self.style.ERROR(f'  [ERROR] {nombre_perfil}: Error de integridad - {str(e)}'))
                        errores += 1
                        continue
                    except ValueError as e:
                        self.stdout.write(self.style.ERROR(f'  [ERROR] {nombre_perfil}: Error de valor - {str(e)}'))
                        errores += 1
                        continue
                    except DatabaseError as e:
                        self.stdout.write(self.style.ERROR(f'  [ERROR] {nombre_perfil}: Error de base de datos - {str(e)}'))
                        errores += 1
                        continue
                
                # Resumen final
                total_perfiles = PerfilLaboratorio.objects.filter(area_pertenencia=categoria_quimica).count()
                
                self.stdout.write(self.style.SUCCESS('\n' + '='*60))
                self.stdout.write(self.style.SUCCESS('[COMPLETADO] CREACIÓN DE PERFILES FINALIZADA'))
                self.stdout.write(self.style.SUCCESS('='*60))
                self.stdout.write(f'\nResumen:')
                self.stdout.write(f'   - Perfiles nuevos: {perfiles_creados}')
                self.stdout.write(f'   - Perfiles actualizados: {perfiles_actualizados}')
                self.stdout.write(f'   - Errores: {errores}')
                self.stdout.write(f'   - Total de perfiles en {categoria_quimica.nombre}: {total_perfiles}')
                self.stdout.write(self.style.SUCCESS(f'\n[EXITO] Perfiles de Química Clínica creados exitosamente!\n'))
                
        except ValidationError as e:
            logger.error(f"Validacion fallida: {e}")
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Error durante la creación: {str(e)}'))
            self.stdout.write(self.style.ERROR('   La transacción ha sido revertida.'))
            raise
        except IntegrityError as e:
            logger.error(f"Error BD integridad: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Error durante la creación: {str(e)}'))
            self.stdout.write(self.style.ERROR('   La transacción ha sido revertida.'))
            raise
        except ValueError as e:
            logger.error(f"ValueError: {e}")
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Error durante la creación: {str(e)}'))
            self.stdout.write(self.style.ERROR('   La transacción ha sido revertida.'))
            raise
        except Exception as e:
            logger.critical(f"Error desconocido: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Error durante la creación: {str(e)}'))
            self.stdout.write(self.style.ERROR('   La transacción ha sido revertida.'))
            raise
