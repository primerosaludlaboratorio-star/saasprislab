"""
Comando de management para crear superusuario en producción.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os


class Command(BaseCommand):
    help = 'Crea o actualiza el superusuario admin en producción'

    def handle(self, *args, **options):
        User = get_user_model()
        
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        email = os.environ.get('ADMIN_EMAIL', 'admin@prislab.com')
        password = os.environ.get('ADMIN_PASSWORD')
        if not password:
            self.stderr.write(self.style.ERROR(
                'ERROR: La variable de entorno ADMIN_PASSWORD no esta configurada. '
                'Abortando para no crear cuentas con credenciales inseguras.'
            ))
            return
        
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password)
            self.stdout.write(
                self.style.SUCCESS(f'✅ Usuario {username} creado exitosamente.')
            )
        else:
            u = User.objects.get(username=username)
            u.set_password(password)
            u.is_staff = True
            u.is_superuser = True
            u.is_active = True
            u.save()
            self.stdout.write(
                self.style.SUCCESS(f'✅ Contraseña de {username} actualizada.')
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Usuario {username} configurado como superusuario y staff.')
            )
