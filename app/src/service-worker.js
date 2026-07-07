/**
 * ◑ MiMi Nox – Service Worker
 * 
 * Strategie:
 *   - Static Assets (CSS, JS, fonts, SVG): Cache-First (schnell, offline-fähig)
 *   - API / Images / Audio: Network-Only (immer frisch, kein alter Cache)
 *   - Alles andere: Network-First mit Cache-Fallback
 */

const CACHE_VERSION = 'v24'; // refresh restricted-browser and file-protocol frontend assets
const CACHE_NAME = `mimi-nox-${CACHE_VERSION}`;

// Statische Assets die pre-gecached werden
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/mobile.html',
  '/style.css',
  '/main.js',
  '/artifact.js',
  '/i18n.js',
  '/manifest.json',
  '/forest.svg',
  '/lib/marked.min.js',
  '/lib/purify.min.js',
  '/icon-192.png',
  '/icon-512.png',
  '/favicon.ico',
];

// Diese URL-Präfixe werden NIEMALS gecached (immer Live-Daten)
const NETWORK_ONLY_PATTERNS = [
  '/api/',
  '/images/',
  '/audio/',
];

// Release-critical files prefer the network, then fall back to cache offline.
const NETWORK_FIRST_ASSETS = [
  '/',
  '/index.html',
  '/main.js',
  '/i18n.js',
  '/style.css',
  '/service-worker.js',
];

// ── Install: Pre-cache statische Assets ────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting()) // Sofort aktiv werden
  );
});

// ── Activate: Alte Caches löschen ──────────────────────────────────────────
self.addEventListener('activate', (event) => {
  let deletedOldCache = false;
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.startsWith('mimi-nox-') && key !== CACHE_NAME)
          .map((key) => caches.delete(key).then((deleted) => {
            deletedOldCache = deletedOldCache || deleted;
            return deleted;
          }))
      ))
      .then(() => self.clients.claim())
      .then(() => self.clients.matchAll({ type: 'window', includeUncontrolled: true }))
      .then((clients) => {
        if (!deletedOldCache) return undefined;
        return Promise.all(
          clients.map((client) => {
            if ('navigate' in client && client.url) {
              return client.navigate(client.url);
            }
            return undefined;
          })
        );
      })
  );
});

// ── Fetch: Routing-Strategie ────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Network-Only: API, dynamische Daten — niemals cachen
  const isNetworkOnly = NETWORK_ONLY_PATTERNS.some((p) => url.pathname.startsWith(p));
  if (isNetworkOnly) {
    event.respondWith(
      fetch(event.request).catch(() =>
        new Response(
          JSON.stringify({ error: 'offline', message: 'Server nicht erreichbar' }),
          { status: 503, headers: { 'Content-Type': 'application/json' } }
        )
      )
    );
    return;
  }

  const isDocument = event.request.mode === 'navigate' || event.request.destination === 'document';
  const isNetworkFirstAsset = NETWORK_FIRST_ASSETS.includes(url.pathname);
  if (isDocument || isNetworkFirstAsset) {
    event.respondWith(
      fetch(event.request).then((response) => {
        if (response && response.status === 200 && event.request.method === 'GET') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      }).catch(() =>
        caches.match(event.request)
          .then((cached) => cached || caches.match('/index.html'))
          .then((fallback) => fallback || new Response('', { status: 503 }))
      )
    );
    return;
  }

  // Cache-First: Statische Assets
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;

      // Nicht im Cache → aus dem Netzwerk holen und cachen
      return fetch(event.request).then((response) => {
        if (response && response.status === 200 && event.request.method === 'GET') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => {
        // Offline-Fallback für HTML-Anfragen
        if (event.request.destination === 'document') {
          return caches.match('/index.html');
        }
        return new Response('', { status: 503 });
      });
    })
  );
});

// ── Message Handler: Cache invalidieren wenn nötig ─────────────────────────
self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
});
