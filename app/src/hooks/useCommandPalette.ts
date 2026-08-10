import { useRef, useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useChatStore } from '@/store/chatStore'

export interface CommandItem {
  id: string
  label: string
  section: string
  action: () => void
  shortcut?: string
  icon?: string
}

export function useCommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { createSession } = useChatStore()

  // Keyboard shortcut: Ctrl/Cmd+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen((prev) => !prev)
      }
      if (e.key === 'Escape' && open) {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open])

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50)
    } else {
      setQuery('')
    }
  }, [open])

  const commands: CommandItem[] = [
    {
      id: 'chat',
      label: t('commandPalette.items.chat'),
      section: t('commandPalette.sections.pages'),
      action: () => { navigate('/chat'); setOpen(false) },
      shortcut: '⌘K',
    },
    {
      id: 'landing',
      label: t('commandPalette.items.landing'),
      section: t('commandPalette.sections.pages'),
      action: () => { navigate('/'); setOpen(false) },
    },
    {
      id: 'new-session',
      label: t('commandPalette.items.newSession'),
      section: t('commandPalette.sections.sessions'),
      action: () => { createSession(); setOpen(false) },
    },
    {
      id: 'settings',
      label: t('commandPalette.items.settings'),
      section: t('commandPalette.sections.settings'),
      action: () => { setOpen(false) },
    },
    {
      id: 'features',
      label: t('commandPalette.items.features'),
      section: t('commandPalette.sections.features'),
      action: () => { navigate('/'); setOpen(false) },
    },
    {
      id: 'architecture',
      label: t('commandPalette.items.architecture'),
      section: t('commandPalette.sections.features'),
      action: () => { navigate('/'); setOpen(false) },
    },
    {
      id: 'skills',
      label: t('commandPalette.items.skills'),
      section: t('commandPalette.sections.features'),
      action: () => { navigate('/'); setOpen(false) },
    },
    {
      id: 'download',
      label: t('commandPalette.items.download'),
      section: t('commandPalette.sections.features'),
      action: () => { navigate('/'); setOpen(false) },
    },
    {
      id: 'github',
      label: t('commandPalette.items.github'),
      section: t('commandPalette.sections.pages'),
      action: () => { window.open('https://github.com/bemlerlabs/mimi-nox', '_blank'); setOpen(false) },
    },
    {
      id: 'docs',
      label: t('commandPalette.items.docs'),
      section: t('commandPalette.sections.pages'),
      action: () => { window.open('https://miminox.app/docs', '_blank'); setOpen(false) },
    },
  ]

  // Load recent sessions for search
  const sessions = useChatStore.getState().sessions
  const sessionCommands: CommandItem[] = sessions.slice(0, 5).map((s) => ({
    id: `session-${s.id}`,
    label: s.title,
    section: t('commandPalette.sections.sessions'),
    action: () => {
      useChatStore.getState().setActiveSession(s.id)
      navigate('/chat')
      setOpen(false)
    },
  }))

  const allCommands = [...sessionCommands, ...commands]

  const filteredCommands = query
    ? allCommands.filter((c) =>
        c.label.toLowerCase().includes(query.toLowerCase()) ||
        c.section.toLowerCase().includes(query.toLowerCase())
      )
    : allCommands

  // Group by section
  const grouped: Record<string, CommandItem[]> = {}
  for (const cmd of filteredCommands) {
    if (!grouped[cmd.section]) {
      grouped[cmd.section] = []
    }
    grouped[cmd.section]!.push(cmd)
  }

  return {
    open,
    setOpen,
    query,
    setQuery,
    inputRef,
    grouped,
    t,
  }
}