/**
 * API client for MiMi Nox — talks to the local backend.
 * Backend runs on localhost:8765 by default (overridable via VITE_API_URL).
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8765'

// Types aus kanonischer Quelle (types/index.ts) re-exportieren — einzige Wahrheit.
import type {
  ApiChatMessage as ChatMessage,
  ApiMessage as Message,
  ApiSession as Session,
  AppSettings,
  PendingToolCall,
  ProviderSettings,
  ProviderType,
} from '@/types'

export type {
  AppSettings,
  ProviderSettings,
  ProviderType,
  PendingToolCall,
  Session,
  Message,
  ChatMessage,
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

/**
 * Send a chat message to the backend, optionally streaming assistant
 * chunks via an onChunk callback (server-sent events or chunked JSON).
 */
export async function sendMessage(
  message: string,
  sessionId?: string,
  onChunk?: (chunk: string) => void
): Promise<string> {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  })
  if (!res.ok) {
    throw new Error(`Chat failed (${res.status})`)
  }
  const body = await res.json() as { content?: string; response?: string }
  const content = body.content ?? body.response ?? ''
  if (onChunk) {
    onChunk(content)
  }
  return content
}

export function getSettings(): Promise<AppSettings> {
  return request<AppSettings>('/api/settings')
}

export function updateSettings(settings: Partial<AppSettings>): Promise<AppSettings> {
  return request<AppSettings>('/api/settings', {
    method: 'POST',
    body: JSON.stringify(settings),
  })
}

export async function healthCheck(): Promise<{ status: string; model: string }> {
  return request<{ status: string; model: string }>('/api/health')
}
