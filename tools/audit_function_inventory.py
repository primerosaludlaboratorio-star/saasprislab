"""Generate a zero-omission ledger for first-party Python callables.

This is an inventory and static-verification pass, not a substitute for
behavioral tests. Every discovered function receives an explicit status so
that unverified code cannot disappear from aggregate percentages.
"""
from __future__ import annotations

import argparse
import ast
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".github",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv_audit",
    "__pycache__",
    "htmlcov",
    "logs",
    "media",
    "node_modules",
    "staticfiles",
    "venv",
}
RISK_CALLS = {
    "eval": "dynamic_execution",
    "exec": "dynamic_execution",
    "compile": "dynamic_execution",
    "os.system": "shell_execution",
    "subprocess.call": "process_execution",
    "subprocess.Popen": "process_execution",
    "subprocess.run": "process_execution",
    "pickle.load": "unsafe_deserialization",
    "pickle.loads": "unsafe_deserialization",
    "yaml.load": "unsafe_deserialization",
    "mark_safe": "html_trust_boundary",
}
STATIC_DISPOSITIONS = {
    "completar_todo_funcional.py::run_cmd": ("intentional_safe", "argv tokenized with shlex and executed without a shell"),
    "config/admin_site.py::mark_safe_header": ("requires_hardening", "unused helper trusts arbitrary text as safe HTML"),
    "core/management/commands/backup_database.py::Command.handle": ("intentional_safe", "pg_dump receives an argv list and credentials through the environment"),
    "core/management/commands/backup_nocturno.py::Command._respaldo_base_datos": ("intentional_safe", "pg_dump receives a settings-derived argv list"),
    "core/management/commands/restaurar_backup.py::Command._pg_restore": ("intentional_safe", "pg_restore receives an argv list and a validated dump path"),
    "core/management/commands/restaurar_backup.py::Command._psql_restore": ("intentional_safe", "psql receives an argv list and a validated SQL path"),
    "core/management/commands/stress_test_extremo.py::Command._detener_procesos_huerfanos": ("requires_hardening", "pkill uses a broad process-name pattern and is not portable"),
    "core/migrations/0052_notificacionpanico_fk_ordendeservicio.py::_noop_reverse": ("generated_migration_noop", "forward-only data repointing"),
    "core/migrations/0053_repoint_ia_iot_fk_ordendeservicio.py::backwards": ("generated_migration_noop", "forward-only foreign-key repointing"),
    "core/migrations/0058_resultadoparametro_analito_lims.py::_noop_reverse": ("generated_migration_noop", "forward-only LIMS data consolidation"),
    "core/migrations/0063_tejido_blando_v75_marketing_academy.py::_noop_reverse": ("generated_migration_noop", "forward-only data population"),
    "core/migrations/0067_resultadoparametro_ia_ethics_p18.py::noop_reverse": ("generated_migration_noop", "forward-only audit data population"),
    "core/migrations/0069_detalleorden_drop_legacy_estudio_id.py::_noop_reverse": ("generated_migration_noop", "destructive legacy-column removal cannot restore data"),
    "core/migrations/0070_repair_client_mutation_columns.py::_noop_reverse": ("generated_migration_noop", "idempotent schema repair has no meaningful reverse"),
    "core/migrations/0073_conveniopreciolims_and_legacy_lab_drop.py::_noop_reverse": ("generated_migration_noop", "destructive legacy-catalog consolidation"),
    "core/migrations/0078_remove_default_pin_and_disable_emergency_bypass.py::noop_reverse": ("generated_migration_noop", "security cleanup must not restore insecure defaults"),
    "core/migrations/0092_configuracionmodulos_pin_precio_neto_4_digitos.py::noop_reverse": ("generated_migration_noop", "data validation cleanup is forward-only"),
    "diagnose_and_fix_tests.py::run_tests_capture_failures": ("intentional_safe", "test runner receives a fixed argv list"),
    "e2e_test_prod.py::curl": ("intentional_safe", "curl receives caller arguments as an argv list with timeouts"),
    "generar_migraciones_consolidacion.py::main": ("intentional_safe", "Django command receives a controlled argv list"),
    "inventario/migrations/0003_salidaanaliticalab_idempotency_key.py::_noop": ("generated_migration_noop", "generated idempotency keys are not safely reversible"),
    "inventario/migrations/0004_consumoestudioreactivo_analito_lims.py::_noop": ("generated_migration_noop", "forward-only LIMS mapping"),
    "scripts/run_manage_with_env.py::main": ("intentional_safe", "manage.py receives command-line arguments as an argv list"),
}
BRANCH_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.BoolOp,
    ast.IfExp,
    ast.Match,
    ast.comprehension,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _category(path: Path) -> str:
    parts = set(path.parts)
    name = path.name.lower()
    if "migrations" in parts:
        return "migration"
    if "tests" in parts or name.startswith("test_") or name in {"tests.py", "tests_e2e.py"}:
        return "test"
    if "management" in parts and "commands" in parts:
        return "management_command"
    if path.parts and path.parts[0] in {"tools", "scripts"}:
        return "tooling"
    if "views" in parts or name.startswith("views") or name.endswith("_views.py"):
        return "view"
    if "models" in parts or name.startswith("models"):
        return "model"
    if "services" in parts or name.startswith("services"):
        return "service"
    return "application"


def _iter_python_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        files.append(path)
    return sorted(files)


class FunctionVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: Path):
        self.rel_path = rel_path
        self.scope: list[str] = []
        self.items: list[dict] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record(node, is_async=True)

    def _record(self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_async: bool) -> None:
        qualname = ".".join([*self.scope, node.name])
        definition_key = f"{self.rel_path.as_posix()}::{qualname}"
        function_id = f"{definition_key}@{node.lineno}"
        calls = Counter()
        risks = set()
        branches = 0
        raises_not_implemented = False
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call = _call_name(child.func)
                if call:
                    calls[call] += 1
                    for risky_call, risk in RISK_CALLS.items():
                        if call == risky_call:
                            risks.add(risk)
            if isinstance(child, BRANCH_NODES):
                branches += 1
            if (
                isinstance(child, ast.Raise)
                and isinstance(child.exc, ast.Call)
                and _call_name(child.exc.func) == "NotImplementedError"
            ):
                raises_not_implemented = True

        body_without_docstring = list(node.body)
        if body_without_docstring and isinstance(body_without_docstring[0], ast.Expr):
            value = body_without_docstring[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                body_without_docstring.pop(0)
        empty = len(body_without_docstring) == 1 and (
            isinstance(body_without_docstring[0], ast.Pass)
            or (
                isinstance(body_without_docstring[0], ast.Expr)
                and isinstance(body_without_docstring[0].value, ast.Constant)
                and body_without_docstring[0].value.value is Ellipsis
            )
        )
        decorators = [_call_name(item) for item in node.decorator_list]
        is_test = node.name.startswith("test_") or _category(self.rel_path) == "test"
        static_status = "static_review_flagged" if (risks or empty or raises_not_implemented) else "static_review_passed"
        disposition, disposition_reason = STATIC_DISPOSITIONS.get(definition_key, (None, None))

        self.items.append(
            {
                "id": function_id,
                "file": self.rel_path.as_posix(),
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "qualname": qualname,
                "category": _category(self.rel_path),
                "async": is_async,
                "is_test": is_test,
                "decorators": [item for item in decorators if item],
                "arguments": len(node.args.posonlyargs) + len(node.args.args) + len(node.args.kwonlyargs),
                "complexity_proxy": 1 + branches,
                "has_docstring": ast.get_docstring(node, clean=False) is not None,
                "empty_body": empty,
                "raises_not_implemented": raises_not_implemented,
                "risk_signals": sorted(risks),
                "calls_count": sum(calls.values()),
                "static_status": static_status,
                "static_disposition": disposition,
                "static_disposition_reason": disposition_reason,
                "behavioral_status": "test_definition" if is_test else "not_demonstrated_per_function",
            }
        )
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()


def _normalize_coverage_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _load_coverage(path: Path | None) -> tuple[dict, dict, dict | None]:
    if path is None:
        return {}, {}, None
    payload = json.loads(path.read_text(encoding="utf-8"))
    branch_coverage = bool(payload.get("meta", {}).get("branch_coverage"))
    index = {}
    measured_files = {}
    for file_name, file_data in payload.get("files", {}).items():
        normalized_file = _normalize_coverage_path(file_name)
        measured_files[normalized_file] = file_data
        for qualname, function_data in file_data.get("functions", {}).items():
            if qualname:
                index[(normalized_file, qualname, function_data.get("start_line"))] = function_data
    return index, measured_files, {
        "path": str(path),
        "coverage_version": payload.get("meta", {}).get("version"),
        "timestamp": payload.get("meta", {}).get("timestamp"),
        "branch_coverage": branch_coverage,
    }


def _apply_coverage(
    functions: list[dict], coverage_index: dict, measured_files: dict, coverage_meta: dict | None
) -> None:
    if coverage_meta is None:
        return
    for item in functions:
        measured = coverage_index.get((item["file"], item["qualname"], item["line"]))
        if measured is None:
            file_data = measured_files.get(item["file"])
            if file_data is None:
                item["behavioral_status"] = "not_measured"
                item["coverage"] = None
                continue
            nested_ranges = [
                (other["line"], other["end_line"])
                for other in functions
                if other["file"] == item["file"]
                and other["line"] > item["line"]
                and other["end_line"] <= item["end_line"]
                and other["qualname"].startswith(f"{item['qualname']}.")
            ]
            belongs_to_function = lambda line: (
                item["line"] <= line <= item["end_line"]
                and not any(start <= line <= end for start, end in nested_ranges)
            )
            executed_lines = [line for line in file_data["executed_lines"] if belongs_to_function(line)]
            missing_lines = [line for line in file_data["missing_lines"] if belongs_to_function(line)]
            executed_branches = [arc for arc in file_data["executed_branches"] if belongs_to_function(arc[0])]
            missing_branches = [arc for arc in file_data["missing_branches"] if belongs_to_function(arc[0])]
            statement_count = len(executed_lines) + len(missing_lines)
            branch_count = len(executed_branches) + len(missing_branches)
            summary = {
                "num_statements": statement_count,
                "covered_lines": len(executed_lines),
                "missing_lines": len(missing_lines),
                "percent_statements_covered": 100 * len(executed_lines) / statement_count if statement_count else 100.0,
                "covered_branches": len(executed_branches),
                "missing_branches": len(missing_branches),
                "percent_branches_covered": 100 * len(executed_branches) / branch_count if branch_count else 100.0,
            }
            item["coverage_match"] = "ast_range_fallback"
        else:
            summary = measured["summary"]
            item["coverage_match"] = "coverage_function_identity"
        if summary["num_statements"] == 0:
            status = "no_executable_statements"
        elif summary["covered_lines"] == 0:
            status = "not_executed"
        elif summary["missing_lines"] == 0 and (
            not coverage_meta["branch_coverage"] or summary["missing_branches"] == 0
        ):
            status = "fully_covered"
        else:
            status = "partially_covered"
        item["behavioral_status"] = status
        item["coverage"] = {
            "covered_lines": summary["covered_lines"],
            "missing_lines": summary["missing_lines"],
            "line_percent": summary["percent_statements_covered"],
            "covered_branches": summary["covered_branches"],
            "missing_branches": summary["missing_branches"],
            "branch_percent": summary["percent_branches_covered"],
        }


def build_inventory(coverage_path: Path | None = None) -> dict:
    functions: list[dict] = []
    syntax_errors: list[dict] = []
    files = _iter_python_files()
    for path in files:
        rel = path.relative_to(ROOT)
        try:
            source = path.read_text(encoding="utf-8-sig", errors="strict")
            tree = ast.parse(source, filename=str(rel))
        except (OSError, UnicodeError, SyntaxError) as exc:
            syntax_errors.append(
                {
                    "file": rel.as_posix(),
                    "line": getattr(exc, "lineno", None),
                    "error": str(exc),
                }
            )
            continue
        visitor = FunctionVisitor(rel)
        visitor.visit(tree)
        functions.extend(visitor.items)

    grouped_definitions = defaultdict(list)
    for item in functions:
        grouped_definitions[(item["file"], item["qualname"])].append(item)
    definition_collisions = []
    for (file_name, qualname), definitions in grouped_definitions.items():
        if len(definitions) < 2:
            continue
        decorators = {decorator for item in definitions for decorator in item["decorators"]}
        intentional_descriptor = "property" in decorators and any(
            decorator.endswith(".setter") or decorator.endswith(".deleter")
            for decorator in decorators
        )
        status = "intentional_descriptor_pair" if intentional_descriptor else "shadowed_redefinition"
        for item in definitions:
            item["definition_collision_status"] = status
        definition_collisions.append(
            {
                "key": f"{file_name}::{qualname}",
                "status": status,
                "definitions": [item["id"] for item in definitions],
            }
        )

    coverage_index, measured_files, coverage_meta = _load_coverage(coverage_path)
    _apply_coverage(functions, coverage_index, measured_files, coverage_meta)

    by_category = Counter(item["category"] for item in functions)
    by_static_status = Counter(item["static_status"] for item in functions)
    by_static_disposition = Counter(
        item["static_disposition"] for item in functions if item["static_disposition"]
    )
    risk_signals = Counter(
        risk for item in functions for risk in item["risk_signals"]
    )
    production = [item for item in functions if item["category"] not in {"test", "migration", "tooling"}]
    behaviorally_unverified = [
        item for item in production
        if item["behavioral_status"] not in {"fully_covered", "partially_covered"}
    ]
    by_behavioral_status = Counter(item["behavioral_status"] for item in production)
    return {
        "protocol": "PRISLAB_FUNCTION_INVENTORY_V1",
        "timestamp": _iso_now(),
        "root": str(ROOT),
        "scope": {
            "extensions": [".py"],
            "excluded_directories": sorted(SKIP_DIRS),
            "note": "First-party Python only; JavaScript/templates require a separate parser-backed ledger.",
        },
        "coverage_evidence": coverage_meta,
        "summary": {
            "python_files": len(files),
            "functions": len(functions),
            "production_functions": len(production),
            "behaviorally_unverified_production_functions": len(behaviorally_unverified),
            "syntax_errors": len(syntax_errors),
            "by_category": dict(sorted(by_category.items())),
            "by_static_status": dict(sorted(by_static_status.items())),
            "by_static_disposition": dict(sorted(by_static_disposition.items())),
            "production_by_behavioral_status": dict(sorted(by_behavioral_status.items())),
            "static_flags_without_disposition": sum(
                item["static_status"] == "static_review_flagged" and not item["static_disposition"]
                for item in functions
            ),
            "definition_collision_groups": len(definition_collisions),
            "shadowed_redefinition_groups": sum(
                item["status"] == "shadowed_redefinition" for item in definition_collisions
            ),
            "risk_signals": dict(sorted(risk_signals.items())),
        },
        "syntax_errors": syntax_errors,
        "definition_collisions": definition_collisions,
        "functions": functions,
    }


def write_markdown(payload: dict, path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# Ledger de funciones Python",
        "",
        f"Generado: `{payload['timestamp']}`",
        "",
        "## Resumen",
        "",
        f"- Archivos Python propios: **{summary['python_files']}**",
        f"- Funciones/métodos descubiertos: **{summary['functions']}**",
        f"- Funciones productivas: **{summary['production_functions']}**",
        f"- Funciones productivas sin demostración conductual individual: **{summary['behaviorally_unverified_production_functions']}**",
        f"- Errores de sintaxis/lectura: **{summary['syntax_errors']}**",
        f"- Señales estáticas sin disposición: **{summary['static_flags_without_disposition']}**",
        f"- Grupos de redefiniciones sombreadas: **{summary['shadowed_redefinition_groups']}**",
        "",
        "> `static_review_passed` sólo significa que el AST se pudo inspeccionar y no activó las señales incluidas. No demuestra corrección funcional.",
        "",
        "## Evidencia conductual",
        "",
    ]
    coverage_evidence = payload.get("coverage_evidence")
    if coverage_evidence:
        lines.extend(
            [
                f"- Fuente: `{coverage_evidence['path']}`",
                f"- Coverage.py: `{coverage_evidence['coverage_version']}`",
                f"- Cobertura de ramas: **{'sí' if coverage_evidence['branch_coverage'] else 'no'}**",
                "",
                "| Estado productivo | Funciones |",
                "|---|---:|",
            ]
        )
        for status, count in summary["production_by_behavioral_status"].items():
            lines.append(f"| {status} | {count} |")
    else:
        lines.append("- No se proporcionó evidencia de cobertura instrumentada.")
    lines.extend(
        [
            "",
            "> La cobertura demuestra ejecución de sentencias/ramas, no corrección semántica ni suficiencia de las aserciones.",
            "",
            "## Conteo por categoría",
            "",
            "| Categoría | Funciones |",
            "|---|---:|",
        ]
    )
    for category, count in summary["by_category"].items():
        lines.append(f"| {category} | {count} |")
    lines.extend(
        [
            "",
            "## Definiciones marcadas",
            "",
            "| ID | Disposición | Señales | Evidencia |",
            "|---|---|---|---|",
        ]
    )
    flagged = [item for item in payload["functions"] if item["static_status"] == "static_review_flagged"]
    for item in flagged:
        signals = list(item["risk_signals"])
        if item["empty_body"]:
            signals.append("empty_body")
        if item["raises_not_implemented"]:
            signals.append("not_implemented")
        lines.append(
            f"| `{item['id']}` | {item['static_disposition'] or 'pending_review'} | "
            f"{', '.join(signals)} | {item['static_disposition_reason'] or '-'} |"
        )
    if not flagged:
        lines.append("| _Ninguna_ | - | - | - |")
    lines.extend(
        [
            "",
            "## Colisiones de definición",
            "",
            "| Nombre | Disposición | Definiciones |",
            "|---|---|---|",
        ]
    )
    for collision in payload["definition_collisions"]:
        definitions = "<br>".join(f"`{item}`" for item in collision["definitions"])
        lines.append(f"| `{collision['key']}` | {collision['status']} | {definitions} |")
    if not payload["definition_collisions"]:
        lines.append("| _Ninguna_ | - | - |")
    lines.extend(
        [
            "",
            "## Limitación obligatoria",
            "",
            "Este ledger garantiza censo AST de las definiciones Python dentro del alcance declarado. No permite afirmar que cada función sea correcta: para eso cada función productiva debe quedar enlazada a una prueba conductual y cobertura de ramas, y las integraciones deben verificarse en el entorno objetivo.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default="audit/function_inventory.json")
    parser.add_argument("--markdown", default="audit/FUNCTION_LEDGER.md")
    parser.add_argument("--coverage-json")
    parser.add_argument("--fail-on-syntax-error", action="store_true")
    parser.add_argument("--fail-on-coverage-unmatched", action="store_true")
    args = parser.parse_args()

    coverage_path = ROOT / args.coverage_json if args.coverage_json else None
    payload = build_inventory(coverage_path)
    json_path = ROOT / args.json
    markdown_path = ROOT / args.markdown
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, markdown_path)
    print(json.dumps(payload["summary"], ensure_ascii=False))
    if args.fail_on_syntax_error and payload["syntax_errors"]:
        return 1
    if args.fail_on_coverage_unmatched and payload["summary"]["production_by_behavioral_status"].get("coverage_unmatched"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())