import json

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.test import Client

from core.models import Paciente
from pacientes.portal_models import SolicitudAccesoPortal, UsuarioPaciente


class Command(BaseCommand):
    help = (
        "Auditoria segura de pacientes en modo solo lectura. "
        "No crea, actualiza ni elimina datos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa-id",
            type=int,
            help="Filtra la auditoria a una empresa especifica.",
        )
        parser.add_argument(
            "--username",
            type=str,
            help="Usuario existente para validar rutas autenticadas sin mutar datos.",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="Password del usuario para validar rutas autenticadas.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Imprime el resultado completo en JSON.",
        )

    def handle(self, *args, **options):
        self.empresa_id = options.get("empresa_id")
        self.client = Client()
        self.resultados = {
            "scope": {
                "empresa_id": self.empresa_id,
                "read_only": True,
            },
            "auth": {
                "attempted": bool(options.get("username") and options.get("password")),
                "authenticated": False,
                "username": options.get("username") or "",
            },
            "resumen": {
                "ok": 0,
                "warn": 0,
                "fail": 0,
            },
            "checks": [],
        }

        self._print_header()
        self._authenticate(options.get("username"), options.get("password"))
        self._run_route_checks()
        self._run_data_checks()
        self._run_integrity_checks()
        self._print_summary(options.get("json", False))

    def _print_header(self):
        self.stdout.write("=" * 72)
        self.stdout.write("AUDITORIA SEGURA PACIENTES (SOLO LECTURA)")
        self.stdout.write("=" * 72)

    def _authenticate(self, username, password):
        if not username or not password:
            self._add_check(
                "auth",
                "WARN",
                "Sin credenciales: se validaran rutas en modo anonimo o por redireccion.",
            )
            return

        authenticated = self.client.login(username=username, password=password)
        self.resultados["auth"]["authenticated"] = authenticated
        if authenticated:
            self._add_check("auth", "OK", f"Login correcto para {username}.")
        else:
            self._add_check(
                "auth",
                "WARN",
                f"No se pudo autenticar a {username}; se continua con validaciones de solo lectura.",
            )

    def _empresa_filter(self, field="empresa_id"):
        if not self.empresa_id:
            return Q()
        return Q(**{field: self.empresa_id})

    def _add_check(self, nombre, status, detalle, extra=None):
        self.resultados["checks"].append(
            {
                "nombre": nombre,
                "status": status,
                "detalle": detalle,
                "extra": extra or {},
            }
        )
        if status == "OK":
            self.resultados["resumen"]["ok"] += 1
            self.stdout.write(self.style.SUCCESS(f"[OK] {nombre}: {detalle}"))
        elif status == "WARN":
            self.resultados["resumen"]["warn"] += 1
            self.stdout.write(self.style.WARNING(f"[WARN] {nombre}: {detalle}"))
        else:
            self.resultados["resumen"]["fail"] += 1
            self.stdout.write(self.style.ERROR(f"[FAIL] {nombre}: {detalle}"))

    def _run_route_checks(self):
        self.stdout.write("\n[RUTAS]")
        rutas = [
            ("pacientes_lista", "/pacientes/"),
            ("pacientes_portal_login", "/pacientes/portal/"),
            ("pacientes_portal_solicitar", "/pacientes/portal/solicitar-acceso/"),
            ("pacientes_api_buscar", "/api/pacientes/buscar/?q=ju"),
            ("pacientes_medico_buscar", "/medico/api/buscar-paciente/?q=ju"),
            ("pacientes_cotizacion_buscar", "/cotizacion/api/buscar-paciente/?q=ju"),
            ("pacientes_lab_lista", "/laboratorio/pacientes/"),
        ]

        for nombre, url in rutas:
            response = self.client.get(url, follow=False, secure=True)
            status = response.status_code
            if status >= 500:
                self._add_check(nombre, "FAIL", f"{url} devolvio {status}.", {"status_code": status})
            elif status == 404:
                self._add_check(nombre, "FAIL", f"{url} no existe.", {"status_code": status})
            elif status in (200, 301, 302, 400, 401, 403):
                level = "OK" if status in (200, 301, 302, 400, 401) else "WARN"
                self._add_check(nombre, level, f"{url} respondio {status}.", {"status_code": status})
            else:
                self._add_check(nombre, "WARN", f"{url} respondio {status}.", {"status_code": status})

    def _run_data_checks(self):
        self.stdout.write("\n[DATOS]")
        pacientes_qs = Paciente.objects.filter(self._empresa_filter())
        usuarios_portal_qs = UsuarioPaciente.objects.filter(paciente__in=pacientes_qs)
        solicitudes_qs = SolicitudAccesoPortal.objects.filter(
            Q(paciente__empresa_id=self.empresa_id) if self.empresa_id else Q()
        )

        self._add_check(
            "snapshot_pacientes",
            "OK",
            (
                f"pacientes={pacientes_qs.count()}, activos={pacientes_qs.filter(activo=True).count()}, "
                f"portal_usuarios={usuarios_portal_qs.count()}, solicitudes_portal={solicitudes_qs.count()}"
            ),
            {
                "pacientes": pacientes_qs.count(),
                "pacientes_activos": pacientes_qs.filter(activo=True).count(),
                "portal_usuarios": usuarios_portal_qs.count(),
                "solicitudes_portal": solicitudes_qs.count(),
            },
        )

    def _run_integrity_checks(self):
        self.stdout.write("\n[INTEGRIDAD]")
        pacientes_qs = Paciente.objects.filter(self._empresa_filter())
        usuarios_portal_qs = UsuarioPaciente.objects.filter(paciente__in=pacientes_qs)
        solicitudes_qs = SolicitudAccesoPortal.objects.filter(
            Q(paciente__empresa_id=self.empresa_id) if self.empresa_id else Q()
        )

        pacientes_sin_uuid = pacientes_qs.filter(uuid__isnull=True).count()
        pacientes_sin_fecha_nacimiento = pacientes_qs.filter(fecha_nacimiento__isnull=True).count()
        pacientes_sin_sexo = pacientes_qs.filter(Q(sexo__isnull=True) | Q(sexo="")).count()
        portal_activos_sin_verificar = usuarios_portal_qs.filter(
            is_active=True,
            email_verificado=False,
        ).count()
        solicitudes_aprobadas_sin_paciente = solicitudes_qs.filter(
            estado=SolicitudAccesoPortal.ESTADO_APROBADA,
            paciente__isnull=True,
        ).count()
        solicitudes_rechazadas_sin_motivo = solicitudes_qs.filter(
            estado=SolicitudAccesoPortal.ESTADO_RECHAZADA,
        ).filter(
            Q(motivo_rechazo__isnull=True) | Q(motivo_rechazo="")
        ).count()
        portal_usuario_paciente_inactivo = usuarios_portal_qs.filter(
            is_active=True,
            paciente__activo=False,
        ).count()

        self._integrity_check("pacientes_sin_uuid", pacientes_sin_uuid, "Pacientes sin UUID")
        self._integrity_check("pacientes_sin_fecha_nacimiento", pacientes_sin_fecha_nacimiento, "Pacientes sin fecha_nacimiento")
        self._integrity_check("pacientes_sin_sexo", pacientes_sin_sexo, "Pacientes sin sexo registrado")
        self._integrity_check("portal_activos_sin_verificar", portal_activos_sin_verificar, "Usuarios de portal activos sin email verificado")
        self._integrity_check("solicitudes_aprobadas_sin_paciente", solicitudes_aprobadas_sin_paciente, "Solicitudes aprobadas sin paciente vinculado")
        self._integrity_check("solicitudes_rechazadas_sin_motivo", solicitudes_rechazadas_sin_motivo, "Solicitudes rechazadas sin motivo")
        self._integrity_check("portal_usuario_paciente_inactivo", portal_usuario_paciente_inactivo, "Usuarios de portal activos ligados a paciente inactivo")

    def _integrity_check(self, nombre, cantidad, descripcion):
        if cantidad == 0:
            self._add_check(nombre, "OK", f"{descripcion}: 0")
        else:
            self._add_check(nombre, "WARN", f"{descripcion}: {cantidad}", {"count": cantidad})

    def _print_summary(self, as_json):
        self.stdout.write("\n[RESUMEN]")
        resumen = self.resultados["resumen"]
        self.stdout.write(
            f"OK={resumen['ok']} WARN={resumen['warn']} FAIL={resumen['fail']}"
        )
        if as_json:
            self.stdout.write(json.dumps(self.resultados, indent=2, ensure_ascii=False))
