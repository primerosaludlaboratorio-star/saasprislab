"""
Script para crear usuarios de producción en PRISLAB v5.
Ejecutar en producción o localmente conectado a PostgreSQL.
"""

import getpass
import os
import sys

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from core.models import Empresa

User = get_user_model()


class Command(BaseCommand):
    help = 'Crea los usuarios de producción con sus roles y permisos'

    password_env = 'PRISLAB_PRODUCTION_USER_PASSWORD'

    def _password(self):
        """Obtiene una contraseña explícita sin valores por defecto inseguros."""
        password = os.environ.get(self.password_env, '').strip()
        if not password:
            if getattr(settings, 'IS_PRODUCTION', False) or not sys.stdin.isatty():
                raise CommandError(
                    f'Configura {self.password_env} en el entorno antes de ejecutar este comando.'
                )
            password = getpass.getpass('Contraseña temporal para los usuarios: ').strip()
        if len(password) < 12:
            raise CommandError('La contraseña debe tener al menos 12 caracteres.')
        return password

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== CREACIÓN DE USUARIOS DE PRODUCCIÓN ===\n'))
        password = self._password()

        # Obtener o crear empresa principal
        empresa, created = Empresa.objects.get_or_create(
            nombre='Laboratorio del Valle',
            defaults={
                'rfc': '',
                'activa': True,
                'periodo_vigencia': '2024-2030'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Empresa "{empresa.nombre}" creada'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Empresa "{empresa.nombre}" ya existe'))

        # Lista de usuarios a crear
        usuarios_config = [
            {
                'username': 'dra.brissia',
                'email': 'dra.brissia@prislab.com',
                'rol': 'DIRECTOR',
                'nombre': 'Dra. Brissia',
                'is_staff': True,
                'puede_usar_ia': True,
                'nivel_ia': 'IA_MASTER'
            },
            {
                'username': 'nancy.quimica',
                'email': 'nancy.quimica@prislab.com',
                'rol': 'QUIMICO',
                'nombre': 'Nancy',
                'is_staff': True,
                'puede_usar_ia': True,
                'nivel_ia': 'IA_TECNICA'
            },
            {
                'username': 'gabriela.quimica',
                'email': 'gabriela.quimica@prislab.com',
                'rol': 'QUIMICO',
                'nombre': 'Gabriela',
                'is_staff': True,
                'puede_usar_ia': True,
                'nivel_ia': 'IA_TECNICA'
            },
            {
                'username': 'melisa',
                'email': 'melisa@prislab.com',
                'rol': 'RECEPCION',
                'nombre': 'Melisa',
                'is_staff': False,
                'puede_usar_ia': False,
                'nivel_ia': 'IA_BASICA'
            },
            {
                'username': 'janet',
                'email': 'janet@prislab.com',
                'rol': 'RECEPCION',
                'nombre': 'Janet',
                'is_staff': False,
                'puede_usar_ia': False,
                'nivel_ia': 'IA_BASICA'
            },
            {
                'username': 'deyanira',
                'email': 'deyanira@prislab.com',
                'rol': 'CAJERO',
                'nombre': 'Deyanira',
                'is_staff': False,
                'puede_usar_ia': False,
                'nivel_ia': 'IA_BASICA'
            },
        ]

        for user_config in usuarios_config:
            username = user_config.pop('username')
            nombre = user_config.pop('nombre')
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    **user_config,
                    'empresa': empresa,
                    'first_name': nombre.split()[0] if nombre.split() else nombre,
                    'last_name': ' '.join(nombre.split()[1:]) if len(nombre.split()) > 1 else ''
                }
            )

            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'✅ Usuario "{username}" creado exitosamente'))
            else:
                # Actualizar datos si el usuario ya existe
                for key, value in user_config.items():
                    setattr(user, key, value)
                user.empresa = empresa
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.WARNING(f'⚠️  Usuario "{username}" ya existía, datos actualizados'))

        self.stdout.write(self.style.SUCCESS('\n✅ Todos los usuarios han sido creados/actualizados con la contraseña proporcionada.'))
        self.stdout.write(self.style.SUCCESS('=== PROCESO COMPLETADO ===\n'))
