from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea/actualiza el grupo Super Master con todos los permisos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="",
            help="Opcional: marca a este superusuario con es_auditor_supremo=True.",
        )

    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name="Super Master")
        group.permissions.set(Permission.objects.all())

        username = (options.get("username") or "").strip()
        if username:
            Usuario = get_user_model()
            try:
                user = Usuario.objects.get(username=username, is_superuser=True)
            except Usuario.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(
                        "No existe un superusuario con ese username. No se marco el flag."
                    )
                )
            else:
                user.es_auditor_supremo = True
                user.groups.add(group)
                user.save(update_fields=["es_auditor_supremo"])
                self.stdout.write(self.style.SUCCESS(f"{username} marcado como Super Master."))

        self.stdout.write(self.style.SUCCESS("Grupo Super Master actualizado."))
