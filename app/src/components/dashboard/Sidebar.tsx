'use client'

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import {
  Sparkles, Plus, X, Trash2, Settings, Search,
  ChevronRight,
} from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { format, isToday, isYesterday, isThisWeek, isThisMonth } from 'date-fns'
import { de } from 'date-fns/locale'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  onOpenSettings: () => void
}

// Date group type
interface DateGroup {
  label: string
  sessions: Session[]
}

// Session type matching the store
interface Session {
  id: string
  title: string
  messages: Array<{ id: string; role: string; content: string }>
  createdAt: number
}

// Simple date groupings
function groupSessionsByDate(sessions: Session[], t: (key: string) => string): DateGroup[] {
  const groups: DateGroup[] = []

  const groupLabel = (date: Date): string => {
    if (isToday(date)) return t('sidebar.today')
    if (isYesterday(date)) return t('sidebar.yesterday')
    if (isThisWeek(date, { weekStartsOn: 1 })) return t('sidebar.thisWeek')
    if (isThisMonth(date)) return t('sidebar.thisMonth')
    return format(date, 'MMMM yyyy', { locale: de })
  }

  // Sort by createdAt descending
  const sorted = [...sessions].sort((a, b) => b.createdAt - a.createdAt)

  let currentLabel = ''
  let currentSessions: Session[] = []

  for (const session of sorted) {
    const label = groupLabel(new Date(session.createdAt))
    if (label !== currentLabel) {
      if (currentSessions.length > 0) {
        groups.push({ label: currentLabel, sessions: currentSessions })
      }
      currentLabel = label
      currentSessions = [session]
    } else {
      currentSessions.push(session)
    }
  }
  if (currentSessions.length > 0) {
    groups.push({ label: currentLabel, sessions: currentSessions })
  }

  return groups
}

export default function Sidebar({ isOpen, onClose, onOpenSettings }: SidebarProps) {
  const { t } = useTranslation()
  const { sessions, activeSessionId, setActiveSession, createSession, deleteSession } = useChatStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [searchFocused, setSearchFocused] = useState(false)
  // Desktop (lg+ ≥1024px) → ständige Spalte; darunter → Slide-Drawer.
  const isDesktop = useMediaQuery('(min-width: 1024px)')

  const filteredSessions = sessions
    .filter(s => !searchQuery || s.title.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => b.createdAt - a.createdAt)

  const dateGroups = groupSessionsByDate(filteredSessions, t)

  const handleDelete = (id: string) => {
    deleteSession(id)
    setDeleteConfirm(null)
  }

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar — Desktop (lg+): ständige Spalte ohne Slide-Animation
          (framer-motion setzt inline transform, der CSS-Klassen übersteuert —
          bei !isOpen würde er die Sidebar deshalb aus dem Viewport schieben).
          Mobile: Drawer mit Spring-Transition + Backdrop. */}
      <motion.aside
        initial={isDesktop ? false : { x: -320 }}
        animate={isDesktop ? { x: 0 } : { x: isOpen ? 0 : -320 }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className={`left-0 top-0 h-full z-50 w-72 liquid-glass-strong border-r border-green-500/10 flex flex-col ${
          isDesktop ? 'relative' : 'fixed'
        }`}
        aria-label={t('a11y.sidebar')}
        data-testid="chat-sidebar"
      >
        {/* Header */}
        <div className="p-4 border-b border-white/5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg liquid-glass flex items-center justify-center">
                <Sparkles className="h-3.5 w-3.5 text-green-400" />
              </div>
              <h2 className="text-sm font-semibold text-white/90">{t('nav.appName')}</h2>
            </div>
            <button onClick={onClose} className="lg:hidden p-1.5 rounded-lg hover:bg-white/5 text-white/40 hover:text-white transition-colors">
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* New Session */}
          <button
            onClick={() => createSession()}
            data-testid="new-session"
            className="w-full bg-green-500/10 hover:bg-green-500/15 border border-green-400/10 hover:border-green-400/20 text-green-400 rounded-xl h-9 text-xs font-medium transition-all duration-200 flex items-center justify-center gap-1.5"
            aria-label={t('sidebar.newChat')}
          >
            <Plus className="h-3.5 w-3.5" />
            {t('sidebar.newChat')}
          </button>
        </div>

        {/* Search */}
        <div className="px-3 py-2.5">
          <div className={`relative flex items-center rounded-lg border transition-all duration-200 ${
            searchFocused ? 'border-green-400/20 bg-white/[0.03]' : 'border-white/5 bg-black/20'
          }`}>
            <Search className="h-3.5 w-3.5 text-white/20 absolute left-2.5" />
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
              placeholder={t('sidebar.searchPlaceholder')}
              className="w-full bg-transparent pl-8 pr-2.5 py-1.5 text-xs text-white/70 placeholder:text-white/20 outline-none"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 text-white/20 hover:text-white/40"
                aria-label={t('a11y.close')}
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>

        {/* Session List — Date Grouped */}
        <div className="flex-1 overflow-y-auto px-3 pb-2" data-testid="sessions-view">
          {dateGroups.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-10 h-10 rounded-xl liquid-glass flex items-center justify-center mb-3">
                <Sparkles className="h-5 w-5 text-white/20" />
              </div>
              <p className="text-xs text-white/30">{t('sidebar.emptyTitle')}</p>
              <p className="text-[10px] text-white/20 mt-1">{t('sidebar.emptyDesc')}</p>
            </div>
          ) : (
            <div className="space-y-4">
              {dateGroups.map((group) => (
                <div key={group.label}>
                  {/* Date Group Header */}
                  <button
                    className="flex items-center gap-1.5 w-full py-1.5 px-1 text-[10px] font-medium text-white/25 uppercase tracking-wider hover:text-white/40 transition-colors"
                  >
                    <ChevronRight className="h-3 w-3" />
                    {group.label}
                    <span className="text-[9px] bg-white/[0.05] px-1.5 py-0.5 rounded-full">{group.sessions.length}</span>
                  </button>

                  {/* Sessions */}
                  <div className="space-y-0.5 mt-0.5 ml-1.5">
                    {group.sessions.map((session) => (
                      <div key={session.id} className="group relative">
                        <button
                          onClick={() => {
                            setActiveSession(session.id)
                            if (window.innerWidth < 1024) onClose()
                          }}
                          className={`w-full text-left rounded-lg px-2.5 py-2 transition-all duration-150 ${
                            activeSessionId === session.id
                              ? 'bg-green-500/10 border border-green-400/15'
                              : 'hover:bg-white/[0.03]'
                          }`}
                        >
                          <p className={`text-xs truncate ${
                            activeSessionId === session.id ? 'text-white/90 font-medium' : 'text-white/50'
                          }`}>
                            {session.title}
                          </p>
                          <p className="text-[10px] text-white/20 mt-0.5">
                            {session.messages.length} {t('sidebar.messages')}
                          </p>
                        </button>

                        {/* Delete button (hover) */}
                        {deleteConfirm === session.id ? (
                          <div className="absolute right-1 top-1/2 -translate-y-1/2 flex items-center gap-0.5 liquid-glass-strong rounded-lg p-0.5 z-10">
                            <button
                              onClick={() => handleDelete(session.id)}
                              className="bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded px-1.5 py-0.5 text-[10px] font-medium transition-colors"
                            >
                              {t('sidebar.deleteYes')}
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(null)}
                              className="text-white/30 hover:text-white/50 rounded px-1 py-0.5 text-[10px] transition-colors"
                            >
                              {t('sidebar.deleteNo')}
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setDeleteConfirm(session.id)
                            }}
                            className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-white/5 text-white/20 hover:text-red-400 transition-all"
                            aria-label={t('sidebar.deleteConfirm')}
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-white/5">
          <button
            onClick={onOpenSettings}
            className="w-full liquid-glass rounded-xl p-2.5 flex items-center justify-center gap-2 text-white/30 hover:text-green-400 hover:bg-green-500/5 transition-all"
            aria-label={t('sidebar.settings')}
          >
            <Settings className="h-3.5 w-3.5" />
            <span className="text-[11px] font-medium">{t('sidebar.settings')}</span>
          </button>
          <p className="text-[10px] text-white/10 text-center mt-2">v2.0.0</p>
        </div>
      </motion.aside>
    </>
  )
}