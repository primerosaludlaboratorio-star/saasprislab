"""
Script de configuración de roles y permisos RBAC (Role-Based Access Control).

Este script crea grupos de permisos con jerarquía operativa definida por Jonathan:
- GERENCIA_OPERATIVA: Acceso casi total (Nancy y Gabriela)
- STAFF_GENERAL: Solo operación básica (Técnicos/Recepción Jr)
- MEDICO_RADIOLOGO: Perfil para Doctora (Nuevo)

Uso:
    python manage.py setup_roles
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import (
    Usuario, Producto, Lote, Venta, DetalleVenta, Pago, Medico, Receta, Gasto,
    OrdenDeServicio, DetalleOrden, Paciente,
)
from laboratorio.models import Estudio


class Command(BaseCommand):
    help = 'Configura grupos de permisos RBAC con jerarquía operativa'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Limpiar grupos existentes antes de crear nuevos (siempre se hace)',
        )

    def handle(self, *args, **options):
        # SIEMPRE borrar y recrear grupos para asegurar permisos exactos
        self.stdout.write(self.style.WARNING('Borrando grupos existentes para recrearlos...'))
        Group.objects.filter(
            name__in=['GERENCIA_OPERATIVA', 'STAFF_GENERAL', 'MEDICO_RADIOLOGO']
        ).delete()
        self.stdout.write(self.style.SUCCESS('Grupos borrados'))
        
        # Crear grupos
        self.stdout.write(self.style.WARNING('\n=== Creando grupos de permisos ==='))
        
        grupo_gerencia = Group.objects.create(name='GERENCIA_OPERATIVA')
        grupo_staff = Group.objects.create(name='STAFF_GENERAL')
        grupo_medico = Group.objects.create(name='MEDICO_RADIOLOGO')
        
        self.stdout.write(self.style.SUCCESS('Grupo GERENCIA_OPERATIVA creado'))
        self.stdout.write(self.style.SUCCESS('Grupo STAFF_GENERAL creado'))
        self.stdout.write(self.style.SUCCESS('Grupo MEDICO_RADIOLOGO creado'))
        
        # Configurar permisos para GERENCIA_OPERATIVA
        self.stdout.write(self.style.WARNING('\n=== Configurando permisos para GERENCIA_OPERATIVA ==='))
        self.configurar_gerencia_operativa(grupo_gerencia)
        
        # Configurar permisos para STAFF_GENERAL
        self.stdout.write(self.style.WARNING('\n=== Configurando permisos para STAFF_GENERAL ==='))
        self.configurar_staff_general(grupo_staff)
        
        # Configurar permisos para MEDICO_RADIOLOGO
        self.stdout.write(self.style.WARNING('\n=== Configurando permisos para MEDICO_RADIOLOGO ==='))
        self.configurar_medico_radiologo(grupo_medico)
        
        # Asignar usuarios a grupos
        self.stdout.write(self.style.WARNING('\n=== Asignando usuarios a grupos ==='))
        self.asignar_usuarios(grupo_gerencia, grupo_staff, grupo_medico)
        
        # Reporte final
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('=== REPORTE DE CONFIGURACIÓN DE ROLES ==='))
        self.stdout.write(self.style.SUCCESS(f'Grupo GERENCIA_OPERATIVA: {grupo_gerencia.permissions.count()} permisos'))
        self.stdout.write(self.style.SUCCESS(f'Grupo STAFF_GENERAL: {grupo_staff.permissions.count()} permisos'))
        self.stdout.write(self.style.SUCCESS(f'Grupo MEDICO_RADIOLOGO: {grupo_medico.permissions.count()} permisos'))
        self.stdout.write(self.style.SUCCESS(f'Usuarios en GERENCIA_OPERATIVA: {grupo_gerencia.user_set.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Usuarios en STAFF_GENERAL: {grupo_staff.user_set.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Usuarios en MEDICO_RADIOLOGO: {grupo_medico.user_set.count()}'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        # Imprimir grupos creados
        self.stdout.write(self.style.SUCCESS('\n=== GRUPOS CREADOS ==='))
        for grupo in [grupo_gerencia, grupo_staff, grupo_medico]:
            self.stdout.write(self.style.SUCCESS(f'  - {grupo.name} ({grupo.permissions.count()} permisos)'))

    def configurar_gerencia_operativa(self, grupo):
        """
        Configura permisos para GERENCIA_OPERATIVA.
        Filosofía: Acceso casi total, excepto borrado duro y métricas de dueño.
        """
        
        # 1. LABORATORIO: add, change, view, validate, delete (solo soft-delete si aplica)
        self.agregar_permisos_modelo(grupo, Estudio, ['add', 'change', 'view', 'delete'])
        self.agregar_permisos_modelo(grupo, DetalleOrden, ['add', 'change', 'view', 'delete'])
        
        # Permiso personalizado validate (si existe)
        self.agregar_permiso_personalizado(grupo, DetalleOrden, 'validate')
        
        # 2. FARMACIA: add, change, view, delete (para ajustes de inventario)
        self.agregar_permisos_modelo(grupo, Producto, ['add', 'change', 'view', 'delete'])
        self.agregar_permisos_modelo(grupo, Lote, ['add', 'change', 'view', 'delete'])
        self.agregar_permisos_modelo(grupo, Venta, ['add', 'change', 'view', 'delete'])
        self.agregar_permisos_modelo(grupo, DetalleVenta, ['add', 'change', 'view', 'delete'])
        self.agregar_permisos_modelo(grupo, Receta, ['add', 'change', 'view', 'delete'])
        self.agregar_permisos_modelo(grupo, Gasto, ['add', 'change', 'view', 'delete'])
        
        # 3. ÓRDENES: add, change, view (EXCLUIR delete_orden)
        self.agregar_permisos_modelo(grupo, OrdenDeServicio, ['add', 'change', 'view'], excluir_delete=True)
        
        # 4. PACIENTES: add, change, view
        self.agregar_permisos_modelo(grupo, Paciente, ['add', 'change', 'view'], excluir_delete=True)
        self.agregar_permisos_modelo(grupo, Medico, ['add', 'change', 'view'], excluir_delete=True)
        
        # 5. CAJA: add, change, view (Cortes, Cobros)
        self.agregar_permisos_modelo(grupo, Pago, ['add', 'change', 'view'], excluir_delete=True)
        # Nota: Si existe modelo Corte, agregarlo aquí
        
        # 6. PRECIOS: Permitir edición de Producto y Estudio (Precios)
        # Ya incluido arriba con 'change' en Producto y Estudio
        
        # EXCLUIR explícitamente delete_orden
        self.remover_permiso(grupo, OrdenDeServicio, 'delete')
        
        self.stdout.write(self.style.SUCCESS(f'Permisos configurados para GERENCIA_OPERATIVA: {grupo.permissions.count()} permisos'))

    def configurar_staff_general(self, grupo):
        """
        Configura permisos para STAFF_GENERAL.
        Filosofía: Solo operación básica.
        """
        
        # 1. ÓRDENES: add, view (No change, No delete)
        self.agregar_permisos_modelo(grupo, OrdenDeServicio, ['add', 'view'], excluir_delete=True)
        
        # 2. PACIENTES: add, view, change
        self.agregar_permisos_modelo(grupo, Paciente, ['add', 'view', 'change'], excluir_delete=True)
        
        # 3. LABORATORIO: add_resultado, view_resultado (SIN validar)
        # add_resultado = add en DetalleOrden, view_resultado = view en DetalleOrden
        # SIN validar = SIN change en DetalleOrden
        self.agregar_permisos_modelo(grupo, DetalleOrden, ['add', 'view'], excluir_delete=True)
        self.agregar_permisos_modelo(grupo, Estudio, ['view'], excluir_delete=True)  # Solo ver estudios
        
        # 4. CAJA: add_pago (Cobrar), pero SIN do_corte (Hacer corte)
        self.agregar_permisos_modelo(grupo, Pago, ['add', 'view'], excluir_delete=True)
        # Nota: do_corte sería un permiso personalizado o acción específica
        
        # RESTRICCIONES EXPLÍCITAS:
        # - Sin change en OrdenDeServicio (ya excluido arriba)
        # - Sin change en DetalleOrden (ya excluido arriba - no puede validar)
        # - Sin do_corte (no se agrega permiso de corte)
        
        self.stdout.write(self.style.SUCCESS(f'Permisos configurados para STAFF_GENERAL: {grupo.permissions.count()} permisos'))

    def configurar_medico_radiologo(self, grupo):
        """
        Configura permisos para MEDICO_RADIOLOGO.
        Perfil para Doctora (Nuevo).
        """
        
        # 1. LABORATORIO: add_reporte_ultrasonido (cuando creemos el modelo)
        # Por ahora, agregamos permisos básicos de DetalleOrden para reportes
        # Cuando se cree el modelo ReporteUltrasonido, se puede agregar aquí
        self.agregar_permisos_modelo(grupo, DetalleOrden, ['add', 'view'], excluir_delete=True)
        
        # Permiso personalizado add_reporte_ultrasonido (si existe o cuando se cree)
        # self.agregar_permiso_personalizado(grupo, ReporteUltrasonido, 'add_reporte_ultrasonido')
        
        # 2. PACIENTES: view (solo lectura)
        self.agregar_permisos_modelo(grupo, Paciente, ['view'], excluir_delete=True)
        
        # Ver estudios (solo lectura)
        self.agregar_permisos_modelo(grupo, Estudio, ['view'], excluir_delete=True)
        
        self.stdout.write(self.style.SUCCESS(f'Permisos configurados para MEDICO_RADIOLOGO: {grupo.permissions.count()} permisos'))

    def agregar_permisos_modelo(self, grupo, modelo, acciones, excluir_delete=False):
        """
        Agrega permisos de un modelo a un grupo.
        
        Args:
            grupo: Grupo de Django al que agregar permisos
            modelo: Clase del modelo (ej: Paciente, Producto)
            acciones: Lista de acciones ['add', 'change', 'view', 'delete']
            excluir_delete: Si True, nunca agrega permisos de eliminación
        """
        try:
            content_type = ContentType.objects.get_for_model(modelo)
            
            for accion in acciones:
                if excluir_delete and accion == 'delete':
                    continue
                
                codigo_permiso = f'{accion}_{modelo._meta.model_name}'
                try:
                    permiso = Permission.objects.get(
                        content_type=content_type,
                        codename=codigo_permiso
                    )
                    grupo.permissions.add(permiso)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Permiso no encontrado: {codigo_permiso} para {modelo._meta.label}'
                        )
                    )
        except ContentType.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'ContentType no encontrado para {modelo._meta.label}')
            )

    def agregar_permiso_personalizado(self, grupo, modelo, codename):
        """
        Agrega un permiso personalizado a un grupo.
        
        Args:
            grupo: Grupo de Django al que agregar permisos
            modelo: Clase del modelo
            codename: Código del permiso personalizado (ej: 'validate', 'add_reporte_ultrasonido')
        """
        try:
            content_type = ContentType.objects.get_for_model(modelo)
            permiso = Permission.objects.get(
                content_type=content_type,
                codename=codename
            )
            grupo.permissions.add(permiso)
            self.stdout.write(
                self.style.SUCCESS(f'Permiso personalizado agregado: {codename} para {modelo._meta.label}')
            )
        except Permission.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    f'Permiso personalizado no encontrado: {codename} para {modelo._meta.label} '
                    f'(se creará cuando se defina en el modelo)'
                )
            )
        except ContentType.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'ContentType no encontrado para {modelo._meta.label}')
            )

    def remover_permiso(self, grupo, modelo, accion):
        """
        Remueve un permiso específico de un grupo.
        
        Args:
            grupo: Grupo de Django
            modelo: Clase del modelo
            accion: Acción a remover ('delete', 'change', etc.)
        """
        try:
            content_type = ContentType.objects.get_for_model(modelo)
            codigo_permiso = f'{accion}_{modelo._meta.model_name}'
            permiso = Permission.objects.get(
                content_type=content_type,
                codename=codigo_permiso
            )
            grupo.permissions.remove(permiso)
            self.stdout.write(
                self.style.SUCCESS(f'Permiso removido: {codigo_permiso} de {modelo._meta.label}')
            )
        except (Permission.DoesNotExist, ContentType.DoesNotExist):
            pass  # Si no existe, no hay nada que remover

    def asignar_usuarios(self, grupo_gerencia, grupo_staff, grupo_medico):
        """Asigna usuarios especificos a los grupos."""
        from django.contrib.auth.models import Group
        
        # Nancy y Gabriela: GERENCIA_OPERATIVA + TODOS los grupos operativos
        # Tienen autorizacion gerencial, estan arriba de todo el personal,
        # solo debajo del Director (dueno). Acceden a TODAS las areas:
        # laboratorio, farmacia, recepcion, caja, toma de muestra, proceso, etc.
        nombres_buscar = ['nancy', 'gabriela']
        
        # Grupos operativos a los que deben pertenecer
        grupos_operativos = ['LABORATORIO', 'FARMACIA', 'RECEPCION', 'GERENCIA', 'ENFERMERIA']
        
        for nombre in nombres_buscar:
            usuarios = Usuario.objects.filter(
                username__icontains=nombre
            ) | Usuario.objects.filter(
                first_name__icontains=nombre
            ) | Usuario.objects.filter(
                last_name__icontains=nombre
            ) | Usuario.objects.filter(
                email__icontains=nombre
            )
            
            if usuarios.exists():
                for usuario in usuarios:
                    # Grupo principal: GERENCIA_OPERATIVA
                    grupo_gerencia.user_set.add(usuario)
                    
                    # Agregar a TODOS los grupos operativos
                    for grupo_nombre in grupos_operativos:
                        grupo_op, _ = Group.objects.get_or_create(name=grupo_nombre)
                        grupo_op.user_set.add(usuario)
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Usuario {usuario.username} ({usuario.get_full_name() or usuario.email}) '
                            f'asignado a GERENCIA_OPERATIVA + {", ".join(grupos_operativos)}'
                        )
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Usuario con nombre "{nombre}" no encontrado. '
                        f'Busca por username, first_name, last_name o email.'
                    )
                )
        
        # Nota: Los usuarios de STAFF_GENERAL y MEDICO_RADIOLOGO se asignan manualmente
        # o mediante otro proceso ya que no se especificaron usuarios específicos
        
        # Mostrar lista de usuarios disponibles para referencia
        if grupo_gerencia.user_set.count() == 0:
            self.stdout.write(self.style.WARNING('\nUsuarios disponibles en el sistema:'))
            for usuario in Usuario.objects.filter(is_staff=True)[:10]:
                self.stdout.write(
                    f'  - {usuario.username} ({usuario.get_full_name() or "Sin nombre"} - {usuario.email or "Sin email"})'
                )
