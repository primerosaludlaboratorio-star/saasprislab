#!/usr/bin/env python3
"""
Cierra todos los issues abiertos de un repositorio GitHub (API REST v3).

Autenticación (una de):
  - Variable de entorno GITHUB_TOKEN o GH_TOKEN (classic: repo scope)
  - gh auth token (si usas GitHub CLI): export GITHUB_TOKEN=$(gh auth token)

Repositorio:
  - GITHUB_REPOSITORY=owner/repo (como en Actions)
  - o argumentos: --repo owner/nombre

Uso:
  python tools/github_close_all_issues.py --dry-run
  python tools/github_close_all_issues.py
  python tools/github_close_all_issues.py --repo mi-org/PRISLAB_SaaS

Alternativa rápida (GitHub CLI, bash):
  gh issue list --state open --limit 1000 --json number -q '.[].number' | xargs -n1 gh issue close

PowerShell:
  gh issue list --state open --limit 1000 --json number -q '.[].number' | ConvertFrom-Json | ForEach-Object { gh issue close $_ }
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def _request(method: str, url: str, token: str, data: dict | None = None) -> tuple[int, bytes]:
    body = None
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def list_open_issue_numbers(owner: str, repo: str, token: str) -> list[int]:
    numbers: list[int] = []
    page = 1
    per_page = 100
    while True:
        url = (
            f'https://api.github.com/repos/{owner}/{repo}/issues'
            f'?state=open&per_page={per_page}&page={page}'
        )
        code, raw = _request('GET', url, token)
        if code != 200:
            sys.stderr.write(f'Error listando issues HTTP {code}: {raw.decode("utf-8", errors="replace")[:500]}\n')
            sys.exit(1)
        batch = json.loads(raw.decode('utf-8'))
        if not batch:
            break
        for item in batch:
            # Los pull requests aparecen en /issues; se distinguen por "pull_request" in item
            if item.get('pull_request'):
                continue
            numbers.append(int(item['number']))
        if len(batch) < per_page:
            break
        page += 1
    return numbers


def close_issue(owner: str, repo: str, token: str, number: int) -> bool:
    url = f'https://api.github.com/repos/{owner}/{repo}/issues/{number}'
    code, raw = _request('PATCH', url, token, {'state': 'closed'})
    if code not in (200, 201):
        sys.stderr.write(
            f'No se pudo cerrar #{number} HTTP {code}: {raw.decode("utf-8", errors="replace")[:300]}\n'
        )
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description='Cerrar todos los issues abiertos en GitHub')
    parser.add_argument('--repo', help='owner/repo (si no está GITHUB_REPOSITORY)')
    parser.add_argument('--dry-run', action='store_true', help='Solo listar números, sin PATCH')
    args = parser.parse_args()

    token = (os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN') or '').strip()
    if not token:
        print('Falta GITHUB_TOKEN o GH_TOKEN en el entorno.', file=sys.stderr)
        sys.exit(2)

    repo_spec = args.repo or os.environ.get('GITHUB_REPOSITORY', '').strip()
    if not repo_spec or '/' not in repo_spec:
        print('Especifica --repo owner/nombre o exporta GITHUB_REPOSITORY=owner/nombre.', file=sys.stderr)
        sys.exit(2)

    owner, repo = repo_spec.split('/', 1)
    numbers = list_open_issue_numbers(owner, repo, token)
    print(f'Repositorio {owner}/{repo}: {len(numbers)} issues abiertos (excl. PRs).')

    if args.dry_run:
        print('Dry-run:', numbers[:50], '...' if len(numbers) > 50 else '')
        return

    ok = 0
    for num in numbers:
        if close_issue(owner, repo, token, num):
            ok += 1
            print(f'  cerrado #{num}')
    print(f'Total cerrados: {ok}/{len(numbers)}')


if __name__ == '__main__':
    main()
