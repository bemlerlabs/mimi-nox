/**
 * API client for MiMi Nox — talks to the local backend.
 *
 * Default: same-origin. Die PWA wird vom API-Server selbst ausgeliefert
 * (Prod/One-Command-Install) und in Dev über den Vite-Proxy (5173 → 8765).
 * VITE_API_URL überschreibt für externe Setups (z. B. fester ferner Port).
 */
const BASE_URL = import.meta.env.VITE_API_URL || ''

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

/**
 * Active-Engine-Status vom Backend (Single Source of Truth).
 * Spiegelt server/routes/health.py::HealthResponse wider.
 */
export interface HealthInfo {
  status: string
  version?: string
  ollama: boolean
  models: string[]
  active_tier: string
  active_model: string
  dgx_online: boolean
  active_provider: string
  offline_capable: boolean
  requires_internet: boolean
  model_installed?: boolean
  detail?: string
}

export function healthCheck(): Promise<HealthInfo> {
  return request<HealthInfo>('/api/health')
}

// ── Setup (First-Run-Engine-Auswahl) ───────────────────────────────────────

/**
 * Setup-Status: ist schon eine Engine persistiert (engine.json)?
 * configured=false → die PWA zeigt die Engine-Auswahl (SetupPage).
 */
export interface SetupStatus {
  configured: boolean
  provider: string
  model: string | null
  url: string | null
  reachable: boolean
  available_models: string[]
}

export interface ProviderProbeResponse {
  reachable: boolean
  models: string[]
  detail: string
}

export function getSetupStatus(): Promise<SetupStatus> {
  return request<SetupStatus>('/api/setup/status')
}

/**
 * Endpunkt prüfen + verfügbare Modelle auflisten (Ollama: /api/tags,
 * OpenAI-kompatibel: /v1/models). Kein Persist — reine Erkennung.
 */
export function probeProvider(
  provider: 'local_ollama' | 'custom_ollama' | 'openai_compatible',
  baseUrl?: string,
  apiKey?: string
): Promise<ProviderProbeResponse> {
  return request<ProviderProbeResponse>('/api/model/providers/probe', {
    method: 'POST',
    body: JSON.stringify({
      provider,
      base_url: baseUrl || null,
      api_key: apiKey || null,
    }),
  })
}

export function resetSetup(): Promise<{ configured: boolean }> {
  return request<{ configured: boolean }>('/api/setup/reset', { method: 'POST' })
}

// ── Scheduler (P2-8) ───────────────────────────────────────────────────────

export interface ScheduleJob {
  id: string
  task: string
  cron: string
  next_run?: string
  enabled?: boolean
}

export interface ScheduleResult {
  id: string
  job_id: string
  status: string
  output?: string
  ran_at?: string
}

export function listSchedules(): Promise<{ jobs: ScheduleJob[] }> {
  return request<{ jobs: ScheduleJob[] }>('/api/schedule')
}

export function getScheduleResults(limit = 20): Promise<{ results: ScheduleResult[] }> {
  return request<{ results: ScheduleResult[] }>(`/api/schedule/results?limit=${limit}`)
}

export async function createSchedule(task: string, cron: string): Promise<{ job_id: string; message: string }> {
  return request<{ job_id: string; message: string }>('/api/schedule', {
    method: 'POST',
    body: JSON.stringify({ task, cron }),
  })
}

export function deleteSchedule(jobId: string): Promise<{ status: string; job_id: string }> {
  return request<{ status: string; job_id: string }>(`/api/schedule/${jobId}`, {
    method: 'DELETE',
  })
}
