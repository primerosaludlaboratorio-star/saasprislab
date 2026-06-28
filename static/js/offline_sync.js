/**
 * PRISLAB — cola IndexedDB (outbox) + sincronización híbrida (Background Sync + online).
 * MVP Punto 11: mutaciones POST con client_mutation_id en servidor.
 * Copia canónica desplegada: static/js/offline_sync.js (ver scripts/copy_offline_assets.py).
 */
(function (global) {
  'use strict';

  var DB_NAME = 'prislab-offline';
  var DB_VERSION = 1;
  var STORE = 'outbox';
  var SYNC_TAG = 'prislab-outbox';

  function openDb() {
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onerror = function () { reject(req.error); };
      req.onsuccess = function () { resolve(req.result); };
      req.onupgradeneeded = function (e) {
        var db = e.target.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: 'id' });
        }
      };
    });
  }

  function uuidv4() {
    if (global.crypto && typeof global.crypto.randomUUID === 'function') {
      return global.crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0;
      var v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  function getCsrf() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute('content') : '';
  }

  function enqueue(endpoint, payload) {
    var id = uuidv4();
    var body = Object.assign({}, payload || {});
    if (!body.client_mutation_id) body.client_mutation_id = uuidv4();
    var rec = {
      id: id,
      endpoint: endpoint,
      payload_json: body,
      timestamp: Date.now(),
      intentos: 0,
      estado: 'PENDING',
    };
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).put(rec);
        tx.oncomplete = function () { db.close(); resolve(rec); };
        tx.onerror = function () { db.close(); reject(tx.error); };
      });
    }).then(function (r) {
      return registerBackgroundSync().then(function () { return r; });
    }).then(function (r) {
      notifyCountUpdate();
      if (navigator.onLine) drainOutboxSoon();
      return r;
    });
  }

  function listPending() {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, 'readonly');
        var rq = tx.objectStore(STORE).getAll();
        rq.onsuccess = function () {
          var all = rq.result || [];
          db.close();
          resolve(all.filter(function (r) { return r.estado === 'PENDING'; }));
        };
        rq.onerror = function () { db.close(); reject(rq.error); };
      });
    });
  }

  function putRecord(rec) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).put(rec);
        tx.oncomplete = function () { db.close(); resolve(); };
        tx.onerror = function () { db.close(); reject(tx.error); };
      });
    });
  }

  function deleteRecord(id) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).delete(id);
        tx.oncomplete = function () { db.close(); resolve(); };
        tx.onerror = function () { db.close(); reject(tx.error); };
      });
    });
  }

  function absoluteUrl(endpoint) {
    if (/^https?:\/\//i.test(endpoint)) return endpoint;
    var base = global.location.origin;
    var path = endpoint.charAt(0) === '/' ? endpoint : '/' + endpoint;
    return base + path;
  }

  function sendOne(rec) {
    var url = absoluteUrl(rec.endpoint);
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrf(),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(rec.payload_json),
    });
  }

  function processOutboxRecord(rec) {
    return sendOne(rec).then(function (resp) {
      var st = resp.status;
      if (st >= 200 && st < 300) {
        return deleteRecord(rec.id);
      }
      if (st >= 500 || st === 408) {
        rec.intentos = (rec.intentos || 0) + 1;
        return putRecord(rec);
      }
      if (st >= 400 && st < 500) {
        if (st === 401 || st === 403 || st === 429) {
          rec.intentos = (rec.intentos || 0) + 1;
          return putRecord(rec);
        }
        rec.estado = 'DEAD_LETTER';
        rec.dead_letter_at = Date.now();
        rec.dead_letter_http = st;
        return resp.text().then(function (t) {
          rec.dead_letter_body = (t || '').slice(0, 2000);
          return putRecord(rec);
        }, function () { return putRecord(rec); });
      }
      rec.intentos = (rec.intentos || 0) + 1;
      return putRecord(rec);
    }).catch(function () {
      rec.intentos = (rec.intentos || 0) + 1;
      return putRecord(rec);
    });
  }

  function drainOutbox() {
    return listPending().then(function (pending) {
      var chain = Promise.resolve();
      pending.forEach(function (rec) {
        chain = chain.then(function () { return processOutboxRecord(rec); });
      });
      return chain;
    }).then(function () {
      notifyCountUpdate();
      applyOnlineOnlyControls();
    });
  }

  var drainTimer = null;
  function drainOutboxSoon() {
    if (drainTimer) clearTimeout(drainTimer);
    drainTimer = setTimeout(function () {
      drainTimer = null;
      drainOutbox().catch(function (e) {
        if (global.console && console.warn) console.warn('[PRISLAB offline]', e);
      });
    }, 300);
  }

  function registerBackgroundSync() {
    if (!('serviceWorker' in navigator)) return Promise.resolve();
    return navigator.serviceWorker.ready.then(function (reg) {
      if (reg.sync && reg.sync.register) return reg.sync.register(SYNC_TAG);
    }).catch(function () {});
  }

  function pendingCount() {
    return listPending().then(function (p) { return p.length; });
  }

  function notifyCountUpdate() {
    pendingCount().then(function (n) {
      var wrap = document.getElementById('prislab-outbox-badge-wrap');
      var numEl = document.getElementById('prislab-outbox-num');
      if (!wrap || !numEl) return;
      numEl.textContent = String(n);
      wrap.classList.toggle('d-none', n === 0);
      wrap.setAttribute('title', n > 0 ? (n + ' pendiente(s) de sincronizar') : '');
      try {
        global.dispatchEvent(new CustomEvent('prislab:outbox-count', { detail: { count: n } }));
      } catch (e) { /* ignore */ }
    });
  }

  function setAnchorOffline(el, offline) {
    if (offline) {
      if (el.dataset.prislabHref == null) el.dataset.prislabHref = el.getAttribute('href') || '';
      el.setAttribute('href', '#');
      el.classList.add('disabled', 'prislab-offline-blocked');
      el.style.pointerEvents = 'none';
      el.setAttribute('aria-disabled', 'true');
      el.setAttribute('title', 'Requiere conexión al servidor central (no disponible en modo offline).');
    } else {
      var h = el.dataset.prislabHref;
      if (h) el.setAttribute('href', h);
      else el.removeAttribute('href');
      delete el.dataset.prislabHref;
      el.classList.remove('disabled', 'prislab-offline-blocked');
      el.style.pointerEvents = '';
      el.removeAttribute('aria-disabled');
      var ot = el.dataset.prislabSavedTitle;
      if (ot !== undefined) {
        if (ot) el.setAttribute('title', ot);
        else el.removeAttribute('title');
        delete el.dataset.prislabSavedTitle;
      } else {
        el.removeAttribute('title');
      }
    }
  }

  function applyOnlineOnlyControls() {
    var online = navigator.onLine;
    document.querySelectorAll('[data-prislab-requires-online]').forEach(function (el) {
      var tag = (el.tagName || '').toLowerCase();
      if (tag === 'a') {
        if (!online) {
          if (el.dataset.prislabSavedTitle == null) {
            el.dataset.prislabSavedTitle = el.getAttribute('title') || '';
          }
          setAnchorOffline(el, true);
        } else {
          setAnchorOffline(el, false);
        }
        return;
      }
      if (!online) {
        if (el.dataset.prislabSavedDisabled == null) {
          el.dataset.prislabSavedDisabled = el.disabled ? '1' : '0';
        }
        el.disabled = true;
        el.setAttribute('aria-disabled', 'true');
        if (el.dataset.prislabSavedTitle == null) {
          el.dataset.prislabSavedTitle = el.getAttribute('title') || '';
        }
        el.setAttribute('title', 'Requiere conexión al servidor central (no disponible en modo offline).');
      } else {
        if (el.dataset.prislabSavedDisabled === '0') el.disabled = false;
        else if (el.dataset.prislabSavedDisabled === '1') el.disabled = true;
        delete el.dataset.prislabSavedDisabled;
        var ot = el.dataset.prislabSavedTitle;
        if (ot !== undefined) {
          if (ot) el.setAttribute('title', ot);
          else el.removeAttribute('title');
          delete el.dataset.prislabSavedTitle;
        }
        el.removeAttribute('aria-disabled');
      }
    });
  }

  function init() {
    global.addEventListener('online', function () {
      applyOnlineOnlyControls();
      drainOutboxSoon();
      registerBackgroundSync();
    });
    global.addEventListener('offline', function () {
      applyOnlineOnlyControls();
    });
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', function (ev) {
        if (ev.data && ev.data.type === 'PRISLAB_DRAIN_OUTBOX') drainOutboxSoon();
      });
    }
    applyOnlineOnlyControls();
    notifyCountUpdate();
    if (navigator.onLine) drainOutboxSoon();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  global.PrislabOfflineSync = {
    enqueue: enqueue,
    drain: drainOutbox,
    pendingCount: pendingCount,
    refreshBadge: notifyCountUpdate,
  };
})(typeof window !== 'undefined' ? window : this);
