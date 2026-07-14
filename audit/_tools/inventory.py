"""Generate inventory summary for PRISLAB audit."""
import subprocess
import os
from collections import Counter


def count_lines(path):
    try:
        with open(path, 'rb') as fh:
            chunk = fh.read(4096)
            if b'\x00' in chunk:
                return 0  # binary
            fh.seek(0)
            return sum(1 for _ in fh)
    except Exception:
        return 0


def main():
    files = subprocess.check_output(['git', 'ls-files'], text=True).splitlines()
    exclude = {'node_modules', 'site-packages', '__pycache__', '.git', '.venv', 'venv', 'env'}
    records = []
    for f in files:
        if any(x + '/' in f or f.endswith('/' + x) or f == x for x in exclude):
            continue
        lines = count_lines(f)
        parts = f.split('/')
        top = parts[0] if parts else ''
        ext = os.path.splitext(f)[1].lower()
        records.append({'path': f, 'lines': lines, 'top': top, 'ext': ext})

    total_files = len(records)
    total_lines = sum(r['lines'] for r in records)

    top_counts = Counter(r['top'] for r in records)
    ext_counts = Counter(r['ext'] for r in records)
    largest = sorted(records, key=lambda x: x['lines'], reverse=True)[:100]

    out = []
    out.append('# Resumen de inventario PRISLAB SaaS')
    out.append('')
    out.append(f'- Total de archivos propios: {total_files}')
    out.append(f'- Total de líneas aproximadas: {total_lines}')
    out.append('')
    out.append('## Directorios principales')
    out.append('')
    out.append('| Directorio | Archivos |')
    out.append('|------------|----------|')
    for top, cnt in top_counts.most_common(50):
        out.append(f'| {top} | {cnt} |')
    out.append('')
    out.append('## Extensiones')
    out.append('')
    out.append('| Extensión | Archivos |')
    out.append('|-----------|----------|')
    for ext, cnt in ext_counts.most_common(30):
        display = ext or '(sin extensión)'
        out.append(f'| {display} | {cnt} |')
    out.append('')
    out.append('## Archivos más grandes (top 100)')
    out.append('')
    out.append('| Líneas | Archivo |')
    out.append('|--------|---------|')
    for r in largest:
        out.append(f"| {r['lines']} | `{r['path']}` |")

    os.makedirs('audit/01_backend', exist_ok=True)
    with open('audit/01_backend/_inventory_summary.md', 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))

    print('Wrote audit/01_backend/_inventory_summary.md')


if __name__ == '__main__':
    main()
