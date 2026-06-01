import os
import sys
import json
import argparse
from datetime import datetime, timezone


def _iso():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _pattern_to_str(p):
    try:
        # Django 2/3/4: RoutePattern/RegexPattern
        return str(getattr(p, "pattern", p))
    except Exception:
        return str(p)


def _iter_urlpatterns(urlpatterns, prefix=""):
    for p in urlpatterns:
        try:
            pattern = _pattern_to_str(p.pattern)
        except Exception:
            pattern = ""

        full = (prefix + pattern).replace("//", "/")

        # include()
        if hasattr(p, "url_patterns") and p.url_patterns is not None:
            yield from _iter_urlpatterns(p.url_patterns, prefix=full)
            continue

        cb = getattr(p, "callback", None)
        if cb is None:
            continue

        view_name = None
        try:
            view_name = f"{cb.__module__}.{getattr(cb, '__name__', cb.__class__.__name__)}"
        except Exception:
            view_name = str(cb)

        url_name = getattr(p, "name", None)

        yield {
            "path": "/" + full.lstrip("/"),
            "name": url_name,
            "view": view_name,
            "lookup_str": getattr(p, "lookup_str", None),
            "default_args": getattr(p, "default_args", None),
        }


def main():
    # Asegura que el repo root esté en sys.path.
    # Si ejecutas: `python tools/audit_url_inventory.py`, sys.path[0] queda en /tools
    # y Django no encuentra el paquete `config`.
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    parser = argparse.ArgumentParser(description='PRISLAB URL Inventory Auditor')
    parser.add_argument('--out', default=os.environ.get('URL_INVENTORY_OUT') or '', help='Ruta de salida (UTF-8).')
    args = parser.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings"))

    try:
        import django

        django.setup()
    except Exception as e:
        print(
            json.dumps(
                {
                    "protocol": "PRISLAB_URL_INVENTORY",
                    "timestamp": _iso(),
                    "ok": False,
                    "fatal": str(e),
                },
                indent=2,
            )
        )
        raise

    from django.conf import settings
    from django.urls import get_resolver

    resolver = get_resolver()
    items = list(_iter_urlpatterns(resolver.url_patterns, prefix=""))

    # Clasificación heurística (se refina con el tiempo)
    for it in items:
        p = (it.get("path") or "").lower()
        if p.startswith("/api/") or "/api/" in p:
            it["kind"] = "api"
        elif "/imprimir/" in p or p.endswith("/pdf/") or "/pdf" in p:
            it["kind"] = "pdf"
        else:
            it["kind"] = "ui"

    payload = {
        "protocol": "PRISLAB_URL_INVENTORY",
        "timestamp": _iso(),
        "ok": True,
        "settings": {
            "root_urlconf": getattr(settings, "ROOT_URLCONF", None),
            "installed_apps_count": len(getattr(settings, "INSTALLED_APPS", []) or []),
        },
        "count": len(items),
        "items": items,
    }

    out_path = (args.out or '').strip()
    if out_path:
        out_abs = out_path
        if not os.path.isabs(out_abs):
            out_abs = os.path.abspath(os.path.join(repo_root, out_path))
        os.makedirs(os.path.dirname(out_abs), exist_ok=True)
        with open(out_abs, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
            f.write('\n')
        # Mantener stdout corto para CI
        print(json.dumps({"protocol": payload["protocol"], "ok": True, "count": payload["count"], "out": out_abs}, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
