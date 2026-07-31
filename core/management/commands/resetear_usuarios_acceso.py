"""
Reseteo controlado de usuarios de acceso:
  1) Desactiva cuentas fuera del equipo base.
  2) Crea o actualiza 7 usuarios base con una contraseña proporcionada por el operador.

Uso:
    python manage.py resetear_usuarios_acceso --confirm-reset
"""
import getpass
import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction


class Command(BaseCommand):
    help = "Activa el equipo base con una contraseña explícita y confirmada."

    def add_arguments(self, parser):
        parser.add_argument('--password-env', default='PRISLAB_ACCESS_RESET_PASSWORD')
        parser.add_argument('--confirm-reset', action='store_true')
        parser.add_argument('--dry-run', action='store_true')

    def _get_password(self, env_name):
        password = os.environ.get(env_name, '').strip()
        if not password:
            if getattr(settings, 'IS_PRODUCTION', False) or not sys.stdin.isatty():
                raise CommandError(f'Configura {env_name}; nunca se usa una contraseña por defecto.')
            password = getpass.getpass('Contraseña temporal (mínimo 12 caracteres): ').strip()
        if len(password) < 12:
            raise CommandError('La contraseña debe tener al menos 12 caracteres.')
        return password

    def handle(self, *args, **options):
        User = get_user_model()

        # Credenciales solicitadas por el usuario.
        usuarios_base = [
            {
                "username": "jonathan",
                "first_name": "Jonathan",
                "last_name": "Alonso",
                "email": "jonathan@prislab.com",
                "is_superuser": True,
                "is_staff": True,
                "rol": "ADMIN",
            },
            {
                "username": "nancy",
                "first_name": "Nancy",
                "last_name": "Ramirez",
                "email": "nancy@prislab.com",
                "is_superuser": False,
                "is_staff": True,
                "rol": "CAJERO",
            },
            {
                "username": "gabriela",
                "first_name": "Gabriela",
                "last_name": "Araujo",
                "email": "gabriela@prislab.com",
                "is_superuser": False,
                "is_staff": True,
                "rol": "QUIMICO",
            },
            {
                "username": "janette",
                "first_name": "Janette",
                "last_name": "Garcia",
                "email": "janette@prislab.com",
                "is_superuser": False,
                "is_staff": False,
                "rol": "QUIMICO",
            },
            {
                "username": "tania",
                "first_name": "Tania",
                "last_name": "Castro",
                "email": "tania@prislab.com",
                "is_superuser": False,
                "is_staff": False,
                "rol": "QUIMICO",
            },
            {
                "username": "deyaneira",
                "first_name": "Deyaneira",
                "last_name": "Cruz",
                "email": "deyaneira@prislab.com",
                "is_superuser": False,
                "is_staff": False,
                "rol": "RECEPCION",
            },
            {
                "username": "brizia",
                "first_name": "Brizia",
                "last_name": "Nolasco",
                "email": "brizia@prislab.com",
                "is_superuser": False,
                "is_staff": True,
                "rol": "MEDICO",
            },
        ]

        if not options['confirm_reset']:
            raise CommandError('Operación destructiva: añade --confirm-reset para continuar.')
        password = self._get_password(options['password_env'])
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY-RUN: no se modificarán usuarios.'))
            return

        self.stdout.write("Iniciando reseteo de usuarios...")

        target_usernames = [d["username"] for d in usuarios_base]

        with transaction.atomic():
            # Desactivar todos los usuarios que no son del equipo base
            desactivados = User.objects.exclude(username__in=target_usernames).update(is_active=False)
            self.stdout.write(self.style.WARNING(f"Usuarios desactivados: {desactivados}"))

            # Crear o actualizar cada usuario del equipo base
            for data in usuarios_base:
                user, created = User.objects.get_or_create(
                    username=data["username"],
                    defaults={k: v for k, v in data.items()},
                )
                # Siempre actualizar contraseña, rol, permisos y activar
                user.is_active = True
                user.is_staff = data.get("is_staff", False)
                user.is_superuser = data.get("is_superuser", False)
                user.rol = data.get("rol", "CAJERO")
                user.set_password(password)
                user.save()
                tag = "Creado" if created else "Actualizado"
                self.stdout.write(self.style.SUCCESS(f"{tag}: {user.username}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Reseteo completado."))
        self.stdout.write("Usuarios activos finales:")
        for u in User.objects.filter(is_active=True).order_by("username"):
            self.stdout.write(f"  - {u.username}")
