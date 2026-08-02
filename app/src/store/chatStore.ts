import { create } from 'zustand'
import { dbGetAllSessions, dbDeleteSession, debouncedSaveSession, DbSession } from '@/lib/db'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  tool_calls?: ToolCall[]
}

export interface ToolCall {
  id: string
  name: string
  args: Record<string, unknown>
  result?: string
  status: 'pending' | 'approved' | 'denied' | 'completed' | 'waiting'
  description?: string
}

export interface PendingToolCall {
  id: string
  tool_name: string
  tool_args: Record<string, unknown>
  description: string
  session_id: string
}

interface Session {
  id: string
  title: string
  messages: Message[]
  createdAt: number
}

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
    messages: d.messages as Message[],
    createdAt: d.createdAt,
  }
}

interface ChatStore {
  sessions: Session[]
  activeSessionId: string | null
  isTyping: boolean
  pendingToolCall: PendingToolCall | null
  currentSession: Session | null
  setSessions: (sessions: Session[]) => void
  setActiveSession: (id: string) => void
  createSession: (title?: string) => void
  deleteSession: (id: string) => void
  addMessage: (role: 'user' | 'assistant' | 'system', content: string, toolCalls?: ToolCall[]) => void
  setTyping: (typing: boolean) => void
  setPendingToolCall: (tool: PendingToolCall | null) => void
  // IndexedDB helpers
  initFromDb: () => Promise<void>
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  isTyping: false,
  pendingToolCall: null,
  currentSession: null,

  // Load persisted sessions from IndexedDB on first mount
  initFromDb: async () => {
    try {
      const dbSessions = await dbGetAllSessions()
      if (dbSessions.length > 0) {
        const sessions = dbSessions.map(fromDbSession)
        set({ sessions, activeSessionId: sessions[0]?.id ?? null, currentSession: sessions[0] ?? null })
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
      const message: Message = {
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
}))