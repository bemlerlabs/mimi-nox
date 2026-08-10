import { Camera, History, X } from 'lucide-react'
import type { ChatCheckpoint } from '@/lib/checkpoints'

interface CheckpointControlsProps {
  checkpoints: ChatCheckpoint[]
  onCreate: () => void
  onRollback: (id: string) => void
  onDelete: (id: string) => void
}

/**
 * Checkpoint & Rollback (P2-7) — kompakte Steuerleiste.
 * Ein Button sichert einen Snapshot der aktuellen Session-Messages,
 * darunter liegen die gespeicherten Checkpoints mit Rollback-/Lösch-Aktionen.
 */
export default function CheckpointControls({
  checkpoints,
  onCreate,
  onRollback,
  onDelete,
}: CheckpointControlsProps) {
  return (
    <div className="flex items-center gap-2 shrink-0">
      <button
        onClick={onCreate}
        title="Snapshot sichern"
        className="p-1.5 rounded-lg hover:bg-green-500/5 text-white/40 hover:text-green-400 transition-colors"
      >
        <Camera className="h-4 w-4" />
      </button>
      {checkpoints.length > 0 && (
        <div className="flex items-center gap-1.5">
          {checkpoints.map((cp) => (
            <span
              key={cp.id}
              className="flex items-center gap-1 text-[10px] text-white/40 font-mono px-1.5 py-0.5 rounded bg-white/5"
            >
              <button
                onClick={() => onRollback(cp.id)}
                title={`Rollback zu ${cp.label}`}
                className="hover:text-green-400 transition-colors"
              >
                <History className="h-3 w-3" />
              </button>
              <span className="max-w-24 truncate">{cp.label}</span>
              <button
                onClick={() => onDelete(cp.id)}
                title={`Checkpoint ${cp.label} löschen`}
                className="hover:text-red-400 transition-colors"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
