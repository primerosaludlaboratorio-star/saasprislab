import os
import json
import argparse
from datetime import datetime, timezone


def _iso():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _norm_prefix(p: str) -> str:
    p = (p or '').strip()
    if not p.startswith('/'):
        p = '/' + p
    if not p.endswith('/'):
        p = p + '/'
    return p


def _match_prefix(path: str, prefixes):
    p = (path or '').strip()
    if not p.startswith('/'):
        p = '/' + p
    # Más específico primero
    for pref in sorted(prefixes, key=len, reverse=True):
        if p.startswith(pref):
            return pref
    return None


def main():
    parser = argparse.ArgumentParser(description='PRISLAB Coverage Gate (inventory vs manifest)')
    parser.add_argument('--inventory', default=os.environ.get('URL_INVENTORY', 'tools/url_inventory.json'))
    parser.add_argument('--manifest', default=os.environ.get('OMNI_MANIFEST', 'tools/omni_manifest.json'))
    parser.add_argument('--out', default=os.environ.get('COVERAGE_GATE_OUT', 'tools/coverage_gate_report.json'))
    parser.add_argument('--enforce', action='store_true', default=False)
    parser.add_argument('--max-samples', type=int, default=80)
    args = parser.parse_args()

    inv = _load_json(args.inventory)
    man = _load_json(args.manifest)

    items = inv.get('items') or []
    targets = man.get('coverage_targets') or []

    prefixes = []
    prefix_to_owners = {}
    for t in targets:
        pref = _norm_prefix(t.get('prefix') or '')
        if pref == '/':
            continue
        prefixes.append(pref)
        prefix_to_owners[pref] = t.get('owners') or []

    uncovered = []
    covered = 0
    covered_by_prefix = {}
    missing_owner = []

    for it in items:
        p = it.get('path') or ''
        m = _match_prefix(p, prefixes)
        if not m:
            uncovered.append({
                'path': p,
                'kind': it.get('kind'),
                'name': it.get('name'),
                'view': it.get('view'),
            })
            continue

        covered += 1
        covered_by_prefix[m] = covered_by_prefix.get(m, 0) + 1
        if not prefix_to_owners.get(m):
            missing_owner.append({'prefix': m, 'path': p})

    total = len(items)
    uncovered_count = len(uncovered)

    report = {
        'protocol': 'PRISLAB_COVERAGE_GATE',
        'timestamp': _iso(),
        'ok': True,
        'enforce': bool(args.enforce),
        'inventory': {
            'path': args.inventory,
            'count': total,
        },
        'manifest': {
            'path': args.manifest,
            'coverage_targets_count': len(targets),
        },
        'coverage': {
            'covered': covered,
            'uncovered': uncovered_count,
            'covered_ratio': (covered / total) if total else 0.0,
            'covered_by_prefix': dict(sorted(covered_by_prefix.items(), key=lambda kv: kv[1], reverse=True)),
            'uncovered_samples': uncovered[: max(1, args.max_samples)],
            'missing_owner_prefix_samples': missing_owner[: max(1, min(50, args.max_samples))],
        },
    }

    if args.enforce and uncovered_count > 0:
        report['ok'] = False
        report['fatal'] = f"Uncovered routes detected: {uncovered_count}"

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')

    # stdout compacto para runner/CI
    print(json.dumps({
        'protocol': report['protocol'],
        'ok': report['ok'],
        'covered': report['coverage']['covered'],
        'uncovered': report['coverage']['uncovered'],
        'covered_ratio': report['coverage']['covered_ratio'],
        'out': args.out,
        'enforce': report['enforce'],
    }, ensure_ascii=False))

    if args.enforce and uncovered_count > 0:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
