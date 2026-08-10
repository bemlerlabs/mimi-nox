/**
 * MiMi Nox — Canonical shared types (EINZIGE WAHRHEIT)
 *
 * Alle Modul-Types (api.ts, chatStore.ts, websocket.ts, db.ts) werden von
 * hier importiert und re-exportiert, damit bestehende Import-Pfade stabil
 * bleiben. Duplikate in den Einzelmodulen sind hier zentralisiert.
 */

export type MessageRole = 'user' | 'assistant' | 'system'

// ── Remote / REST-API-Shapes ───────────────────────────────────────────────

/** Session, wie die REST-API sie zurückgibt */
export interface ApiSession {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

/** Nachricht, wie die REST-API sie zurückgibt */
export interface ApiMessage {
  id: string
  role: MessageRole
  content: string
  tool_calls?: unknown[]
}

/** Chat-Payload für einen REST-Request */
export interface ApiChatMessage {
  role: MessageRole
  content: string
}

// ── Lokale Chat/Store-Shapes ───────────────────────────────────────────────

/** Ein Tool-Call im Chat-Modell (lokal, im Store persistiert) */
export interface ToolCall {
  id: string
  name: string
  args: Record<string, unknown>
  result?: string
  status: 'pending' | 'approved' | 'denied' | 'completed' | 'waiting'
  description?: string
}

/** Pending-Tool-Call, bis der User approve/deny (lokal + WS-Payload) */
export interface PendingToolCall {
  id: string
  tool_name: string
  tool_args: Record<string, unknown>
  description: string
  session_id: string
}

/** Chat-Nachricht im Store (lokal, persistiert) */
export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  timestamp: number
  tool_calls?: ToolCall[]
}

/** Session im Store (lokal, IndexedDB) */
export interface Session {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: number
  /** Angepinnte Session — wird oben fixiert (MiMi-Nox-Feature) */
  pinned?: boolean
}

// ── Provider / Settings ────────────────────────────────────────────────────

export type ProviderType = 'local_ollama' | 'custom_ollama' | 'openai_compatible'

export interface ProviderSettings {
  type: ProviderType
  endpoint?: string
  api_key?: string
  model: string
}

export interface AppSettings {
  provider: ProviderSettings
  memory_enabled: boolean
  language: string
  theme: string
}

// ── WebSocket ──────────────────────────────────────────────────────────────

export interface WSMessage {
  type: 'chat' | 'tool_call' | 'tool_result' | 'error' | 'status'
  content?: string
  tool_name?: string
  tool_args?: Record<string, unknown>
  session_id?: string
  timestamp?: number
}

export interface ToolApprovalRequest {
  tool_name: string
  tool_args: Record<string, unknown>
  description: string
  session_id: string
}

// ── IndexedDB ──────────────────────────────────────────────────────────────

export interface DbSession {
  id: string
  title: string
  messages: unknown[]
  createdAt: number
  updatedAt: number
}
