import { useMemo, useState } from 'react'
import type { ChatMessage } from '@/types'
import { estimateContextUsage, formatPercent, WARN_THRESHOLD } from '@/lib/contextMeter'
import { Zap, Flame, Shield } from 'lucide-react'

/**
 * MiMi Nox — Context Meter + Status Bar (P2-5)
 *
 * Zeigt die Live-Kontext-Belegung einer Session (%-full Meter), das
 * Token-Breakdown nach Rolle und einen YOLO-Toggle (autonomer Modus).
 *
 * Offline-first: die Belegung wird rein aus den Messages geschätzt —
 * kein Backend-Abruf nötig.
 */

interface StatusBarProps {
  messages: ChatMessage[]
  windowTokens?: number
  yolo: boolean
  onYoloChange: (value: boolean) => void
}

export default function StatusBar({
  messages,
  windowTokens,
  yolo,
  onYoloChange,
}: StatusBarProps) {
  const usage = useMemo(
    () => estimateContextUsage(messages || [], windowTokens),
    [messages, windowTokens],
  )

  const [expanded, setExpanded] = useState(false)

  const warn = usage.percent / 100 >= WARN_THRESHOLD
  const danger = usage.percent >= 95
  const meterColor = danger
    ? 'bg-red-500'
    : warn
      ? 'bg-amber-400'
      : 'bg-green-400'

  return (
    <div className="border-b border-white/5 px-3 py-1.5 flex items-center gap-3 flex-shrink-0 select-none">
      {/* Live %-full Meter */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden flex-shrink-0 max-w-[120px]">
          <div
            className={`h-full rounded-full transition-all ${meterColor}`}
            style={{ width: `${usage.percent}%` }}
          />
        </div>
        <span
          className={`text-[10px] font-mono tabular-nums ${danger ? 'text-red-400' : warn ? 'text-amber-400' : 'text-white/40'}`}
        >
          {formatPercent(usage.percent)}
        </span>
      </div>

      {/* Token-Breakdown (Toggle auf Klick) */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="text-[10px] font-mono text-white/30 hover:text-white/60 transition-colors flex items-center gap-1"
        title="Token-Breakdown anzeigen"
      >
        <Zap className="h-3 w-3 text-green-400/70" />
        <span>
          {usage.tokens.total.toLocaleString()} tok
          {expanded && (
            <span className="text-white/20">
              {' '}
              (U {usage.tokens.user.toLocaleString()} · A{' '}
              {usage.tokens.assistant.toLocaleString()} · S{' '}
              {usage.tokens.system.toLocaleString()})
            </span>
          )}
        </span>
      </button>

      <span className="text-[10px] text-white/20 font-mono">
        {usage.remaining.toLocaleString()} frei
      </span>

      {warn && (
        <span className="text-[10px] text-amber-400/70 flex items-center gap-1">
          <Flame className="h-3 w-3" />
          kompakt empfohlen
        </span>
      )}

      {/* YOLO-Toggle */}
      <button
        onClick={() => onYoloChange(!yolo)}
        className={`flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-[10px] font-medium transition-colors ${
          yolo
            ? 'text-green-400 bg-green-500/10'
            : 'text-white/30 hover:text-white/60'
        }`}
        title={yolo ? 'YOLO aktiv — autonomer Modus' : 'YOLO aus — Tool-Freigaben manuell'}
      >
        <Shield className={`h-3 w-3 ${yolo ? 'text-green-400' : 'text-white/30'}`} />
        YOLO
        <span
          className={`h-1.5 w-1.5 rounded-full ${yolo ? 'bg-green-400' : 'bg-white/20'}`}
        />
      </button>
    </div>
  )
}
