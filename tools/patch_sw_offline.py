"""One-shot patch: static/sw.js — Punto 11 precache shell + Background Sync ping."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SW = ROOT / "static" / "sw.js"
text = SW.read_text(encoding="utf-8")

old_ver = "const STATIC_CACHE_NAME = 'prislab-static-v7.0.1';"
new_ver = "const STATIC_CACHE_NAME = 'prislab-static-v7.1.0';"
if old_ver not in text:
    raise SystemExit("Expected cache version line not found; edit patch_sw_offline.py")
text = text.replace(old_ver, new_ver, 1)

old_assets = "const STATIC_ASSETS = ['/', '/static/css/prislab_shared.css', '/static/img/icon-192.svg', '/static/img/icon-512.svg', 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css', 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css', 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css'];"
new_assets = (
    "const STATIC_ASSETS = ['/', '/static/css/prislab_shared.css', '/static/js/offline_sync.js', "
    "'/static/img/icon-192.svg', '/static/img/icon-512.svg', "
    "'/laboratorio/recepcion/', '/laboratorio/', '/finanzas/lab/caja/', "
    "'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css', "
    "'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css', "
    "'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css'];"
)
if old_assets not in text:
    raise SystemExit("STATIC_ASSETS line not found")
text = text.replace(old_assets, new_assets, 1)

inject = (
    "function isOfflineShellPath(pathname) {\n"
    "  const shells = ['/laboratorio/recepcion/', '/laboratorio/', '/finanzas/lab/caja/'];\n"
    "  return shells.some(function (p) { return pathname === p; });\n"
    "}\n"
)
if "function isOfflineShellPath" not in text:
    text = text.replace(
        "function matchesPrefixList(pathname, list) { return list.some(function (p) { return pathname.indexOf(p) === 0; }); }",
        "function matchesPrefixList(pathname, list) { return list.some(function (p) { return pathname.indexOf(p) === 0; }); }\n"
        + inject,
        1,
    )

old_html = (
    "  if (request.headers.get('accept') && request.headers.get('accept').includes('text/html')) {\n"
    "    if (matchesPrefixList(url.pathname, SENSITIVE_HTML_PREFIXES)) { event.respondWith(fetch(request)); return; }"
)
new_html = (
    "  if (request.headers.get('accept') && request.headers.get('accept').includes('text/html')) {\n"
    "    if (isOfflineShellPath(url.pathname)) {\n"
    "      event.respondWith(fetch(request).then((r) => {\n"
    "        if (r && r.status === 200) { var c = r.clone(); caches.open(STATIC_CACHE_NAME).then((ch) => ch.put(request, c)); }\n"
    "        return r;\n"
    "      }).catch(() => caches.match(request).then((c) => c || new Response('<!DOCTYPE html><html><body><h1>Sin conexion</h1><p>Abra la app con red al menos una vez.</p></body></html>', { headers: { 'Content-Type': 'text/html' } }))));\n"
    "      return;\n"
    "    }\n"
    "    if (matchesPrefixList(url.pathname, SENSITIVE_HTML_PREFIXES)) { event.respondWith(fetch(request)); return; }"
)
if old_html not in text:
    raise SystemExit("HTML branch anchor not found")
text = text.replace(old_html, new_html, 1)

# Add sync listener before push listener
if "self.addEventListener('sync'" not in text:
    old_push = "self.addEventListener('push', (event) => {"
    sync_block = (
        "self.addEventListener('sync', (event) => {\n"
        "  if (event.tag === 'prislab-outbox') {\n"
        "    event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {\n"
        "      clients.forEach((c) => { try { c.postMessage({ type: 'PRISLAB_DRAIN_OUTBOX' }); } catch (e) {} });\n"
        "    }));\n"
        "  }\n"
        "});\n"
    )
    if old_push not in text:
        raise SystemExit("push listener anchor not found")
    text = text.replace(old_push, sync_block + old_push, 1)

SW.write_text(text, encoding="utf-8")
print("Patched", SW)
