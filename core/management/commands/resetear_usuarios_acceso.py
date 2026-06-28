"""
Reseteo total de usuarios de acceso:
  1) Elimina TODOS los usuarios existentes.
  2) Crea 7 usuarios base con contraseñas definidas.

Uso:
    python manage.py resetear_usuarios_acceso
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction


class Command(BaseCommand):
    help = "Elimina todos los usuarios y crea los usuarios base de acceso."

    def handle(self, *args, **options):
        User = get_user_model()

        # Credenciales solicitadas por el usuario.
        usuarios_base = [
            {
                "username": "jonathan",
                "password": "Admin2026!",
                "first_name": "Jonathan",
                "last_name": "Alonso",
                "email": "jonathan@prislab.com",
                "is_superuser": True,
                "is_staff": True,
                "rol": "ADMIN",
            },
            {
                "username": "nancy",
                "password": "Nancy2026!",
                "first_name": "Nancy",
                "last_name": "Ramirez",
                "email": "nancy@prislab.com",
                "is_superuser": False,
                "is_staff": True,
                "rol": "CAJERO",
            },
            {
                "username": "gabriela",
                "password": "Gabriela2026!",
                "first_name": "Gabriela",
                "last_name": "Araujo",
                "email": "gabriela@prislab.com",
                "is_superuser": False,
                "is_staff": True,
                "rol": "QUIMICO",
            },
            {
                "username": "janette",
                "password": "Janette2026!",
                "first_name": "Janette",
                "last_name": "Garcia",
                "email": "janette@prislab.com",
                "is_superuser": False,
                "is_staff": False,
                "rol": "QUIMICO",
            },
            {
                "username": "tania",
                "password": "Tania2026!",
                "first_name": "Tania",
                "last_name": "Castro",
                "email": "tania@prislab.com",
                "is_superuser": False,
                "is_staff": False,
                "rol": "QUIMICO",
            },
            {
                "username": "deyaneira",
                "password": "Deyaneira2026!",
                "first_name": "Deyaneira",
                "last_name": "Cruz",
                "email": "deyaneira@prislab.com",
                "is_superuser": False,
                "is_staff": False,
                "rol": "RECEPCION",
            },
            {
                "username": "brizia",
                "password": "Brizia2026!",
                "first_name": "Brizia",
                "last_name": "Nolasco",
                "email": "brizia@prislab.com",
                "is_superuser": False,
                "is_staff": True,
                "rol": "MEDICO",
            },
        ]

        self.stdout.write("Iniciando reseteo de usuarios...")

        target_usernames = [d["username"] for d in usuarios_base]

        with transaction.atomic():
            # Desactivar todos los usuarios que no son del equipo base
            desactivados = User.objects.exclude(username__in=target_usernames).update(is_active=False)
            self.stdout.write(self.style.WARNING(f"Usuarios desactivados: {desactivados}"))

            # Crear o actualizar cada usuario del equipo base
            for data in usuarios_base:
                password = data.pop("password")
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
