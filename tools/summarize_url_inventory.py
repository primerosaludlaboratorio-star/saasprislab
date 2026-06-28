import json
import os
from collections import Counter, defaultdict


def _norm_prefix(p: str) -> str:
    p = (p or '').strip()
    if not p.startswith('/'):
        p = '/' + p
    parts = [x for x in p.split('/') if x]
    if not parts:
        return '/'
    if parts[0] == 'admin':
        return '/admin/'
    return f"/{parts[0]}/"


def main():
    path = os.environ.get('URL_INVENTORY', 'tools/url_inventory.json')
    with open(path, 'r', encoding='utf-8') as f:
        d = json.load(f)

    items = d.get('items') or []

    kinds = Counter()
    prefixes = Counter()
    views_mod = Counter()
    views_full = Counter()

    for it in items:
        kinds[it.get('kind') or 'unknown'] += 1
        prefixes[_norm_prefix(it.get('path') or '')] += 1

        v = it.get('view') or ''
        views_full[v] += 1
        mod = v.split(':', 1)[0]
        if '.' in mod:
            mod = '.'.join(mod.split('.')[:2])
        views_mod[mod or 'unknown'] += 1

    top_prefixes = prefixes.most_common(30)
    top_views = views_full.most_common(30)
    top_mods = views_mod.most_common(30)

    report = {
        'protocol': 'PRISLAB_URL_INVENTORY_SUMMARY',
        'source': path,
        'count': len(items),
        'kinds': dict(kinds),
        'prefixes_top': [{'prefix': k, 'count': v} for k, v in top_prefixes],
        'view_modules_top': [{'module': k, 'count': v} for k, v in top_mods],
        'views_top': [{'view': k, 'count': v} for k, v in top_views],
    }

    out = os.environ.get('URL_INVENTORY_SUMMARY_OUT', 'tools/url_inventory_summary.json')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')

    print(json.dumps({'protocol': report['protocol'], 'ok': True, 'out': out, 'count': report['count'], 'kinds': report['kinds']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
