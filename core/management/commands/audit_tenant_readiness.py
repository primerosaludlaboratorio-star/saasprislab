# -*- coding: utf-8 -*-
"""
PRISLAB v8.5 — Auditoría de preparación multi-tenant (Fase 0).

Salida esperada:
  - Código 0 + mensaje VERDE si todas las comprobaciones pasan.
  - Código 1 + detalle ROJO si hay bloqueos (migraciones pendientes, etc.).

No sustituye revisiones humanas ni pentests; es gate mínimo antes de activar
blindaje estricto adicional (Fase 1).
"""
import os

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import logging


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


class Command(BaseCommand):
    help = (
        "Verifica preparación tenant: migraciones aplicadas, flags de emergencia, "
        "y filas con empresa_id nulo en modelos TenantModel (muestra)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-null-empresa-scan",
            action="store_true",
            help="No escanear modelos con posible empresa_id NULL (más rápido en CI).",
        )

    def handle(self, *args, **options):
        failures = []
        warnings = []

        # --- 1) Migraciones pendientes ---
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            pending = [f"{m.app_label}.{m.name}" for m, _ in plan]
            failures.append(
                "Migraciones pendientes (aplique migrate antes del blindaje): "
                + ", ".join(pending[:25])
                + ("..." if len(pending) > 25 else "")
            )

        # --- 2) Conflicto de migraciones en grafo ---
        try:
            conflicts = executor.loader.detect_conflicts()
            if conflicts:
                failures.append(f"Conflictos de migraciones detectados: {conflicts}")
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en handle (audit_tenant_readiness.py)")
            warnings.append(f"No se pudo ejecutar detect_conflicts: {exc}")

        # --- 3) Bypass de emergencia activo (solo advertencia en producción) ---
        if _truthy_env("PRISLAB_EMERGENCY_TENANT_BYPASS"):
            msg = (
                "PRISLAB_EMERGENCY_TENANT_BYPASS está activo — el filtro ORM por tenant "
                "se desactiva vía middleware (ver DRP_RUNBOOK_ACAYUCAN.md). "
                "No desplegar así salvo incidente."
            )
            if not settings.DEBUG:
                warnings.append(msg)
            else:
                self.stdout.write(self.style.WARNING(f"ADVERTENCIA: {msg}"))

        # --- 4) Muestra de empresa_id NULL en modelos con FK empresa no null ---
        if not options["skip_null_empresa_scan"]:
            try:
                from core.tenant import TenantModel
            except Exception:
                logging.getLogger(__name__).exception("Error inesperado en handle (audit_tenant_readiness.py)")
                TenantModel = None  # type: ignore

            if TenantModel is not None:
                for model in apps.get_models():
                    if not issubclass(model, TenantModel):
                        continue
                    try:
                        fk = model._meta.get_field("empresa")
                    except Exception:
                        logging.getLogger(__name__).exception("Error inesperado en handle (audit_tenant_readiness.py)")
                        continue
                    if getattr(fk, "null", True):
                        continue
                    mgr = getattr(model, "objects_all", model.objects)
                    try:
                        n = mgr.filter(empresa_id__isnull=True).count()
                    except Exception:
                        logging.getLogger(__name__).exception("Error inesperado en handle (audit_tenant_readiness.py)")
                        continue
                    if n:
                        label = f"{model._meta.app_label}.{model.__name__}"
                        failures.append(
                            f"{label}: {n} fila(s) con empresa_id NULL (integridad tenant)."
                        )

        for w in warnings:
            self.stdout.write(self.style.WARNING(f"ADVERTENCIA: {w}"))

        if failures:
            self.stdout.write(self.style.ERROR("RESULTADO: ROJO — acción requerida."))
            for f in failures:
                self.stdout.write(self.style.ERROR(f"  - {f}"))
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS(
                "RESULTADO: VERDE — audit_tenant_readiness OK (estructura mínima lista)."
            )
        )