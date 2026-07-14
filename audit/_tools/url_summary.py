import json
from collections import Counter

with open('tools/url_inventory.json') as f:
    d = json.load(f)

items = d.get('items', [])

kinds = Counter(i.get('kind', 'unknown') for i in items)

# Count by top-level path
paths = Counter()
for i in items:
    p = i.get('path', '')
    if p.startswith('/'):
        seg = p.split('/')[1]
    else:
        seg = 'root'
    paths[seg] += 1

non_admin = [i for i in items if not i.get('path', '').startswith('/admin/')]

out = []
out.append('# Resumen de inventario de URLs/API')
out.append('')
out.append(f'- Total de rutas: {len(items)}')
out.append(f'- Rutas no-admin: {len(non_admin)}')
out.append(f'- Protocolo: {d.get("protocol")}')
out.append(f'- OK: {d.get("ok")}')
out.append('')
out.append('## Distribución por tipo')
out.append('')
out.append('| Tipo | Cantidad |')
out.append('|------|----------|')
for kind, cnt in kinds.most_common():
    out.append(f'| {kind} | {cnt} |')
out.append('')
out.append('## Distribución por segmento raíz')
out.append('')
out.append('| Segmento | Cantidad |')
out.append('|----------|----------|')
for seg, cnt in paths.most_common(40):
    out.append(f'| /{seg} | {cnt} |')
out.append('')
out.append('## Muestra de rutas no-admin')
out.append('')
out.append('| Ruta | Nombre | View | Tipo |')
out.append('|------|--------|------|------|')
for i in non_admin[:50]:
    view = i.get('lookup_str', i.get('view', ''))[:60]
    out.append(f"| `{i.get('path')}` | {i.get('name') or '-'} | `{view}` | {i.get('kind')} |")

with open('audit/04_api/_api_inventory_summary.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print('Wrote audit/04_api/_api_inventory_summary.md')
