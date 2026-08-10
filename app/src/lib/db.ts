/**
 * MiMi Nox — IndexedDB session cache
 *
 * Replaces localStorage with IndexedDB for session persistence.
 * Provides autoload on init and debounced save on message changes.
 */

import type { DbSession } from '@/types'
import type { ChatCheckpoint } from '@/lib/checkpoints'

const DB_NAME = 'mimi-nox'
const DB_VERSION = 2
const STORE_NAME = 'sessions'
const CHECKPOINT_STORE = 'checkpoints'

export type { DbSession }

// ── Open DB ────────────────────────────────────────────────────────────────

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
        store.createIndex('updatedAt', 'updatedAt', { unique: false })
      }
      if (!db.objectStoreNames.contains(CHECKPOINT_STORE)) {
        db.createObjectStore(CHECKPOINT_STORE, { keyPath: 'sessionId' })
      }
    }

    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

// ── CRUD ───────────────────────────────────────────────────────────────────

export async function dbGetAllSessions(): Promise<DbSession[]> {
  try {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const store = tx.objectStore(STORE_NAME)
      const request = store.getAll()
      request.onsuccess = () => resolve(request.result as DbSession[])
      request.onerror = () => reject(request.error)
    })
  } catch {
    return []
  }
}

export async function dbGetSession(id: string): Promise<DbSession | null> {
  try {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const request = tx.objectStore(STORE_NAME).get(id)
      request.onsuccess = () => resolve(request.result ?? null)
      request.onerror = () => reject(request.error)
    })
  } catch {
    return null
  }
}

export async function dbSaveSession(session: DbSession): Promise<void> {
  try {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).put(session)
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch (err: unknown) {
    console.warn('[IndexedDB] Failed to save session:', session.id, err)
  }
}

export async function dbDeleteSession(id: string): Promise<void> {
  try {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).delete(id)
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch {
    // ignore
  }
}

export async function dbClearAll(): Promise<void> {
  try {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).clear()
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch {
    // ignore
  }
}

// ── Debounced save helper ──────────────────────────────────────────────────

let saveTimer: ReturnType<typeof setTimeout> | null = null

export function debouncedSaveSession(
  session: DbSession,
  delayMs: number = 1500,
): void {
  if (saveTimer) {
    clearTimeout(saveTimer)
  }
  saveTimer = setTimeout(() => {
    dbSaveSession(session)
    saveTimer = null
  }, delayMs)
}

// ── Checkpoints (P2-7) ─────────────────────────────────────────────────────

export async function dbGetCheckpoints(sessionId: string): Promise<ChatCheckpoint[]> {
  try {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(CHECKPOINT_STORE, 'readonly')
      const request = tx.objectStore(CHECKPOINT_STORE).get(sessionId)
      request.onsuccess = () => resolve((request.result as { items?: ChatCheckpoint[] })?.items ?? [])
      request.onerror = () => reject(request.error)
    })
  } catch {
    return []
  }
}

export async function dbSaveCheckpoints(
  sessionId: string,
  checkpoints: ChatCheckpoint[],
): Promise<void> {
  try {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(CHECKPOINT_STORE, 'readwrite')
      tx.objectStore(CHECKPOINT_STORE).put({ sessionId, items: checkpoints })
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch (err: unknown) {
    console.warn('[IndexedDB] Failed to save checkpoints:', sessionId, err)
  }
}

export async function dbDeleteCheckpoints(sessionId: string): Promise<void> {
  try {
    const db = await openDb()
    return new Promise((resolve, reject) => {
      const tx = db.transaction(CHECKPOINT_STORE, 'readwrite')
      tx.objectStore(CHECKPOINT_STORE).delete(sessionId)
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  } catch {
    // ignore
  }
}