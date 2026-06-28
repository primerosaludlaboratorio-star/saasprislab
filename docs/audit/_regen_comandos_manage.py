# Regenera COMANDOS_MANAGE_PY.md — inventario de management commands
# Uso: python docs/audit/_regen_comandos_manage.py (desde la raíz del repo)
from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "audit" / "COMANDOS_MANAGE_PY.md"


def main() -> None:
    cmds: list[tuple[str, str, str]] = []
    for p in REPO.rglob("management/commands/*.py"):
        if p.name.startswith("_") or p.name == "__init__.py":
            continue
        rel = p.relative_to(REPO)
        app = rel.parts[0]
        cmds.append((app, p.stem, rel.as_posix()))

    cmds.sort(key=lambda x: (x[0], x[1]))
    lines = [
        "# COMANDOS_MANAGE_PY — Inventario exhaustivo",
        "",
        "**Total:** %d comandos (`__init__.py` excluido)." % len(cmds),
        "",
        "| App | Comando | Archivo |",
        "|:---|:---|:---|",
    ]
    for app, stem, rel in cmds:
        lines.append("| %s | `%s` | `%s` |" % (app, stem, rel))

    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("OK:", OUT, "count", len(cmds))


if __name__ == "__main__":
    main()
