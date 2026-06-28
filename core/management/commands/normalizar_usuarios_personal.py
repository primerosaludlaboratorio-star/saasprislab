from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import MensajeInterno, NotificacionSistema


User = get_user_model()


class Command(BaseCommand):
    help = (
        "Consolida usuarios duplicados del personal, deja una sola cuenta activa "
        "por persona y opcionalmente resetea contraseñas."
    )

    # Grupos observados en producción (chat) que representan la misma persona.
    GRUPOS = [
        {"clave": "brizia", "keep": "brizia.nolasco", "aliases": ["brizia.nolasco", "brizia", "Brizia"]},
        {"clave": "nancy", "keep": "nancy", "aliases": ["nancy", "Nancy"]},
        {"clave": "tania", "keep": "tania", "aliases": ["tania", "Tania"]},
        {"clave": "gabriela", "keep": "gabriela", "aliases": ["gabriela", "Gabriela"]},
        {"clave": "janette", "keep": "janette", "aliases": ["janette", "Janeth"]},
    ]

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true", help="Aplica cambios (sin esto es solo simulación).")
        parser.add_argument(
            "--password",
            default="",
            help="Contraseña temporal a asignar a las cuentas finales activas de personal.",
        )
        parser.add_argument(
            "--forzar-jonathan-admin",
            action="store_true",
            help="Fuerza permisos de administrador para usuario 'jonathan'.",
        )

    def _obtener_por_username(self, username, ignore_case=False):
        if ignore_case:
            return User.objects.filter(username__iexact=username).order_by("id").first()
        return User.objects.filter(username=username).order_by("id").first()

    def _resolver_keep(self, group):
        # 1) Preferir username configurado
        keep = self._obtener_por_username(group["keep"])
        if keep:
            return keep
        # 2) Primer alias existente
        for alias in group["aliases"]:
            cand = self._obtener_por_username(alias)
            if cand:
                return cand
        # 3) Fallback case-insensitive (último recurso)
        keep = self._obtener_por_username(group["keep"], ignore_case=True)
        if keep:
            return keep
        for alias in group["aliases"]:
            cand = self._obtener_por_username(alias, ignore_case=True)
            if cand:
                return cand
        return None

    @transaction.atomic
    def handle(self, *args, **options):
        aplicar = options["aplicar"]
        password = (options.get("password") or "").strip()
        forzar_jonathan_admin = options["forzar_jonathan_admin"]

        self.stdout.write(self.style.WARNING("=== NORMALIZACION DE USUARIOS DE PERSONAL ==="))
        self.stdout.write(f"Modo: {'APLICAR' if aplicar else 'SIMULACION'}")

        cuentas_finales = []
        duplicados_desactivados = []
        reasignaciones = {
            "mensajes_remitente": 0,
            "mensajes_destinatario": 0,
            "notif_remitente": 0,
            "notif_destinatario": 0,
        }

        for group in self.GRUPOS:
            keep = self._resolver_keep(group)
            if not keep:
                self.stdout.write(self.style.WARNING(f"[{group['clave']}] No se encontró ninguna cuenta del grupo."))
                continue

            miembros = []
            for alias in group["aliases"]:
                u = self._obtener_por_username(alias)
                if u and u.id not in [m.id for m in miembros]:
                    miembros.append(u)

            cuentas_finales.append(keep)
            self.stdout.write(f"[{group['clave']}] Cuenta final: {keep.username} (id={keep.id})")

            for dup in miembros:
                if dup.id == keep.id:
                    continue

                self.stdout.write(f"  - duplicada -> {dup.username} (id={dup.id})")
                if not aplicar:
                    continue

                # Reasignar artefactos de comunicación a la cuenta final.
                reasignaciones["mensajes_remitente"] += MensajeInterno.objects.filter(remitente=dup).update(remitente=keep)
                reasignaciones["mensajes_destinatario"] += MensajeInterno.objects.filter(destinatario=dup).update(destinatario=keep)
                reasignaciones["notif_remitente"] += NotificacionSistema.objects.filter(remitente=dup).update(remitente=keep)
                reasignaciones["notif_destinatario"] += NotificacionSistema.objects.filter(destinatario=dup).update(destinatario=keep)

                # Desactivar duplicada para que no aparezca ni se use.
                dup.is_active = False
                dup.save(update_fields=["is_active"])
                duplicados_desactivados.append(dup.username)

            if aplicar:
                if not keep.is_active:
                    keep.is_active = True
                    keep.save(update_fields=["is_active"])
                if password:
                    keep.set_password(password)
                    keep.save(update_fields=["password"])

        # Asegurar administrador principal
        jonathan = self._obtener_por_username("jonathan")
        if jonathan:
            self.stdout.write(f"[jonathan] encontrado id={jonathan.id}")
            if aplicar and password:
                jonathan.set_password(password)
            if aplicar and forzar_jonathan_admin:
                jonathan.rol = "ADMIN"
                jonathan.is_staff = True
                jonathan.is_superuser = True
                jonathan.is_active = True
                if password:
                    jonathan.save(update_fields=["password", "rol", "is_staff", "is_superuser", "is_active"])
                else:
                    jonathan.save(update_fields=["rol", "is_staff", "is_superuser", "is_active"])
            elif aplicar and password:
                jonathan.save(update_fields=["password"])
            cuentas_finales.append(jonathan)
        else:
            self.stdout.write(self.style.WARNING("[jonathan] no encontrado en base de datos."))

        if not aplicar:
            self.stdout.write(self.style.WARNING("SIMULACION finalizada. Usa --aplicar para ejecutar cambios."))
            return

        self.stdout.write(self.style.SUCCESS("=== CAMBIOS APLICADOS ==="))
        self.stdout.write(f"Duplicados desactivados: {len(duplicados_desactivados)}")
        self.stdout.write(f"Reasignaciones: {reasignaciones}")

        # Limpiar duplicados en salida final
        finales = {}
        for u in cuentas_finales:
            finales[u.username.lower()] = u.username
        self.stdout.write(self.style.SUCCESS("Cuentas finales activas (normalizadas):"))
        for uname in sorted(finales.values(), key=lambda x: x.lower()):
            self.stdout.write(f" - {uname}")

        if password:
            self.stdout.write(self.style.WARNING(f"Password temporal aplicada: {password}"))
