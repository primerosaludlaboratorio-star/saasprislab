"""
Comando: python manage.py sincronizar_roles_grupos

Asigna automáticamente el grupo de Django correcto a cada usuario según su campo `rol`.
Garantiza que los filtros de sidebar funcionen para todos los usuarios.

Uso:
    python manage.py sincronizar_roles_grupos           # Simular (dry-run)
    python manage.py sincronizar_roles_grupos --apply   # Aplicar cambios
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

User = get_user_model()

# Mapeo: rol (case-insensitive) → nombre del grupo de Django
ROL_A_GRUPO = {
    'ADMIN':        'Administrador',
    'DIRECTOR':     'DIRECTOR',
    'GERENTE':      'GERENCIA',
    'MEDICO':       'MEDICOS',
    'QUIMICO':      'LABORATORIO',
    'LABORATORIO':  'LABORATORIO',
    'CAJERO':       'CAJERO',
    'FARMACIA':     'FARMACIA',
    'RECEPCION':    'RECEPCION',
    'ENFERMERA':    'ENFERMERIA',
    'ENFERMERO':    'ENFERMERIA',
    'SOCIOS':       'SOCIOS',
}


class Command(BaseCommand):
    help = 'Sincroniza grupos de Django con el campo rol de cada usuario'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            default=False,
            help='Aplicar cambios (sin este flag solo muestra qué haría)'
        )

    def handle(self, *args, **options):
        apply = options['apply']
        mode = 'APLICANDO' if apply else 'SIMULANDO (usa --apply para guardar)'
        self.stdout.write(self.style.WARNING(f'\n=== SINCRONIZACIÓN ROL → GRUPO [{mode}] ===\n'))

        # Asegurar que todos los grupos necesarios existen
        todos_los_grupos = set(ROL_A_GRUPO.values())
        for nombre_grupo in todos_los_grupos:
            grupo, creado = Group.objects.get_or_create(name=nombre_grupo)
            if creado:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Grupo creado: {nombre_grupo}'))

        cambios = 0
        sin_rol = 0

        for usuario in User.objects.all().prefetch_related('groups'):
            rol = getattr(usuario, 'rol', '') or ''
            rol_upper = rol.strip().upper()

            if not rol_upper:
                sin_rol += 1
                continue

            nombre_grupo = ROL_A_GRUPO.get(rol_upper)
            if not nombre_grupo:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠️  {usuario.username}: rol="{rol}" no mapeado')
                )
                continue

            grupos_actuales = set(usuario.groups.values_list('name', flat=True))
            if nombre_grupo not in grupos_actuales:
                if apply:
                    grupo = Group.objects.get(name=nombre_grupo)
                    usuario.groups.add(grupo)
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✅ {usuario.username} → grupo "{nombre_grupo}" asignado')
                    )
                else:
                    self.stdout.write(
                        f'  📋 {usuario.username} (rol={rol}) → asignaría grupo "{nombre_grupo}"'
                    )
                cambios += 1
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓  {usuario.username}: ya tiene grupo "{nombre_grupo}"')
                )

        self.stdout.write('\n')
        self.stdout.write(f'Total cambios{"realizados" if apply else "pendientes"}: {cambios}')
        self.stdout.write(f'Usuarios sin rol asignado: {sin_rol}')

        if not apply and cambios > 0:
            self.stdout.write(
                self.style.WARNING('\n💡 Ejecuta con --apply para guardar los cambios:\n'
                                   '   python manage.py sincronizar_roles_grupos --apply')
            )
