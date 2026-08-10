import { create } from 'zustand'
import { dbGetAllSessions, dbDeleteSession, debouncedSaveSession, dbGetCheckpoints, dbSaveCheckpoints } from '@/lib/db'
import { createCheckpoint, rollbackToCheckpoint, deleteCheckpoint, type ChatCheckpoint } from '@/lib/checkpoints'
import type {
  ChatMessage,
  DbSession,
  PendingToolCall,
  Session,
  ToolCall,
} from '@/types'

export type { ToolCall, PendingToolCall, ChatMessage, Session }

function toDbSession(s: Session): DbSession {
  return {
    id: s.id,
    title: s.title,
    messages: s.messages,
    createdAt: s.createdAt,
    updatedAt: Date.now(),
  }
}

function fromDbSession(d: DbSession): Session {
  return {
    id: d.id,
    title: d.title,
    messages: d.messages as ChatMessage[],
    createdAt: d.createdAt,
  }
}

interface ChatStore {
  sessions: Session[]
  activeSessionId: string | null
  isTyping: boolean
  pendingToolCall: PendingToolCall | null
  currentSession: Session | null
  checkpoints: Record<string, ChatCheckpoint[]>
  setSessions: (sessions: Session[]) => void
  setActiveSession: (id: string) => void
  createSession: (title?: string) => void
  deleteSession: (id: string) => void
  addMessage: (role: 'user' | 'assistant' | 'system', content: string, toolCalls?: ToolCall[]) => void
  setTyping: (typing: boolean) => void
  setPendingToolCall: (tool: PendingToolCall | null) => void
  // Checkpoints & Rollback (P2-7)
  createCheckpoint: (label?: string) => void
  rollbackToCheckpoint: (id: string) => void
  deleteCheckpoint: (id: string) => void
  // IndexedDB helpers
  initFromDb: () => Promise<void>
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  isTyping: false,
  pendingToolCall: null,
  currentSession: null,
  checkpoints: {},

  // Load persisted sessions from IndexedDB on first mount
  initFromDb: async () => {
    try {
      const dbSessions = await dbGetAllSessions()
      if (dbSessions.length > 0) {
        const sessions = dbSessions.map(fromDbSession)
        const first = sessions[0]!
        set({ sessions, activeSessionId: first.id, currentSession: first })
        // Lade Checkpoints der aktiven Session
        const cps = await dbGetCheckpoints(first.id)
        if (cps.length > 0) {
          set((state) => ({ checkpoints: { ...state.checkpoints, [first.id]: cps } }))
        }
      }
    } catch (err) {
      console.warn('[ChatStore] Failed to load sessions from IndexedDB:', err)
    }
  },

  setSessions: (sessions) => {
    set({ sessions })
    // Persist all sessions to IndexedDB
    for (const s of sessions) {
      debouncedSaveSession(toDbSession(s))
    }
  },
  setActiveSession: (id) => {
    const session = get().sessions.find((s) => s.id === id)
    set({ activeSessionId: id, currentSession: session ?? null })
  },
  createSession: (title) => {
    const newSession: Session = {
      id: crypto.randomUUID(),
      title: title || 'Neue Sitzung',
      messages: [],
      createdAt: Date.now(),
    }
    set((state) => ({
      sessions: [newSession, ...state.sessions],
      activeSessionId: newSession.id,
      currentSession: newSession,
    }))
    // Persist new session to IndexedDB
    debouncedSaveSession(toDbSession(newSession))
  },
  deleteSession: (id) => {
    set((state) => {
      const updated = state.sessions.filter((s) => s.id !== id)
      return {
        sessions: updated,
        activeSessionId: state.activeSessionId === id ? null : state.activeSessionId,
        currentSession: state.currentSession?.id === id ? null : state.currentSession,
      }
    })
    // Delete from IndexedDB
    dbDeleteSession(id)
  },
  addMessage: (role, content, toolCalls) => {
    set((state) => {
      if (!state.activeSessionId) return state
      const message: ChatMessage = {
        id: crypto.randomUUID(),
        role,
        content,
        timestamp: Date.now(),
        tool_calls: toolCalls,
      }
      const sessions = state.sessions.map((s) =>
        s.id === state.activeSessionId
          ? { ...s, messages: [...s.messages, message] }
          : s,
      )
      const currentSession = sessions.find((s) => s.id === state.activeSessionId)
      return { sessions, currentSession }
    })
    // Persist updated session to IndexedDB
    const state = get()
    if (state.activeSessionId) {
      const updated = state.sessions.find((s) => s.id === state.activeSessionId)
      if (updated) {
        debouncedSaveSession(toDbSession(updated))
      }
    }
  },
  setTyping: (typing) => set({ isTyping: typing }),
  setPendingToolCall: (tool) => set({ pendingToolCall: tool }),

  // ── Checkpoints & Rollback (P2-7) ────────────────────────────────────────
  createCheckpoint: (label) => {
    const state = get()
    const sid = state.activeSessionId
    const session = state.currentSession
    if (!sid || !session) return
    const cp = createCheckpoint(session.messages, label)
    const updated = [...(state.checkpoints[sid] ?? []), cp]
    set((s) => ({ checkpoints: { ...s.checkpoints, [sid]: updated } }))
    dbSaveCheckpoints(sid, updated)
  },
  rollbackToCheckpoint: (id) => {
    const state = get()
    const sid = state.activeSessionId
    if (!sid) return
    const cps = state.checkpoints[sid] ?? []
    const rolled = rollbackToCheckpoint(id, cps)
    if (!rolled) return
    set((s) => {
      const sessions = s.sessions.map((sess) =>
        sess.id === sid ? { ...sess, messages: rolled } : sess,
      )
      const currentSession = sessions.find((sess) => sess.id === sid)
      return { sessions, currentSession }
    })
    const updated = state.sessions.find((s) => s.id === sid)
    if (updated) debouncedSaveSession(toDbSession(updated))
  },
  deleteCheckpoint: (id) => {
    const state = get()
    const sid = state.activeSessionId
    if (!sid) return
    const updated = deleteCheckpoint(state.checkpoints[sid] ?? [], id)
    set((s) => ({ checkpoints: { ...s.checkpoints, [sid]: updated } }))
    dbSaveCheckpoints(sid, updated)
  },
}))