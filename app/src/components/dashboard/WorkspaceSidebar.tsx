'use client'

import { useState } from 'react'
import {
  MessageSquare, FileText, MessagesSquare, Cpu, Plus, Pin, PinOff,
  FolderPlus, Settings, X,
} from 'lucide-react'
import type { Session } from '@/types'

export interface SidebarTab {
  id: 'sessions' | 'artifacts' | 'messenger' | 'capability'
  name: string
  icon: typeof MessageSquare
}

// 4 Bereiche — eigene MiMi-Nox-Navigation (keine Hermes-Kopie)
export const SIDEBAR_TABS: SidebarTab[] = [
  { id: 'sessions', name: 'Sessions', icon: MessageSquare },
  { id: 'artifacts', name: 'Artefakte', icon: FileText },
  { id: 'messenger', name: 'Messenger', icon: MessagesSquare },
  { id: 'capability', name: 'Capability', icon: Cpu },
]

interface WorkspaceSidebarProps {
  /** Kompatibilität mit bestehender Sidebar-Integration */
  isOpen?: boolean
  onClose?: () => void
  onOpenSettings?: () => void
  activeTab?: SidebarTab['id']
  sessions?: Session[]
  onTogglePin?: (id: string) => void
}

export function WorkspaceSidebar({
  isOpen = true,
  onClose,
  onOpenSettings,
  activeTab: activeTabProp = 'sessions',
  sessions = [],
  onTogglePin,
}: WorkspaceSidebarProps) {
  const [activeTab, setActiveTab] = useState<SidebarTab['id']>(activeTabProp)

  if (!isOpen) return null

  // Pinned Sessions zuerst, dann nach createdAt desc
  const sorted = [...sessions].sort((a, b) => {
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1
    return b.createdAt - a.createdAt
  })

  return (
    <div className="flex h-full w-full flex-col">
      {/* Header mit Close + New Session — oben links */}
      <div className="flex items-center gap-2 px-2 pt-2">
        {onClose && (
          <button
            data-testid="sidebar-close"
            onClick={onClose}
            className="rounded p-1 text-white/40 hover:bg-white/10 hover:text-white"
            aria-label="Schließen"
          >
            <X className="h-4 w-4" />
          </button>
        )}
        <button
          data-testid="new-session"
          className="flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-sm text-white/90 hover:bg-white/15"
        >
          <Plus className="h-4 w-4" />
          New Session
        </button>
      </div>

      {/* 4 Bereiche */}
      <nav className="px-2">
        {SIDEBAR_TABS.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              data-testid={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm ${
                activeTab === tab.id
                  ? 'bg-white/10 text-white'
                  : 'text-white/60 hover:bg-white/5 hover:text-white'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.name}
            </button>
          )
        })}
      </nav>

      {/* Aktiver Bereich */}
      <div className="flex-1 overflow-auto px-2 pt-2">
        {activeTab === 'sessions' && (
          <div data-testid="sessions-view" className="space-y-1">
            {sorted.length === 0 && (
              <p className="text-xs text-white/40">Keine Sessions</p>
            )}
            {sorted.map((s) => (
              <div
                key={s.id}
                data-testid="session-item"
                className="flex items-center justify-between rounded bg-white/5 px-2 py-1.5 text-sm text-white/80"
              >
                <span className="truncate">{s.title}</span>
                <button
                  data-testid="pin-btn"
                  onClick={() => onTogglePin?.(s.id)}
                  className="ml-2 text-white/40 hover:text-yellow-300"
                  title={s.pinned ? 'Unpin' : 'Pinnen'}
                >
                  {s.pinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
                </button>
              </div>
            ))}
          </div>
        )}
        {activeTab === 'artifacts' && (
          <div data-testid="artifacts-view">
            <p className="text-xs text-white/50">Artefakte aus dem aktiven Thread</p>
          </div>
        )}
        {activeTab === 'messenger' && (
          <div data-testid="messenger-view">
            <p className="text-xs text-white/50">Plattform-Status (optional)</p>
          </div>
        )}
        {activeTab === 'capability' && (
          <div data-testid="capability-view">
            <p className="text-xs text-white/50">Skills & Agent-Fähigkeiten</p>
          </div>
        )}
      </div>

      {/* Projekt anlegen + Settings — unten */}
      <div className="m-2 space-y-1">
        <button
          data-testid="new-project"
          className="flex w-full items-center gap-2 rounded-md border border-white/10 px-3 py-2 text-sm text-white/70 hover:bg-white/5"
        >
          <FolderPlus className="h-4 w-4" />
          Projekt anlegen
        </button>
        {onOpenSettings && (
          <button
            data-testid="sidebar-settings"
            onClick={onOpenSettings}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-white/50 hover:bg-white/5 hover:text-white/80"
          >
            <Settings className="h-4 w-4" />
            Einstellungen
          </button>
        )}
      </div>
    </div>
  )
}
