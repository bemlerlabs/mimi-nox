/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// ── Service Worker Types ──────────────────────────────────────────────────

interface ServiceWorkerGlobalScope extends Omit<ServiceWorkerGlobalScope, 'skipWaiting' | 'clients'> {
  skipWaiting(): void
  clients: Clients
}

interface ExtendableEvent extends Event {
  waitUntil(fn: Promise<void>): void
}

interface FetchEvent extends Event {
  request: Request
  respondWith(resp: Response | PromiseLike<Response>): void
}

interface SyncEvent extends Event {
  tag: string
  lastChance: boolean
  waitUntil(fn: Promise<void>): void
}