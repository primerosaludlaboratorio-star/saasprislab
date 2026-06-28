# Regenera FUNCIONES_EXHAUSTIVO_POR_RUTA.md desde INVENTARIO_URLS.txt
# Uso: python docs/audit/_regen_exhaustivo_rutas.py (desde la raíz del repo)
from __future__ import annotations

import json
import os
from collections import defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
INV = os.path.join(REPO, "docs", "audit", "INVENTARIO_URLS.txt")
OUT = os.path.join(REPO, "docs", "audit", "FUNCIONES_EXHAUSTIVO_POR_RUTA.md")


def main() -> None:
    with open(INV, encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items") or []
    by_seg: dict[str, list] = defaultdict(list)
    for it in items:
        p = (it.get("path") or "/").strip() or "/"
        # Primer segmento útil (saltar ^ de regex en algunos paths)
        clean = p.lstrip("^")
        parts = [x for x in clean.split("/") if x and not x.startswith("(")]
        key = parts[0] if parts else "(root)"
        if key.startswith("^"):
            key = key[1:]
        by_seg[key].append(it)

    lines: list[str] = []
    lines.append("# FUNCIONES_EXHAUSTIVO — Inventario por ruta (URLconf)")
    lines.append("")
    lines.append("**Origen:** `docs/audit/INVENTARIO_URLS.txt` (mismo timestamp que el JSON).")
    lines.append("**Total de rutas registradas:** %d" % len(items))
    lines.append("")
    lines.append("Cada fila es una entrada resuelta por Django: path + nombre de ruta + vista.")
    lines.append("")

    for key in sorted(by_seg.keys(), key=lambda k: (k == "(root)", k)):
        lst = sorted(by_seg[key], key=lambda x: (x.get("path") or "", x.get("name") or ""))
        label = key if key != "(root)" else "root"
        lines.append("## Prefijo `/%s/` (%d rutas)" % (label, len(lst)))
        lines.append("")
        lines.append("| Path | name | Vista (callback) | kind |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for it in lst:
            path = (it.get("path") or "").replace("|", "\\|")
            name = (str(it.get("name") or "—")).replace("|", "\\|")
            view = (str(it.get("view") or "—")).replace("|", "\\|")[:200]
            kind = str(it.get("kind") or "—")
            lines.append("| `%s` | %s | `%s` | %s |" % (path, name, view, kind))
        lines.append("")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("OK:", OUT, "lines", len(lines), "routes", len(items))


if __name__ == "__main__":
    main()
