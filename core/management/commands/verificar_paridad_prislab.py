from django.core.management.base import BaseCommand

from core.services.migration_readiness import summarize_migration_readiness


class Command(BaseCommand):
    help = "Verifica la paridad PRISLAB legado vs PRISLAB SaaS por bloques."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Devuelve el resultado en formato JSON simple.",
        )

    def handle(self, *args, **options):
        data = summarize_migration_readiness()
        checks = data["checks"]
        summary = data["summary"]

        if options.get("json"):
            import json

            self.stdout.write(json.dumps(data, ensure_ascii=False, indent=2))
            return

        self.stdout.write(self.style.SUCCESS("=" * 90))
        self.stdout.write(self.style.SUCCESS("PRISLAB - VERIFICACION DE PARIDAD LEGADO VS SAAS"))
        self.stdout.write(self.style.SUCCESS("=" * 90))
        self.stdout.write(
            f"OK: {summary.get('OK', 0)} | WARN: {summary.get('WARN', 0)} | FAIL: {summary.get('FAIL', 0)}"
        )
        self.stdout.write("")

        for check in checks:
            status = check["status"]
            label = f"{check['code']} {check['label']}"
            notes = "; ".join(check.get("notes", []))
            style = {
                "OK": self.style.SUCCESS,
                "WARN": self.style.WARNING,
                "FAIL": self.style.ERROR,
            }.get(status, self.style.NOTICE)
            self.stdout.write(style(f"[{status}] {label}"))
            if notes:
                self.stdout.write(f"    {notes}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Bloques listos para usar como tablero de cierre."))

