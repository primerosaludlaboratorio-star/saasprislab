"""
Punto 17: barrido de patrones riesgosos en tasks / signals / management (sin rg obligatorio).
"""
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

PAT_ALL = re.compile(r"\.objects\.all\(\)")
PAT_FIRST = re.compile(r"\.objects\.first\(\)")
SKIP = {"migrations", "__pycache__", "venv", ".venv", "node_modules"}
SCAN_DIRS = (
    "core/tasks",
    "marketing",
    "contabilidad",
    "farmacia",
    "inventario",
    "iot",
    "ia",
    "bienestar",
    "seguridad",
)
SCAN_FILES = (
    "core/signals.py",
    "core/tasks.py",
)


class Command(BaseCommand):
    help = "Lista .objects.all() / .objects.first() en tasks, signals y comandos (revisión multi-tenant)."

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR)
        hits = []
        for rel in SCAN_FILES:
            p = base / rel
            if p.is_file():
                self._scan_file(p, hits)
        for d in SCAN_DIRS:
            root = base / d
            if not root.exists():
                continue
            for p in root.rglob("*.py"):
                if any(x in p.parts for x in SKIP):
                    continue
                if "management" in p.parts and "commands" in p.parts:
                    self._scan_file(p, hits)
                elif "tasks" in p.name or p.parent.name in ("tasks", "marketing"):
                    self._scan_file(p, hits)
                elif p.name == "signals.py":
                    self._scan_file(p, hits)

        for h in hits[:200]:
            self.stdout.write(h)
        if len(hits) > 200:
            self.stdout.write(self.style.WARNING(f"... y {len(hits) - 200} más"))
        self.stdout.write(self.style.NOTICE(f"Total hallazgos: {len(hits)} (revisar contexto; Celery debe filtrar por empresa_id)."))

    def _scan_file(self, path: Path, hits: list) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        for i, line in enumerate(text.splitlines(), 1):
            if PAT_ALL.search(line) or PAT_FIRST.search(line):
                if "objects.none()" in line:
                    continue
                hits.append(f"{path.relative_to(Path(settings.BASE_DIR))}:{i}:{line.strip()[:120]}")
