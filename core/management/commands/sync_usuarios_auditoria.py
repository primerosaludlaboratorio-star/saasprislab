from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.models import Empresa


class Command(BaseCommand):
    help = (
        "Crea o actualiza usuarios de auditoría sobre la base activa. "
        "Úsese junto con scripts/run_manage_with_env.py en producción."
    )

    def add_arguments(self, parser):
        parser.add_argument("--empresa-id", type=int, required=True)
        parser.add_argument("--admin-password", required=True)
        parser.add_argument("--jonathan-password", required=True)
        parser.add_argument("--olga-password", required=True)
        parser.add_argument("--admin-director-password", required=True)

    def handle(self, *args, **options):
        empresa = Empresa.objects.filter(pk=options["empresa_id"]).first()
        if not empresa:
            raise CommandError(f"No existe Empresa con id={options['empresa_id']}")

        user_model = get_user_model()
        usuarios = [
            {
                "username": "admin",
                "email": "admin@labcorecloud.com",
                "password": options["admin_password"],
                "rol": "ADMIN",
                "first_name": "Admin",
                "last_name": "PRISLAB",
            },
            {
                "username": "jonathan",
                "email": "jonathan@labcorecloud.com",
                "password": options["jonathan_password"],
                "rol": "DIRECTOR",
                "first_name": "Jonathan",
                "last_name": "PRISLAB",
            },
            {
                "username": "olga",
                "email": "olga@labcorecloud.com",
                "password": options["olga_password"],
                "rol": "DIRECTOR",
                "first_name": "Olga",
                "last_name": "PRISLAB",
            },
            {
                "username": "admin_director",
                "email": "primerosaludlaboratorio@gmail.com",
                "password": options["admin_director_password"],
                "rol": "DIRECTOR",
                "first_name": "Admin",
                "last_name": "Director",
            },
        ]

        for spec in usuarios:
            user, created = user_model.objects.get_or_create(
                username=spec["username"],
                defaults={
                    "email": spec["email"],
                    "is_staff": True,
                    "is_superuser": True,
                    "is_active": True,
                    "rol": spec["rol"],
                    "empresa": empresa,
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                },
            )
            user.email = spec["email"]
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.rol = spec["rol"]
            user.empresa = empresa
            user.first_name = spec["first_name"]
            user.last_name = spec["last_name"]
            user.set_password(spec["password"])
            user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"{'CREATED' if created else 'UPDATED'}: "
                    f"{user.username} empresa={user.empresa_id} rol={user.rol}"
                )
            )
