"""
PRISLAB V5.0 - COMMAND: CREAR GRUPOS DE DJANGO
===============================================
Fecha: 1 de Febrero de 2026
Objetivo: Crear grupos de Django para segregación de roles

Uso:
    python manage.py crear_grupos_roles
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
import logging


class Command(BaseCommand):
    help = 'Crea los grupos de Django necesarios para PRISLAB V5.0'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Iniciando creación de grupos...'))
        
        # ==============================================================================
        # DEFINICIÓN DE GRUPOS Y PERMISOS
        # ==============================================================================
        
        grupos_config = {
            'MEDICOS': {
                'descripcion': 'Personal médico (doctores, especialistas)',
                'permisos': [
                    # Consultas
                    'add_consultamedica',
                    'change_consultamedica',
                    'view_consultamedica',
                    # Pacientes
                    'add_paciente',
                    'change_paciente',
                    'view_paciente',
                    # Recetas
                    'add_receta',
                    'change_receta',
                    'view_receta',
                ]
            },
            'LABORATORIO': {
                'descripcion': 'Personal de laboratorio (químicos, técnicos)',
                'permisos': [
                    # Órdenes de servicio
                    'add_ordendeservicio',
                    'change_ordendeservicio',
                    'view_ordendeservicio',
                    # Resultados
                    'add_resultadoparametro',
                    'change_resultadoparametro',
                    'view_resultadoparametro',
                    # Pacientes (solo lectura)
                    'view_paciente',
                ]
            },
            'FARMACIA': {
                'descripcion': 'Personal de farmacia (cajeros, auxiliares)',
                'permisos': [
                    # Ventas
                    'add_venta',
                    'change_venta',
                    'view_venta',
                    # Productos
                    'view_producto',
                    'change_producto',
                    # Pacientes (solo lectura)
                    'view_paciente',
                ]
            },
            'RECEPCION': {
                'descripcion': 'Personal de recepción',
                'permisos': [
                    # Citas
                    'add_agendacita',
                    'change_agendacita',
                    'view_agendacita',
                    # Pacientes
                    'add_paciente',
                    'change_paciente',
                    'view_paciente',
                    # Órdenes (solo crear y ver)
                    'add_ordendeservicio',
                    'view_ordendeservicio',
                ]
            },
            'ENFERMERIA': {
                'descripcion': 'Personal de enfermería',
                'permisos': [
                    # Pacientes
                    'view_paciente',
                    'change_paciente',
                    # Somatometría
                    'add_somatometria',
                    'change_somatometria',
                    'view_somatometria',
                    # Consultas (solo ver)
                    'view_consultamedica',
                ]
            },
            'GERENCIA': {
                'descripcion': 'Gerencia y administración',
                'permisos': [
                    # Acceso a todo (se configurará manualmente)
                ]
            },
        }
        
        # ==============================================================================
        # CREAR GRUPOS
        # ==============================================================================
        
        grupos_creados = 0
        grupos_existentes = 0
        
        for grupo_nombre, config in grupos_config.items():
            # Crear o obtener grupo
            grupo, created = Group.objects.get_or_create(name=grupo_nombre)
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'[OK] Grupo creado: {grupo_nombre}')
                )
                grupos_creados += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'  Grupo ya existe: {grupo_nombre}')
                )
                grupos_existentes += 1
            
            # Agregar permisos
            permisos_agregados = 0
            for permiso_codename in config['permisos']:
                try:
                    # Buscar permiso (puede tener formato app.codename)
                    if '.' in permiso_codename:
                        app_label, codename = permiso_codename.split('.')
                        permiso = Permission.objects.get(
                            codename=codename,
                            content_type__app_label=app_label
                        )
                    else:
                        permiso = Permission.objects.get(codename=permiso_codename)
                    
                    grupo.permissions.add(permiso)
                    permisos_agregados += 1
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'    [!] Permiso no encontrado: {permiso_codename}')
                    )
                except Exception as e:
                    logging.getLogger(__name__).exception("Error inesperado en handle (crear_grupos_roles.py)")
                    self.stdout.write(
                        self.style.ERROR(f'    [X] Error con permiso {permiso_codename}: {e}')
                    )
            
            if permisos_agregados > 0:
                self.stdout.write(
                    f'    -> {permisos_agregados} permisos asignados'
                )
        
        # ==============================================================================
        # RESUMEN
        # ==============================================================================
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('RESUMEN:'))
        self.stdout.write(self.style.SUCCESS(f'  Grupos creados: {grupos_creados}'))
        self.stdout.write(self.style.SUCCESS(f'  Grupos existentes: {grupos_existentes}'))
        self.stdout.write(self.style.SUCCESS(f'  Total de grupos: {len(grupos_config)}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS('[OK] Comando completado exitosamente'))
        self.stdout.write('')
        self.stdout.write('Grupos disponibles:')
        for grupo_nombre, config in grupos_config.items():
            self.stdout.write(f'  - {grupo_nombre}: {config["descripcion"]}')