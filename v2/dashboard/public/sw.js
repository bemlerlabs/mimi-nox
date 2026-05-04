/**
 * ◑ MiMiNox v2 — Service Worker
 * public/sw.js
 *
 * Offline-First: MiMiNox funktioniert ohne Internet.
 * Das ist kein Nice-to-have — im Funkloch, im Berg, im Keller
 * MUSS der Assistent antworten können.
 *
 * Strategie:
 *   App Shell (HTML/CSS/JS):  Cache-First  → immer sofort da
 *   API (/api/*):             Network-First → versucht Live, fällt auf Cache zurück
 *   Alles andere:             Stale-While-Revalidate
 */

const CACHE_VERSION  = 'miminox-v2-r2'; // r2: + map tiles
const CACHE_SHELL    = `${CACHE_VERSION}-shell`;
const CACHE_DATA     = `${CACHE_VERSION}-data`;
const CACHE_TILES    = `${CACHE_VERSION}-tiles`; // OSM-Kacheln — Cache-First

// Tile-Hosts die gecacht werden (OSM + OpenTopoMap)
const TILE_HOSTS = [
  'tile.openstreetmap.org',
  'a.tile.openstreetmap.org',
  'b.tile.openstreetmap.org',
  'c.tile.openstreetmap.org',
  'opentopomap.org',
  'a.tile.opentopomap.org',
  'b.tile.opentopomap.org',
  'c.tile.opentopomap.org',
  // Leaflet-Icons via CDN
  'cdnjs.cloudflare.com',
];

// App Shell: muss offline verfügbar sein
const PRECACHE = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.svg',
];

// Diese Pfade NIEMALS cachen — immer live
const NETWORK_ONLY = [
  '/api/vision',    // Foto-Analyse: zu groß für Cache
  '/api/tasks',     // Neue Aufgaben: immer live
];

// ── Install ────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_SHELL)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: Alte Cache-Versionen löschen ─────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((k) => k.startsWith('miminox-') && k !== CACHE_SHELL && k !== CACHE_DATA && k !== CACHE_TILES)
          .map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// ── Fetch: Routing ─────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Nur GET-Requests cachen
  if (request.method !== 'GET') return;

  // ── Karten-Tiles (cross-origin): Cache-First ───────────────────
  // Tiles werden beim Online-Sein gecacht → offline aus Cache serviert
  if (TILE_HOSTS.some((h) => url.hostname === h || url.hostname.endsWith('.' + h))) {
    event.respondWith(
      caches.open(CACHE_TILES).then(async (cache) => {
        const cached = await cache.match(request);
        if (cached) return cached;              // Offline: aus Cache
        try {
          const response = await fetch(request);
          if (response.ok) cache.put(request, response.clone());
          return response;
        } catch {
          return new Response('', { status: 503 }); // Kein Tile → leer
        }
      })
    );
    return;
  }

  // Andere Origins ignorieren (nicht Tile-Hosts)
  if (url.origin !== self.location.origin) return;

  // Network-Only: Mutation-Endpunkte
  if (NETWORK_ONLY.some((p) => url.pathname.startsWith(p))) {
    event.respondWith(
      fetch(request).catch(() =>
        new Response(
          JSON.stringify({ error: 'offline', message: 'Nicht erreichbar — du bist offline.' }),
          { status: 503, headers: { 'Content-Type': 'application/json' } }
        )
      )
    );
    return;
  }

  // API: Network-First mit Cache-Fallback (Chat-History offline lesbar)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_DATA).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // App Shell + Assets: Cache-First
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_SHELL).then((cache) => cache.put(request, clone));
        }
        return response;
      }).catch(() => {
        // Offline-Fallback: immer die App zurückgeben
        if (request.destination === 'document') {
          return caches.match('/index.html');
        }
        return new Response('', { status: 503 });
      });
    })
  );
});

// ── Message: Force-Update ──────────────────────────────────────
self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') self.skipWaiting();
});
