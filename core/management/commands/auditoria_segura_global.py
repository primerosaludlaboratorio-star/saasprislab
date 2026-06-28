from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Ejecuta el paquete de auditorias seguras (farmacia, laboratorio, "
        "consultorio y pacientes) en modo solo lectura."
    )

    def add_arguments(self, parser):
        parser.add_argument("--empresa-id", type=int, help="Filtra por empresa.")
        parser.add_argument("--username", type=str, help="Usuario para autenticacion opcional.")
        parser.add_argument("--password", type=str, help="Password para autenticacion opcional.")

    def handle(self, *args, **options):
        self.stdout.write("=" * 72)
        self.stdout.write("AUDITORIA SEGURA GLOBAL")
        self.stdout.write("=" * 72)

        common = {}
        if options.get("empresa_id"):
            common["empresa_id"] = options["empresa_id"]
        if options.get("username"):
            common["username"] = options["username"]
        if options.get("password"):
            common["password"] = options["password"]

        comandos = [
            "auditoria_segura_farmacia",
            "auditoria_segura_laboratorio",
            "auditoria_segura_consultorio",
            "auditoria_segura_pacientes",
        ]

        for comando in comandos:
            self.stdout.write("\n" + "-" * 72)
            self.stdout.write(f"Ejecutando: {comando}")
            self.stdout.write("-" * 72)
            call_command(comando, stdout=self.stdout, **common)

        self.stdout.write("\n" + "=" * 72)
        self.stdout.write("AUDITORIA SEGURA GLOBAL FINALIZADA")
        self.stdout.write("=" * 72)
