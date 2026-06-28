// Service Worker PRISLAB v6.2 — rutas clinicas/financieras sin cache persistente
const STATIC_CACHE_NAME = 'prislab-static-v7.1.0';
const DYNAMIC_CACHE_NAME = 'prislab-dynamic-v7.0.1';
const SENSITIVE_PREFIXES = ['/api/', '/admin/', '/laboratorio/api/', '/farmacia/api/', '/lims/api/', '/marketing/api/', '/seguridad/api/', '/ia/', '/contabilidad/', '/consultorio/', '/enfermeria/', '/expediente', '/bienestar/', '/caja', '/orden/', '/pago/'];
const SENSITIVE_HTML_PREFIXES = ['/contabilidad/', '/consultorio/', '/enfermeria/', '/farmacia/pdv', '/laboratorio/', '/expediente', '/caja', '/marketing/', '/seguridad/', '/bienestar/', '/ia/', '/mantenimiento/', '/home/', '/login/', '/dashboard/'];
function matchesPrefixList(pathname, list) { return list.some(function (p) { return pathname.indexOf(p) === 0; }); }
function isOfflineShellPath(pathname) {
  const shells = ['/laboratorio/recepcion/', '/laboratorio/', '/finanzas/lab/caja/'];
  return shells.some(function (p) { return pathname === p; });
}

const STATIC_ASSETS = ['/static/css/prislab_shared.css', '/static/js/offline_sync.js', '/static/img/icon-192.svg', '/static/img/icon-512.svg', '/laboratorio/recepcion/', '/laboratorio/', '/finanzas/lab/caja/', 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css', 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css', 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css'];
self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(STATIC_CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS.map(url => { try { return new Request(url, { mode: 'no-cors' }); } catch (e) { return url; } }))).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((names) => Promise.all(names.map((cn) => { if (cn !== STATIC_CACHE_NAME && cn !== DYNAMIC_CACHE_NAME && cn.startsWith('prislab-')) return caches.delete(cn); }))));
  return self.clients.claim();
});
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET') return;
  if (url.pathname.indexOf('/farmacia/pdv/buscar-fragmento') !== -1) return;
  if (matchesPrefixList(url.pathname, SENSITIVE_PREFIXES)) {
    event.respondWith(fetch(request).catch(() => new Response(JSON.stringify({ detail: 'offline' }), { status: 503, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } })));
    return;
  }
  if (url.pathname.startsWith('/static/js/')) {
    event.respondWith(fetch(request).then((r) => { if (r && r.status === 200) { var c = r.clone(); caches.open(STATIC_CACHE_NAME).then((ch) => ch.put(request, c)); } return r; }).catch(() => caches.match(request)));
    return;
  }
  if (url.pathname.startsWith('/static/') || url.origin.includes('cdn.jsdelivr') || url.origin.includes('cdnjs.cloudflare')) {
    event.respondWith(caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((r) => {
        if (!r || r.status !== 200) return r;
        var c = r.clone();
        caches.open(STATIC_CACHE_NAME).then((ch) => ch.put(request, c));
        return r;
      }).catch(() => { if (request.destination === 'image') return new Response('', { status: 404 }); });
    }));
    return;
  }
  if (request.headers.get('accept') && request.headers.get('accept').includes('text/html')) {
    if (url.pathname === '/' || url.pathname === '/login/' || url.pathname === '/home/' || url.pathname === '/dashboard/') {
      event.respondWith(fetch(request, { cache: 'no-store', credentials: 'include' }));
      return;
    }
    if (isOfflineShellPath(url.pathname)) {
      event.respondWith(fetch(request).then((r) => {
        if (r && r.status === 200) { var c = r.clone(); caches.open(STATIC_CACHE_NAME).then((ch) => ch.put(request, c)); }
        return r;
      }).catch(() => caches.match(request).then((c) => c || new Response('<!DOCTYPE html><html><body><h1>Sin conexion</h1><p>Abra la app con red al menos una vez.</p></body></html>', { headers: { 'Content-Type': 'text/html' } }))));
      return;
    }
    if (matchesPrefixList(url.pathname, SENSITIVE_HTML_PREFIXES)) { event.respondWith(fetch(request)); return; }
    event.respondWith(fetch(request).then((r) => {
      if (r.status === 200) { var c = r.clone(); caches.open(DYNAMIC_CACHE_NAME).then((ch) => ch.put(request, c)); }
      return r;
    }).catch(() => caches.match(request).then((c) => c || new Response('<!DOCTYPE html><html><body><h1>Sin conexion</h1></body></html>', { headers: { 'Content-Type': 'text/html' } }))));
    return;
  }
  if (matchesPrefixList(url.pathname, SENSITIVE_HTML_PREFIXES)) { event.respondWith(fetch(request)); return; }
  event.respondWith(fetch(request).then((r) => {
    if (r.status === 200) { var c = r.clone(); caches.open(DYNAMIC_CACHE_NAME).then((ch) => ch.put(request, c)); }
    return r;
  }).catch(() => caches.match(request)));
});
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
  if (event.data && event.data.type === 'CLEAR_CACHE') { caches.delete(STATIC_CACHE_NAME); caches.delete(DYNAMIC_CACHE_NAME); }
  if (event.data && event.data.type === 'FORENSIC_LOGOUT') {
    event.waitUntil(caches.keys().then((names) => Promise.all(names.map((n) => caches.delete(n)))));
  }
});
self.addEventListener('sync', (event) => {
  if (event.tag === 'prislab-outbox') {
    event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      clients.forEach((c) => { try { c.postMessage({ type: 'PRISLAB_DRAIN_OUTBOX' }); } catch (e) {} });
    }));
  }
});
self.addEventListener('push', (event) => {
  var nd = { title: 'PRISLAB', body: 'Nueva notificacion', icon: '/static/images/icons/icon-192x192.png', badge: '/static/images/icons/icon-72x72.png', vibrate: [200, 100, 200], tag: 'prislab-notification', requireInteraction: true, data: { url: '/' } };
  if (event.data) {
    try {
      var p = event.data.json();
      nd = { title: p.title || nd.title, body: p.body || nd.body, icon: p.icon || nd.icon, badge: p.badge || nd.badge, vibrate: p.vibrate || nd.vibrate, tag: p.tag || nd.tag, requireInteraction: p.requireInteraction !== false, data: { url: p.url || '/', incidenciaId: p.incidenciaId, severidad: p.severidad, isla: p.isla }, actions: p.actions || [{ action: 'open', title: 'Ver Detalle' }, { action: 'close', title: 'Cerrar' }] };
    } catch (e) { console.error('[SW] push parse', e); }
  }
  event.waitUntil(self.registration.showNotification(nd.title, nd));
});
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'close') return;
  var urlToOpen = event.notification.data && event.notification.data.url ? event.notification.data.url : '/';
  event.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
    for (var i = 0; i < list.length; i++) {
      if (list[i].url.includes(self.registration.scope) && 'focus' in list[i]) {
        return list[i].focus().then(function (c) { if (c.navigate) return c.navigate(urlToOpen); });
      }
    }
    if (clients.openWindow) return clients.openWindow(urlToOpen);
  }));
});
self.addEventListener('notificationclose', function () {});
