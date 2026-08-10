import { useMemo } from 'react'
import type { ChatMessage, MessageRole } from '@/types'

/**
 * MiMi Nox — Timeline Rail (P2-6)
 *
 * Schmale vertikale Marker-Leiste neben den Messages. Jeder Punkt ist eine
 * Nachricht; Farbe nach Rolle; Klick scrollt zum zugehörigen Message.
 * Die aktuell sichtbare Nachricht wird hervorgehoben (via activeIndex).
 */

const ROLE_COLOR: Record<MessageRole, string> = {
  user: 'bg-green-400',
  assistant: 'bg-white/40',
  system: 'bg-amber-400/70',
}

interface TimelineRailProps {
  messages: ChatMessage[]
  activeIndex?: number
  onSelect: (index: number) => void
}

export default function TimelineRail({ messages, activeIndex, onSelect }: TimelineRailProps) {
  const markers = useMemo(
    () =>
      (messages || []).map((m, i) => ({
        index: i,
        color: ROLE_COLOR[m.role] ?? 'bg-white/20',
        active: i === activeIndex,
      })),
    [messages, activeIndex],
  )

  if (markers.length === 0) return null

  return (
    <div className="w-3 flex-shrink-0 self-stretch flex flex-col items-center gap-1 py-2 select-none"
      aria-label="Timeline"
    >
      {markers.map((m) => (
        <button
          key={m.index}
          onClick={() => onSelect(m.index)}
          title={`Nachricht ${m.index + 1}${m.active ? ' (aktuell)' : ''}`}
          className={`w-1.5 h-1.5 rounded-full transition-all cursor-pointer ${
            m.color
          } ${m.active ? 'ring-2 ring-white/70 scale-125' : 'opacity-40 hover:opacity-100'}`}
          aria-label={`Zu Nachricht ${m.index + 1}`}
        />
      ))}
    </div>
  )
}
