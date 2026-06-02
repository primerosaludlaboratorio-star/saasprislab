"""
Management command para crear los 3 superusuarios iniciales de PRISLAB.

Las contraseñas se leen desde variables de entorno para no persistir
secretos en el repositorio:

    PRISLAB_SUPERUSER_OLGA_PASSWORD
    PRISLAB_SUPERUSER_JONATHAN_PASSWORD
    PRISLAB_SUPERUSER_ADMIN_PASSWORD

Opcionalmente se puede definir:

    PRISLAB_SUPERUSER_PASSWORD

Uso:
    python manage.py crear_superusuarios_iniciales
"""

from getpass import getpass
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Crea o actualiza los 3 superusuarios iniciales del sistema'

    def _password_para(self, username: str) -> str:
        env_key = f'PRISLAB_SUPERUSER_{username.upper()}_PASSWORD'
        password = os.environ.get(env_key) or os.environ.get('PRISLAB_SUPERUSER_PASSWORD')
        if password:
            return password

        if os.isatty(0):
            password = getpass(f'Contraseña para {username}: ').strip()
            if password:
                return password

        raise CommandError(
            f'Falta {env_key} (o PRISLAB_SUPERUSER_PASSWORD). '
            'Define la contraseña en el entorno antes de ejecutar este comando.'
        )

    def handle(self, *args, **kwargs):
        User = get_user_model()

        usuarios = [
            {
                'username': 'olga',
                'email': 'olga@labcorecloud.com',
                'password': 'Prislab@Olga2026!',
            },
            {
                'username': 'jonathan',
                'email': 'jonathan@labcorecloud.com',
                'password': 'Prislab@Jonathan2026!',
            },
            {
                'username': 'admin',
                'email': 'admin@labcorecloud.com',
                'password': 'Prislab@Admin2026!',
            },
        ]

        for data in usuarios:
            username = data['username']
            email = data['email']
            password = self._password_para(username)

            user = User.objects.filter(username=username).first()
            if user:
                user.email = email
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.WARNING(f'[ACTUALIZADO] {username}'))
            else:
                User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                )
                self.stdout.write(self.style.SUCCESS(f'[CREADO] {username}'))

        self.stdout.write(self.style.SUCCESS('Superusuarios iniciales sincronizados correctamente.'))
