#!/usr/bin/env python
"""Run static negative controls against a disposable repository copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class NegativeControl:
    name: str
    description: str
    file_path: str
    invariant: str
    minimum_count: int = 1


CONTROLS = (
    NegativeControl("CONTROL_APPEND_ONLY_GUARD",
                    "AuditLog must reject append-only updates.",
                    "core/models/operaciones.py",
                    "reject_append_only_mutation(self, 'actualizacion')"),
    NegativeControl("CONTROL_HISTORIAL_TENANT_FILTER",
                    "LIMS history must filter the catalog by company.",
                    "core/views/historial_resultados.py",
                    "Analito.objects.filter(empresa=empresa, activo=True)"),
    NegativeControl("CONTROL_RECEPCION_TENANT_FILTER",
                    "LIMS reception must filter analytes by company.",
                    "core/views/laboratorio/recepcion.py",
                    "Analito.objects.filter(empresa=empresa, activo=True)"),
    NegativeControl("CONTROL_ADMIN_TENANT_MIXIN",
                    "Operational Admin must use tenant isolation.",
                    "core/admin/tenant.py",
                    "class TenantScopedAdmin(TenantScopedAdminMixin, admin.ModelAdmin):"),
    NegativeControl("CONTROL_WEBHOOK_CONSTANT_TIME",
                    "Both webhook checks must use constant-time comparison.",
                    "core/views/prisci_webhook.py",
                    "secrets.compare_digest",
                    minimum_count=2),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect(control: NegativeControl, workspace: Path) -> bool:
    path = workspace / control.file_path
    return path.is_file() and path.read_text(encoding="utf-8").count(
        control.invariant
    ) >= control.minimum_count


def catalog(workspace: Path) -> list[dict]:
    entries = []
    for control in CONTROLS:
        path = workspace / control.file_path
        count = path.read_text(encoding="utf-8").count(control.invariant) if path.is_file() else 0
        entries.append({
            "name": control.name,
            "file_path": control.file_path,
            "detector_type": "static_invariant",
            "target_exists": path.is_file(),
            "baseline_invariant_count": count,
            "minimum_count": control.minimum_count,
            "status": "READY" if path.is_file() and count >= control.minimum_count else "BLOCKED",
        })
    return entries


def disposable_copy(source: Path) -> Path:
    destination = Path(tempfile.mkdtemp(prefix="prislab-negative-controls-"))
    ignore = shutil.ignore_patterns(".git", ".venv*", "node_modules", "__pycache__", "*.pyc")
    shutil.copytree(source, destination, dirs_exist_ok=True, ignore=ignore)
    return destination


def execute_control(control: NegativeControl, workspace: Path) -> dict:
    path = workspace / control.file_path
    result = {
        "name": control.name,
        "description": control.description,
        "file_path": control.file_path,
        "detector_type": "static_invariant",
        "detector": f"required invariant count >= {control.minimum_count}",
        "status": "BLOCKED",
    }
    if not path.is_file():
        result["reason"] = "target file does not exist"
        return result
    original_bytes = path.read_bytes()
    original = original_bytes.decode("utf-8")
    baseline_hash = sha256(path)
    if original.count(control.invariant) < control.minimum_count:
        result["reason"] = "baseline invariant is missing"
        return result
    path.write_text(
        original.replace(control.invariant, "__NEGATIVE_CONTROL_REMOVED_INVARIANT__"),
        encoding="utf-8",
        newline="",
    )
    mutation_detected = not detect(control, workspace)
    path.write_bytes(original_bytes)
    restored_hash = sha256(path)
    result.update({
        "mutation_detected": mutation_detected,
        "baseline_sha256": baseline_hash,
        "restored_sha256": restored_hash,
        "restored_integrity": baseline_hash == restored_hash,
        "status": "PASS" if mutation_detected and baseline_hash == restored_hash else "FAIL",
    })
    return result


def run(mode: str, source: Path, output: Path) -> int:
    results = {
        "schema": "prislab-negative-controls-v2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "source_workspace": str(source),
        "detector_scope": "static_invariant_only",
        "checkout_mutated": False,
    }
    if mode == "dry-run":
        results["controls"] = catalog(source)
    else:
        temporary = disposable_copy(source)
        try:
            entries = catalog(temporary)
            results["controls"] = (
                entries if any(item["status"] == "BLOCKED" for item in entries)
                else [execute_control(control, temporary) for control in CONTROLS]
            )
        finally:
            shutil.rmtree(temporary, ignore_errors=True)
    statuses = [item["status"] for item in results["controls"]]
    results["summary"] = {
        "total": len(statuses),
        "pass": statuses.count("PASS"),
        "fail": statuses.count("FAIL"),
        "blocked": statuses.count("BLOCKED"),
        "ready": statuses.count("READY"),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(results["summary"], sort_keys=True))
    if mode == "dry-run":
        return 0 if results["summary"]["blocked"] == 0 else 1
    return 0 if results["summary"]["fail"] == 0 and results["summary"]["blocked"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("dry-run", "execute"), default="dry-run")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("audit/negative-controls/results.json"))
    args = parser.parse_args()
    try:
        return run(args.mode, args.workspace.resolve(), args.output.resolve())
    except Exception as exc:
        print(f"negative-controls fatal error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
