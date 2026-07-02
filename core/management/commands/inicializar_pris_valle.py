"""
Comando de Management: Inicialización tenant único (desarrollo PRISLAB).

Este comando:
1. Verifica/crea la empresa PRISLAB con colores corporativos
2. Crea la sucursal 'Matriz' vinculada a PRISLAB
3. Asigna usuarios sin empresa/sucursal a PRISLAB y Matriz
4. Crea ConfiguracionModulos con módulos activos

Multi-empresa se configurará más adelante; en desarrollo se asume una sola institución.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Empresa, Sucursal, ConfiguracionModulos, Usuario
import logging


class Command(BaseCommand):
    help = 'Inicializa empresa PRISLAB, sucursal Matriz y módulos (desarrollo tenant único)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar recreación incluso si ya existe configuración',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.SUCCESS('\n[INICIO] Inicializando PRISLAB (tenant único dev)...\n'))
        
        try:
            with transaction.atomic():
                # ============================================================
                # PASO 1: Verificar/Crear Empresa Prislab
                # ============================================================
                self.stdout.write('Paso 1: Verificando empresa Prislab...')
                
                empresa_prislab, created = Empresa.objects.get_or_create(
                    nombre='PRISLAB S.A. de C.V.',
                    defaults={
                        'periodo_vigencia': '2024-2030',
                        'color_primario': '#D9230F',  # Rojo Prislab
                        'color_secundario': '#2B3A42',  # Oxford Grey
                        'color_fondo': '#FFFFFF',  # Blanco
                        'activa': True,
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  [OK] Empresa "{empresa_prislab.nombre}" creada'))
                else:
                    # Si ya existe, actualizar colores si están vacíos o en force mode
                    if force or not empresa_prislab.color_primario or empresa_prislab.color_primario == '#D9230F':
                        empresa_prislab.color_primario = '#D9230F'
                        empresa_prislab.color_secundario = '#2B3A42'
                        empresa_prislab.color_fondo = '#FFFFFF'
                        empresa_prislab.activa = True
                        empresa_prislab.save()
                        self.stdout.write(self.style.SUCCESS(f'  [OK] Empresa "{empresa_prislab.nombre}" actualizada con colores corporativos'))
                    else:
                        self.stdout.write(self.style.WARNING(f'  [INFO] Empresa "{empresa_prislab.nombre}" ya existe'))
                
                # ============================================================
                # PASO 2: Crear Sucursal Matriz
                # ============================================================
                self.stdout.write('\nPaso 2: Verificando sucursal Matriz...')
                
                sucursal_matriz, created = Sucursal.objects.get_or_create(
                    codigo_sucursal='SUC-001',
                    defaults={
                        'empresa': empresa_prislab,
                        'nombre': 'Matriz',
                        'activa': True,
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  [OK] Sucursal "{sucursal_matriz.nombre}" creada'))
                else:
                    # Si ya existe, asegurar que esté vinculada a Prislab
                    if sucursal_matriz.empresa != empresa_prislab:
                        sucursal_matriz.empresa = empresa_prislab
                        sucursal_matriz.save()
                        self.stdout.write(self.style.SUCCESS(f'  [OK] Sucursal "{sucursal_matriz.nombre}" vinculada a Prislab'))
                    else:
                        self.stdout.write(self.style.WARNING(f'  [INFO] Sucursal "{sucursal_matriz.nombre}" ya existe'))
                
                # ============================================================
                # PASO 3: Asignar Usuarios a Prislab y Sucursal Matriz
                # ============================================================
                self.stdout.write('\nPaso 3: Asignando usuarios a Prislab y Sucursal Matriz...')
                
                usuarios_sin_empresa = Usuario.objects.filter(empresa__isnull=True)
                usuarios_sin_sucursal = Usuario.objects.filter(sucursal__isnull=True, empresa=empresa_prislab)
                usuarios_totales = Usuario.objects.all().count()
                
                asignados = 0
                
                # Asignar empresa a usuarios sin empresa
                for usuario in usuarios_sin_empresa:
                    usuario.empresa = empresa_prislab
                    usuario.save()
                    asignados += 1
                
                # Asignar sucursal a usuarios sin sucursal
                for usuario in usuarios_sin_sucursal:
                    usuario.add_sucursal(sucursal_matriz)
                    asignados += 1
                
                if asignados > 0:
                    self.stdout.write(self.style.SUCCESS(f'  [OK] {asignados} usuarios asignados a Prislab/Sucursal Matriz'))
                else:
                    self.stdout.write(self.style.WARNING(f'  [INFO] Todos los usuarios ya están asignados (Total: {usuarios_totales})'))
                
                # ============================================================
                # PASO 4: Crear ConfiguracionModulos para Prislab
                # ============================================================
                self.stdout.write('\nPaso 4: Configurando modulos de Prislab...')
                
                config_modulos, created = ConfiguracionModulos.objects.get_or_create(
                    empresa=empresa_prislab,
                    defaults={
                        'modulo_laboratorio': True,
                        'modulo_farmacia': True,
                        'modulo_ia': True,
                        'modulo_expediente_clinico': False,
                        'modulo_consulta_externa': False,
                        'modulo_hospitalizacion': False,
                        'modulo_citas': False,
                        'modulo_rrhh': False,
                        'modulo_contabilidad': False,
                        'modulo_iot': False,
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  [OK] Configuración de módulos creada'))
                    self.stdout.write(self.style.SUCCESS(f'     - Laboratorio: ACTIVO'))
                    self.stdout.write(self.style.SUCCESS(f'     - Farmacia: ACTIVO'))
                    self.stdout.write(self.style.SUCCESS(f'     - IA: ACTIVO'))
                else:
                    # Actualizar módulos en modo force
                    if force:
                        config_modulos.modulo_laboratorio = True
                        config_modulos.modulo_farmacia = True
                        config_modulos.modulo_ia = True
                        config_modulos.save()
                        self.stdout.write(self.style.SUCCESS(f'  [OK] Configuración de módulos actualizada'))
                    else:
                        self.stdout.write(self.style.WARNING(f'  [INFO] Configuración de módulos ya existe'))
                
                # ============================================================
                # RESUMEN FINAL
                # ============================================================
                self.stdout.write(self.style.SUCCESS('\n' + '='*60))
                self.stdout.write(self.style.SUCCESS('[COMPLETADO] INICIALIZACION COMPLETA'))
                self.stdout.write(self.style.SUCCESS('='*60))
                self.stdout.write(f'\nResumen:')
                self.stdout.write(f'   - Empresa: {empresa_prislab.nombre}')
                self.stdout.write(f'   - Sucursal: {sucursal_matriz.nombre} ({sucursal_matriz.codigo_sucursal})')
                self.stdout.write(f'   - Usuarios asignados: {Usuario.objects.filter(empresa=empresa_prislab).count()}')
                self.stdout.write(f'   - Modulos activos: Laboratorio, Farmacia, IA')
                self.stdout.write(self.style.SUCCESS('\n[EXITO] PRISLAB listo (empresa + Matriz + módulos).\n'))
                
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (inicializar_pris_valle.py)")
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Error durante la inicializacion: {str(e)}'))
            self.stdout.write(self.style.ERROR('   La transaccion ha sido revertida.'))
            raise