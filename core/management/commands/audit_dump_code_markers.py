"""
Vuelca marcadores TODO / FIXME / HACK / XXX a docs/audit/TODO_CODE_SCAN.txt
para gobernanza §7 (visibilidad sin revisión manual de todo el árbol).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

SKIP_DIR_NAMES = frozenset({
    'migrations', '__pycache__', 'venv', '.venv', 'env', 'node_modules',
    'staticfiles', 'media', '.git', 'htmlcov', '.pytest_cache', '.mypy_cache',
})
SCAN_TOP = ('core', 'lims', 'farmacia', 'laboratorio', 'inventario', 'recepcion',
            'mantenimiento', 'consultorio', 'marketing', 'iot', 'ia', 'bienestar',
            'seguridad', 'contabilidad', 'nomina', 'crm', 'config')
# Solo comentarios explícitos (#, //, <!--, /*) para no confundir con la palabra española "todo".
# Coincidencia: marcador en mayúsculas y plural opcional (p. ej. omni_audit: «TODOs y FIXMEs»).
_PAT_HASH_TODO = re.compile(r'#\s*TODOs?\b')
_PAT_HASH_OTHER = re.compile(r'#\s*(FIXME|HACK|XXX)s?\b', re.IGNORECASE)
_PAT_SLASH_TODO = re.compile(r'//\s*TODOs?\b')
_PAT_SLASH_OTHER = re.compile(r'//\s*(FIXME|HACK|XXX)s?\b', re.IGNORECASE)
_PAT_HTML_TODO = re.compile(r'<!--\s*TODOs?\b')
_PAT_HTML_OTHER = re.compile(r'<!--\s*(FIXME|HACK|XXX)s?\b', re.IGNORECASE)
_PAT_CSS_TODO = re.compile(r'/\*\s*TODOs?\b')
_PAT_CSS_OTHER = re.compile(r'/\*\s*(FIXME|HACK|XXX)s?\b', re.IGNORECASE)
EXT_OK = {'.py', '.html', '.js', '.css', '.ts', '.tsx', '.vue'}


def _line_has_dev_marker(line: str) -> bool:
    if _PAT_HASH_TODO.search(line) or _PAT_HASH_OTHER.search(line):
        return True
    if _PAT_SLASH_TODO.search(line) or _PAT_SLASH_OTHER.search(line):
        return True
    if _PAT_HTML_TODO.search(line) or _PAT_HTML_OTHER.search(line):
        return True
    if _PAT_CSS_TODO.search(line) or _PAT_CSS_OTHER.search(line):
        return True
    return False


class Command(BaseCommand):
    help = 'Genera docs/audit/TODO_CODE_SCAN.txt desde comentarios de deuda (apps PRISLAB).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-lines',
            type=int,
            default=8000,
            help='Tope de líneas de salida (evita archivos gigantes).',
        )

    def handle(self, *args, **options):
        max_lines: int = options['max_lines']
        root = Path(settings.BASE_DIR)
        out_path = root / 'docs' / 'audit' / 'TODO_CODE_SCAN.txt'
        out_path.parent.mkdir(parents=True, exist_ok=True)

        matches: list[str] = []
        scanned_files = 0

        for top in SCAN_TOP:
            base = root / top
            if not base.is_dir():
                continue
            for path in base.rglob('*'):
                if path.is_dir():
                    if path.name in SKIP_DIR_NAMES:
                        continue
                if not path.is_file():
                    continue
                if path.suffix.lower() not in EXT_OK:
                    continue
                parts = path.parts
                if any(p in SKIP_DIR_NAMES for p in parts):
                    continue
                scanned_files += 1
                try:
                    text = path.read_text(encoding='utf-8', errors='replace')
                except OSError:
                    continue
                rel = path.relative_to(root).as_posix()
                for i, line in enumerate(text.splitlines(), start=1):
                    if _line_has_dev_marker(line):
                        matches.append(f'{rel}:{i}:{line.strip()[:500]}')
                        if len(matches) >= max_lines:
                            break
                if len(matches) >= max_lines:
                    break
            if len(matches) >= max_lines:
                break

        iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        header = (
            f'# TODO_CODE_SCAN — generado {iso} (UTC)\n'
            f'# Comando: python manage.py audit_dump_code_markers\n'
            f'# Archivos recorridos (aprox.): {scanned_files}\n'
            f'# Coincidencias (cap {max_lines}): {len(matches)}\n'
            '# Formato: ruta:linea:contenido_truncado\n\n'
        )
        body = '\n'.join(matches)
        if len(matches) >= max_lines:
            body += '\n\n# … truncado: aumente --max-lines o refine carpetas.\n'

        out_path.write_text(header + body, encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Escrito {out_path} ({len(matches)} líneas).'))
