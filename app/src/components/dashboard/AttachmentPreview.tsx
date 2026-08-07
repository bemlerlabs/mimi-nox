import { FileText, X } from 'lucide-react'

export interface Attachment {
  path: string
  name: string
}

interface AttachmentPreviewProps {
  attachments: Attachment[]
  onRemove: (index: number) => void
}

/** Angehängte Dateien als Chips mit Entfernen-Button (unterhalb des Inputs) */
export default function AttachmentPreview({ attachments, onRemove }: AttachmentPreviewProps) {
  if (attachments.length === 0) return null
  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {attachments.map((att, i) => (
        <div
          key={`${att.path}-${i}`}
          className="flex items-center gap-1.5 bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-xs text-white/70 max-w-[240px]"
        >
          <FileText className="h-3.5 w-3.5 text-green-400 flex-shrink-0" />
          <span className="truncate">{att.name}</span>
          <button
            onClick={() => onRemove(i)}
            className="text-white/30 hover:text-red-400 transition-colors ml-1 flex-shrink-0"
            aria-label="Attachment entfernen"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      ))}
    </div>
  )
}
