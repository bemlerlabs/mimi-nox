import { useRef, useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Search, Command as CommandIcon, ArrowRight } from 'lucide-react'
import type { CommandItem } from '@/hooks/useCommandPalette'

interface CommandPaletteProps {
  open: boolean
  query: string
  setQuery: (q: string) => void
  inputRef: React.RefObject<HTMLInputElement | null>
  grouped: Record<string, CommandItem[]>
  t: ReturnType<typeof useTranslation>['t']
  onClose: () => void
  onSelect: (cmd: CommandItem) => void
}

export default function CommandPalette({ open, query, setQuery, inputRef, grouped, t, onClose, onSelect }: CommandPaletteProps) {
  const [activeIndex, setActiveIndex] = useState(0)
  const allItemsRef = useRef<CommandItem[]>([])

  // Flatten all items for keyboard navigation
  useEffect(() => {
    const items: CommandItem[] = []
    for (const section of Object.values(grouped)) {
      items.push(...section)
    }
    allItemsRef.current = items
    setActiveIndex(0)
  }, [grouped])

  // Keyboard navigation
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIndex((i) => Math.min(i + 1, allItemsRef.current.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIndex((i) => Math.max(i - 1, 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        const active = allItemsRef.current[activeIndex]
        if (active) { onSelect(active); return }
        // If input has value, trigger first match
        const first = allItemsRef.current[0]
        if (first) { onSelect(first) }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, activeIndex, onSelect])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[20vh]" role="dialog" aria-modal="true" aria-label={t('commandPalette.title')}>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="relative z-10 w-full max-w-xl liquid-glass-strong rounded-2xl shadow-2xl border border-white/10 overflow-hidden">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5">
          <Search className="h-4 w-4 text-white/30 flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('commandPalette.placeholder')}
            className="flex-1 bg-transparent text-sm text-white placeholder:text-white/30 outline-none"
            aria-label={t('commandPalette.placeholder')}
          />
          <kbd className="hidden sm:inline-flex items-center gap-0.5 text-[10px] text-white/20 bg-white/5 rounded px-1.5 py-0.5 font-mono">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[60vh] overflow-y-auto p-2" role="listbox" aria-label={t('commandPalette.title')}>
          {Object.keys(grouped).length === 0 ? (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-white/30">{t('commandPalette.noResults')}</p>
            </div>
          ) : (
            Object.entries(grouped).map(([section, commands]) => (
              <div key={section}>
                <p className="px-2 py-1.5 text-[10px] font-medium text-white/20 uppercase tracking-wider">{section}</p>
                <ul role="list">
                  {commands.map((cmd) => {
                    const isActive = allItemsRef.current.indexOf(cmd) === activeIndex
                    return (
                      <li key={cmd.id} role="option" aria-selected={isActive}>
                        <button
                          onClick={() => onSelect(cmd)}
                          onMouseEnter={() => setActiveIndex(allItemsRef.current.indexOf(cmd))}
                          className={`w-full flex items-center gap-3 px-3 py-2 text-left text-sm transition-colors rounded-lg ${
                            isActive
                              ? 'bg-green-500/10 text-white'
                              : 'text-white/70 hover:bg-white/[0.03] hover:text-white'
                          }`}
                        >
                          <CommandIcon className="h-3.5 w-3.5 text-white/20 flex-shrink-0" />
                          <span className="flex-1 truncate">{cmd.label}</span>
                          {cmd.shortcut && (
                            <span className="text-[10px] text-white/20 font-mono">{cmd.shortcut}</span>
                          )}
                          <ArrowRight className="h-3 w-3 text-white/10" />
                        </button>
                      </li>
                    )
                  })}
                </ul>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-3 py-2 border-t border-white/5 flex items-center gap-3 text-[10px] text-white/15">
          <span className="flex items-center gap-1">
            <kbd className="bg-white/5 rounded px-1">↑↓</kbd> navigate
          </span>
          <span className="flex items-center gap-1">
            <kbd className="bg-white/5 rounded px-1">↵</kbd> select
          </span>
          <span className="flex items-center gap-1">
            <kbd className="bg-white/5 rounded px-1">ESC</kbd> close
          </span>
        </div>
      </div>
    </div>
  )
}