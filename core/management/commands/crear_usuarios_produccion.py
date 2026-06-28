"""
Script para crear usuarios de producción en PRISLAB v5.
Ejecutar en producción o localmente conectado a PostgreSQL.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Empresa

User = get_user_model()


class Command(BaseCommand):
    help = 'Crea los usuarios de producción con sus roles y permisos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== CREACIÓN DE USUARIOS DE PRODUCCIÓN ===\n'))

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

        password_default = 'Prislab2025'

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
                user.set_password(password_default)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'✅ Usuario "{username}" creado exitosamente'))
            else:
                # Actualizar datos si el usuario ya existe
                for key, value in user_config.items():
                    setattr(user, key, value)
                user.empresa = empresa
                user.set_password(password_default)
                user.save()
                self.stdout.write(self.style.WARNING(f'⚠️  Usuario "{username}" ya existía, datos actualizados'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ Todos los usuarios han sido creados/actualizados con contraseña: {password_default}'))
        self.stdout.write(self.style.SUCCESS('=== PROCESO COMPLETADO ===\n'))
