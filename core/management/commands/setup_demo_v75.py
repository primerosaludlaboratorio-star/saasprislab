"""
Demo mínima LIMS v7.5 — orden con analitos reales (sin core.Estudio / core.Parametro).

Ejecuta el ensamblaje oficial (`ensamblar_lims_v75` → datos_lims/) y crea una OrdenDeServicio
con dos DetalleOrden + ResultadoParametro por analito (valor placeholder para captura en UI).

Nota de modelo: no existe el literal CAPTURANDO en OrdenDeServicio; se usa estado EN_PROCESO y
estado_clinico EN_PROCESO como fase operativa de laboratorio lista para captura/validación.

Uso:
  python manage.py setup_demo_v75
  python manage.py setup_demo_v75 --force
  python manage.py setup_demo_v75 --saltar-ensamblaje   # catálogo ya cargado
"""
from __future__ import annotations

import sys
import uuid
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from lims.models import Analito

from core.models import (
    Empresa,
    Sucursal,
    Paciente,
    Medico,
    OrdenDeServicio,
    DetalleOrden,
    ResultadoParametro,
)

User = get_user_model()

DEMO_EMPRESA_NOMBRE = "PRISLAB Demo LIMS v7.5"
DEMO_SUCURSAL_NOMBRE = "Sucursal Demo v7.5"
DEMO_SUCURSAL_CODIGO = "SUC-DEMO-V75"
DEMO_PACIENTE_NOMBRE = "Paciente Demo v7.5"
DEMO_MEDICO_CEDULA = "DEMO-V75-MED-001"
DEMO_USUARIO_USERNAME = "demo_v75_quimico"


class Command(BaseCommand):
    help = (
        "Ensambla catálogo LIMS v7.5 desde datos_lims/ y crea orden demo con 2 analitos "
        "(DetalleOrden + ResultadoParametro)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="No pedir confirmación por consola si ya existen órdenes.",
        )
        parser.add_argument(
            "--saltar-ensamblaje",
            action="store_true",
            help="No ejecutar ensamblar_lims_v75 (asume Analitos ya importados).",
        )

    def handle(self, *args, **options):
        force: bool = options["force"]
        saltar_ensamblaje: bool = options["saltar_ensamblaje"]

        n_ordenes = OrdenDeServicio.objects.filter(deleted_at__isnull=True).count()
        if n_ordenes > 0 and not force:
            self.stdout.write(
                self.style.WARNING(
                    f"ADVERTENCIA: Ya existen {n_ordenes} orden(es) de servicio (no eliminadas)."
                )
            )
            if not sys.stdin.isatty():
                raise CommandError(
                    "Hay órdenes existentes. En modo no interactivo use: "
                    "python manage.py setup_demo_v75 --force"
                )
            resp = input("¿Inyectar datos de prueba demo v7.5? [s/N]: ").strip().lower()
            if resp not in ("s", "si", "sí", "y", "yes"):
                self.stdout.write(self.style.ERROR("Operación cancelada."))
                return

        if not saltar_ensamblaje:
            self.stdout.write(self.style.HTTP_INFO(">>> Ejecutando ensamblar_lims_v75 …\n"))
            try:
                call_command("ensamblar_lims_v75", stdout=self.stdout, stderr=self.stderr)
            except Exception as exc:
                raise CommandError(f"Falló ensamblar_lims_v75: {exc}") from exc
        else:
            self.stdout.write(self.style.WARNING(">>> Ensamblaje omitido (--saltar-ensamblaje).\n"))

        analitos = self._pick_two_analitos()
        if len(analitos) < 2:
            raise CommandError(
                "Se requieren al menos 2 analitos activos. "
                "Ejecute sin --saltar-ensamblaje o verifique datos_lims/ y el pipeline LIMS."
            )

        with transaction.atomic():
            empresa, sucursal = self._ensure_empresa_sucursal()
            paciente = self._ensure_paciente(empresa, sucursal)
            medico = self._ensure_medico(empresa)
            usuario = self._ensure_responsable(empresa, sucursal)

            lineas: list[tuple[Analito, Decimal]] = []
            for an in analitos:
                precio = (
                    an.costo_lista
                    if an.costo_lista is not None
                    else Decimal("0.00")
                )
                lineas.append((an, precio))

            total = sum((p for _, p in lineas), Decimal("0.00"))
            folio = f"DEMO-V75-{uuid.uuid4().hex[:10].upper()}"

            # EN_PROCESO: no existe CAPTURANDO en el modelo; equivale a orden en flujo de laboratorio.
            orden = OrdenDeServicio.objects.create(
                empresa=empresa,
                sucursal=sucursal,
                paciente=paciente,
                paciente_nombre_snapshot=paciente.nombre_completo,
                paciente_edad_snapshot=paciente.edad,
                paciente_sexo_snapshot=paciente.sexo or "M",
                medico_referente=medico,
                estado="EN_PROCESO",
                estado_pago="PAGADO",
                estado_clinico="EN_PROCESO",
                total=total,
                anticipo=total,
                responsable_ingreso=usuario,
                folio_orden=folio,
                tipo_servicio="RUTINA",
            )

            for an, precio in lineas:
                DetalleOrden.objects.create(
                    orden=orden,
                    analito=an,
                    descripcion_linea=(an.nombre or an.abreviatura or "")[:300],
                    precio_momento=precio,
                    estado_procesamiento="EN_PROCESO",
                )
                ResultadoParametro.objects.create(
                    orden=orden,
                    analito=an,
                    valor="PENDIENTE_CAPTURA",
                    capturado_por=usuario,
                    metodo_captura="MANUAL",
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"OK — Orden demo LIMS v7.5: id={orden.pk} folio={folio!r} "
                f"(2 analitos: {', '.join(a.abreviatura for a, _ in lineas)}). "
                "Busque la orden en la UI de laboratorio por id o folio."
            )
        )

    def _pick_two_analitos(self) -> list[Analito]:
        preferidos = (
            Analito.objects.filter(activo=True)
            .filter(
                Q(nombre__icontains="gluc")
                | Q(nombre__icontains="colest")
                | Q(nombre__icontains="glucose")
                | Q(nombre__icontains="cholesterol")
                | Q(abreviatura__icontains="GLU")
                | Q(abreviatura__icontains="COL")
            )
            .order_by("id")
        )
        out: list[Analito] = list(preferidos[:2])
        if len(out) >= 2:
            return out
        exclude = {a.pk for a in out}
        extra = list(
            Analito.objects.filter(activo=True)
            .exclude(pk__in=exclude)
            .order_by("id")[: 2 - len(out)]
        )
        return out + extra

    def _ensure_empresa_sucursal(self) -> tuple[Empresa, Sucursal]:
        empresa, _ = Empresa.objects.get_or_create(
            nombre=DEMO_EMPRESA_NOMBRE,
            defaults={
                "rfc": "DEM750101XXX",
                "activa": True,
            },
        )
        sucursal, _ = Sucursal.objects.get_or_create(
            codigo_sucursal=DEMO_SUCURSAL_CODIGO,
            defaults={
                "empresa": empresa,
                "nombre": DEMO_SUCURSAL_NOMBRE,
                "activa": True,
            },
        )
        if sucursal.empresa_id != empresa.id:
            sucursal.empresa = empresa
            sucursal.save(update_fields=["empresa"])
        return empresa, sucursal

    def _ensure_paciente(self, empresa: Empresa, sucursal: Sucursal) -> Paciente:
        paciente, created = Paciente.objects.get_or_create(
            empresa=empresa,
            nombre_completo=DEMO_PACIENTE_NOMBRE,
            defaults={
                "sucursal": sucursal,
                "nombres": "Paciente",
                "apellido_paterno": "Demo",
                "apellido_materno": "v7.5",
                "fecha_nacimiento": date(1990, 5, 15),
                "sexo": "M",
                "telefono": "5550100750",
                "tipo": "GENERAL",
            },
        )
        if not created and paciente.sucursal_id is None:
            paciente.sucursal = sucursal
            paciente.save(update_fields=["sucursal"])
        return paciente

    def _ensure_medico(self, empresa: Empresa) -> Medico:
        medico, _ = Medico.objects.get_or_create(
            cedula_profesional=DEMO_MEDICO_CEDULA,
            defaults={
                "empresa": empresa,
                "nombre_completo": "Dr. Demo LIMS v7.5",
                "especialidad": "Médico General",
                "activo": True,
            },
        )
        if medico.empresa_id != empresa.id:
            medico.empresa = empresa
            medico.save(update_fields=["empresa"])
        return medico

    def _ensure_responsable(self, empresa: Empresa, sucursal: Sucursal) -> User | None:
        user = (
            User.objects.filter(empresa=empresa)
            .order_by("-is_staff", "-is_superuser", "id")
            .first()
        )
        if user:
            return user
        user, created = User.objects.get_or_create(
            username=DEMO_USUARIO_USERNAME,
            defaults={
                "email": "demo_v75_quimico@prislab.local",
                "empresa": empresa,
                "sucursal": sucursal,
                "rol": "QUIMICO",
                "is_staff": False,
                "is_superuser": False,
            },
        )
        if created:
            user.set_unusable_password()
            user.save(
                update_fields=[
                    "password",
                    "empresa",
                    "sucursal",
                    "rol",
                    "is_staff",
                    "is_superuser",
                ]
            )
            self.stdout.write(
                self.style.WARNING(
                    f"Usuario responsable creado: {DEMO_USUARIO_USERNAME} "
                    "(contraseña deshabilitada; asigne una desde admin o use otro usuario)."
                )
            )
        else:
            user.empresa = empresa
            user.sucursal = sucursal
            user.rol = "QUIMICO"
            user.save(update_fields=["empresa", "sucursal", "rol"])
        return user
