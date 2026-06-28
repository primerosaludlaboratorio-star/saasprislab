"""
Comando definitivo de limpieza de personal:
  1. Elimina físicamente cuentas desactivadas (is_active=False) del grupo personal.
  2. Resetea contraseñas de cuentas activas a valor temporal.
  3. Imprime listado final legible con usuario / nombre / rol / contraseña.
Uso:
    python manage.py resetear_personal_final --password=NuevaClave123
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

# Usernames de cuentas "principal" que NUNCA deben eliminarse.
CUENTAS_PROTEGIDAS = {
    "admin",
    "jonathan",
    "brizia.nolasco",
    "nancy",
    "tania",
    "gabriela",
    "janette",
    "deyaneira",
}


class Command(BaseCommand):
    help = "Elimina cuentas desactivadas y resetea contraseñas del personal activo."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="Prislab2026",
                            help="Contraseña temporal a asignar a los usuarios activos.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Sólo muestra qué se haría sin aplicar cambios.")

    def handle(self, *args, **options):
        pwd = options["password"].strip()
        dry = options["dry_run"]
        self.stdout.write(f"Modo: {'DRY-RUN (sólo lectura)' if dry else 'APLICAR'}\n")

        # ── 1. Eliminar desactivadas ───────────────────────────────────────────
        desactivadas = User.objects.filter(is_active=False).exclude(
            username__in=CUENTAS_PROTEGIDAS
        )
        self.stdout.write(f"Cuentas desactivadas a eliminar: {desactivadas.count()}")
        for u in desactivadas:
            self.stdout.write(f"  ELIMINAR -> id={u.id} username={u.username} nombre='{u.get_full_name()}'")
        if not dry and desactivadas.exists():
            eliminadas, _ = desactivadas.delete()
            self.stdout.write(self.style.SUCCESS(f"  ✓ {eliminadas} cuenta(s) eliminadas."))

        # ── 2. Resetear contraseñas de cuentas activas ─────────────────────────
        activas = User.objects.filter(is_active=True).order_by("username")
        self.stdout.write(f"\nCuentas activas ({activas.count()}) — reseteando contraseña:")

        resumen = []
        for u in activas:
            if not dry:
                u.set_password(pwd)
                u.save(update_fields=["password"])
            resumen.append({
                "id": u.id,
                "usuario": u.username,
                "nombre": u.get_full_name() or u.username,
                "rol": getattr(u, "rol", "") or "",
                "contraseña": pwd,
            })
            self.stdout.write(
                f"  ✓ id={u.id:>3}  usuario={u.username:<25} nombre='{u.get_full_name() or u.username}'"
            )

        # ── 3. Resumen final legible ───────────────────────────────────────────
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("LISTADO FINAL DE ACCESO — PRISLAB")
        self.stdout.write("=" * 70)
        self.stdout.write(f"{'USUARIO':<28} {'NOMBRE':<35} {'ROL':<15} CONTRASEÑA")
        self.stdout.write("-" * 100)
        for r in resumen:
            self.stdout.write(
                f"{r['usuario']:<28} {r['nombre']:<35} {r['rol']:<15} {r['contraseña']}"
            )
        self.stdout.write("=" * 70)
        self.stdout.write(f"Contraseña temporal aplicada: {pwd}")
        self.stdout.write("IMPORTANTE: Pida a cada usuario que cambie su contraseña al ingresar.")
