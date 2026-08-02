
// Service Worker for MiMi Nox PWA
// Cache key is versioned so releases invalidate stale caches automatically.
const CACHE_NAME = 'mimi-nox-v2.0.0'
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  '/favicon.svg',
]

const sw = self

// Install event — cache assets
sw.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
  )
  sw.skipWaiting()
})

// Activate event — clean old caches
sw.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(cacheNames.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name)))
    )
  )
  sw.clients.claim()
})

// Fetch event — serve from cache, fallback to network
sw.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const network = fetch(event.request).then((res) => {
        if (res.status === 200) {
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, res.clone()))
        }
        return res
      })
      return cached || network
    })
  )
})

// Background sync (disabled until proper types are available)
// sw.addEventListener('sync', (event) => {
//   if (event.tag === 'sync-messages') {
//     event.waitUntil(Promise.resolve())
//   }
// })
