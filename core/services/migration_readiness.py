from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.urls import get_resolver


@dataclass
class BlockCheck:
    code: str
    label: str
    status: str
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "label": self.label,
            "status": self.status,
            "notes": self.notes,
        }


def _exists(rel_path: str) -> bool:
    return (Path(settings.BASE_DIR) / rel_path).exists()


def _importable(path: str, attr_names: Iterable[str]) -> tuple[bool, list[str]]:
    notes: list[str] = []
    try:
        module = __import__(path, fromlist=["*"])
    except Exception as exc:  # pragma: no cover - defensive
        return False, [f"import-error:{exc}"]

    ok = True
    for attr in attr_names:
        if not hasattr(module, attr):
            ok = False
            notes.append(f"missing:{attr}")
    return ok, notes


def _url_exists(name: str) -> bool:
    resolver = get_resolver()
    def _walk(patterns):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                yield from _walk(pattern.url_patterns)
            else:
                yield pattern

    return any(getattr(pattern, "name", None) == name for pattern in _walk(resolver.url_patterns))


def _safe_count(model_path: str, attr: str) -> tuple[bool, str]:
    try:
        module_path, model_name = model_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[model_name])
        model = getattr(module, model_name)
        return True, f"{attr}:{model.objects.count()}"
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"{attr}_error:{exc}"


def collect_migration_readiness() -> list[BlockCheck]:
    checks: list[BlockCheck] = []

    # Bloque 0 - base de control
    matrix_docs = [
        "MATRIZ_MIGRACION_PRISLAB_VS_PRISLAB_SAAS.md",
        "PLAN_CIERRE_MIGRACION_PRISLAB.md",
        "PLAN_BLOQUE_POR_BLOQUE_PRISLAB.md",
        "CHECKLIST_CONTROL_PRISLAB.md",
        "ANEXO_TECNICO_PRISLAB_LEGACY_VS_SAAS.md",
    ]
    present = [doc for doc in matrix_docs if _exists(doc)]
    checks.append(
        BlockCheck(
            code="B0",
            label="Base de control",
            status="OK" if len(present) == len(matrix_docs) else "WARN",
            notes=[f"docs:{len(present)}/{len(matrix_docs)}"],
        )
    )

    # Bloque 1 - catálogo LIMS
    lims_attrs = ["Analito", "ValorReferenciaAnalito", "PerfilLims", "PaqueteLims", "PrecioItem"]
    lims_ok, lims_notes = _importable("lims.models", lims_attrs)
    pipeline_exists = _exists("lims/management/commands/ensamblar_lims_v75.py")
    counts_notes: list[str] = []
    for model_path, label in [
        ("lims.models.Analito", "analitos"),
        ("lims.models.ValorReferenciaAnalito", "referencias"),
        ("lims.models.PerfilLims", "perfiles"),
        ("lims.models.PaqueteLims", "paquetes"),
        ("lims.models.PrecioItem", "precios"),
    ]:
        ok, note = _safe_count(model_path, label)
        if ok:
            counts_notes.append(note)
        else:
            counts_notes.append(note)
            lims_ok = False
    checks.append(
        BlockCheck(
            code="B1",
            label="Catalogo LIMS base",
            status="OK" if lims_ok and pipeline_exists else "WARN",
            notes=(["pipeline:OK" if pipeline_exists else "pipeline:MISSING"] + lims_notes + counts_notes),
        )
    )

    # Bloque 2 - referencias y resultados
    result_files = [
        "core/services/resultados_impresion_presentacion.py",
        "core/templates/core/resultados_print.html",
        "core/templates/core/laboratorio/captura_resultados.html",
    ]
    result_present = [f for f in result_files if _exists(f)]
    checks.append(
        BlockCheck(
            code="B2",
            label="Resultados y referencias",
            status="OK" if len(result_present) == len(result_files) else "WARN",
            notes=[f"files:{len(result_present)}/{len(result_files)}"],
        )
    )

    # Bloque 3 - recepción y órdenes
    order_files = [
        "core/templates/core/recepcion_lab.html",
        "core/views/laboratorio.py",
    ]
    order_urls = ["recepcion_lab", "captura_resultados", "lista_trabajo_lab", "dashboard_pendientes"]
    order_present = [f for f in order_files if _exists(f)]
    order_urls_ok = [u for u in order_urls if _url_exists(u)]
    checks.append(
        BlockCheck(
            code="B3",
            label="Recepcion y ordenes",
            status="OK" if len(order_present) == len(order_files) and len(order_urls_ok) >= 2 else "WARN",
            notes=[f"files:{len(order_present)}/{len(order_files)}", f"urls:{len(order_urls_ok)}/{len(order_urls)}"],
        )
    )

    # Bloque 4 - pacientes
    patient_files = [
        "core/views/paciente_detalle.py",
        "core/templates/core/lab_pacientes/lista.html",
        "core/templates/core/lab_pacientes/historial.html",
    ]
    patient_present = [f for f in patient_files if _exists(f)]
    checks.append(
        BlockCheck(
            code="B4",
            label="Pacientes",
            status="OK" if len(patient_present) == len(patient_files) else "WARN",
            notes=[f"files:{len(patient_present)}/{len(patient_files)}"],
        )
    )

    # Bloque 5 - clientes
    client_files = [
        "core/views/general.py",
        "core/templates/core/clientes",
    ]
    client_ok = _exists("core/views/general.py")
    checks.append(
        BlockCheck(
            code="B5",
            label="Clientes",
            status="OK" if client_ok else "WARN",
            notes=[f"files:{1 if client_ok else 0}/1"],
        )
    )

    # Bloque 6 - médicos
    doctor_files = [
        "core/views/medico.py",
        "core/templates/core/medico",
    ]
    doctor_ok = _exists("core/views/medico.py")
    checks.append(
        BlockCheck(
            code="B6",
            label="Medicos",
            status="OK" if doctor_ok else "WARN",
            notes=[f"files:{1 if doctor_ok else 0}/1"],
        )
    )

    # Bloque 7 - cotización
    cot_files = ["core/views/cotizacion.py"]
    cot_ok = _exists("core/views/cotizacion.py")
    checks.append(
        BlockCheck(
            code="B7",
            label="Cotizacion",
            status="OK" if cot_ok else "WARN",
            notes=[f"files:{1 if cot_ok else 0}/1"],
        )
    )

    # Bloque 8 - cobranza
    pay_files = [
        "core/views/motor_financiero.py",
        "core/models/ventas.py",
    ]
    pay_present = [f for f in pay_files if _exists(f)]
    checks.append(
        BlockCheck(
            code="B8",
            label="Cobranza",
            status="OK" if len(pay_present) == len(pay_files) else "WARN",
            notes=[f"files:{len(pay_present)}/{len(pay_files)}"],
        )
    )

    # Bloque 9 - auditoría
    audit_files = [
        "core/management/commands/audit_system.py",
        "core/services/audit_service.py",
        "core/views/auditoria_campo.py",
    ]
    audit_present = [f for f in audit_files if _exists(f)]
    checks.append(
        BlockCheck(
            code="B9",
            label="Auditoria",
            status="OK" if len(audit_present) == len(audit_files) else "WARN",
            notes=[f"files:{len(audit_present)}/{len(audit_files)}"],
        )
    )

    # Bloque 10 - seguridad
    sec_files = [
        "config/settings.py",
        "core/middleware/read_only.py",
        "core/utils/permisos.py",
    ]
    sec_present = [f for f in sec_files if _exists(f)]
    checks.append(
        BlockCheck(
            code="B10",
            label="Seguridad y permisos",
            status="OK" if len(sec_present) == len(sec_files) else "WARN",
            notes=[f"files:{len(sec_present)}/{len(sec_files)}"],
        )
    )

    # Bloque 11 - lealtad
    loyalty_files = [
        "core/models/ventas.py",
        "core/views/motor_financiero.py",
    ]
    loyalty_present = [f for f in loyalty_files if _exists(f)]
    checks.append(
        BlockCheck(
            code="B11",
            label="Lealtad",
            status="WARN" if len(loyalty_present) < len(loyalty_files) else "OK",
            notes=[f"files:{len(loyalty_present)}/{len(loyalty_files)}"],
        )
    )

    # Bloque 12 - microbiología
    micro_files = [
        "mantenimiento/views.py",
        "mantenimiento/models.py",
        "core/views/laboratorio.py",
    ]
    micro_present = [f for f in micro_files if _exists(f)]
    checks.append(
        BlockCheck(
            code="B12",
            label="Microbiologia",
            status="WARN" if len(micro_present) < len(micro_files) else "OK",
            notes=[f"files:{len(micro_present)}/{len(micro_files)}"],
        )
    )

    # Bloque 13 - reportes
    report_files = [
        "core/views/dashboard_unificado.py",
        "core/services/motor_reportes_lab.py",
        "core/templates/core/finanzas/caja_laboratorio.html",
    ]
    report_present = [f for f in report_files if _exists(f)]
    checks.append(
        BlockCheck(
            code="B13",
            label="Reportes",
            status="OK" if len(report_present) == len(report_files) else "WARN",
            notes=[f"files:{len(report_present)}/{len(report_files)}"],
        )
    )

    # Bloque 14 - integraciones
    integration_files = [
        "core/utils/google_drive.py",
        "core/utils/gemini_client.py",
        "core/push_service.py",
        "middleware_local/drivers",
    ]
    integration_ok = sum(1 for f in integration_files if _exists(f)) >= 3
    checks.append(
        BlockCheck(
            code="B14",
            label="Integraciones externas",
            status="OK" if integration_ok else "WARN",
            notes=[f"files:{sum(1 for f in integration_files if _exists(f))}/{len(integration_files)}"],
        )
    )

    # Bloque 15 - validación final
    ready_blocks = sum(1 for c in checks if c.status == "OK")
    checks.append(
        BlockCheck(
            code="B15",
            label="Validacion final",
            status="OK" if ready_blocks >= 10 else "WARN",
            notes=[f"bloques_ok:{ready_blocks}/{len(checks)}"],
        )
    )

    return checks


def summarize_migration_readiness() -> dict:
    checks = collect_migration_readiness()
    counters = {"OK": 0, "WARN": 0, "FAIL": 0}
    for check in checks:
        counters[check.status] = counters.get(check.status, 0) + 1
    return {
        "summary": counters,
        "checks": [c.as_dict() for c in checks],
    }
