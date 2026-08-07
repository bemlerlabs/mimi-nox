import { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Image, Mic, FileText, Command } from 'lucide-react'
import { Badge } from '@/components/ui'
import { getSettings } from '@/lib/api'
import AttachmentPreview, { type Attachment } from './AttachmentPreview'

export type { Attachment }

interface ChatInputProps {
  onSend: (message: string, attachments?: Attachment[]) => void
  disabled?: boolean
}

// Tauri 2.x IPC — graceful fallback im Browser/Dev-Modus
function invoke(cmd: string): Promise<unknown> {
  if (window.__TAURI__?.core?.invoke) {
    return window.__TAURI__.core.invoke(cmd)
  }
  console.log(`[Tauri IPC] ${cmd}`)
  return Promise.resolve(null)
}

export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [message, setMessage] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const [model, setModel] = useState('gemma4:e4b')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Aktives Modell aus Settings laden (statt hartkodiert)
  useEffect(() => {
    let cancelled = false
    getSettings()
      .then((s) => {
        if (!cancelled && s.provider?.model) setModel(s.provider.model)
      })
      .catch(() => {}) // Backend offline → Default-Badge behalten
    return () => { cancelled = true }
  }, [])

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim(), attachments.length > 0 ? attachments : undefined)
      setMessage('')
      setAttachments([])
    }
  }

  // Native Datei-Auswahl (Tauri) oder Browser-Input
  const handleAttach = async () => {
    const result = await invoke('open_file_picker')
    if (result && typeof result === 'string') {
      const name = result.split(/[\\/]/).pop() || result
      setAttachments((prev) => [...prev, { path: result, name }])
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="px-4 pb-4">
      <div className={`liquid-glass rounded-2xl p-3 transition-all duration-200 ${isFocused ? 'forest-glow-subtle' : ''}`}>
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder="Schreibe eine Nachricht..."
          className="w-full bg-transparent text-white placeholder:text-white/30 resize-none outline-none text-sm min-h-[48px] max-h-32"
          rows={1}
          disabled={disabled}
        />
        <div className="flex items-center justify-between mt-2">
          <div className="flex items-center gap-1">
            <button
              onClick={handleAttach}
              className="p-2 rounded-lg hover:bg-green-500/5 text-white/40 hover:text-green-400 transition-colors"
            >
              <Paperclip className="h-4 w-4" />
            </button>
            <button className="p-2 rounded-lg hover:bg-green-500/5 text-white/40 hover:text-green-400 transition-colors">
              <Image className="h-4 w-4" />
            </button>
            <button className="p-2 rounded-lg hover:bg-green-500/5 text-white/40 hover:text-green-400 transition-colors">
              <Mic className="h-4 w-4" />
            </button>
            <button className="p-2 rounded-lg hover:bg-green-500/5 text-white/40 hover:text-green-400 transition-colors">
              <FileText className="h-4 w-4" />
            </button>
            <button className="p-2 rounded-lg hover:bg-green-500/5 text-white/40 hover:text-green-400 transition-colors">
              <Command className="h-4 w-4" />
            </button>
          </div>
          <button
            onClick={handleSend}
            disabled={disabled || !message.trim()}
            className="bg-green-500 hover:bg-green-600 disabled:opacity-30 disabled:cursor-not-allowed text-black rounded-xl p-2 transition-all duration-200 forest-glow"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
      <AttachmentPreview
        attachments={attachments}
        onRemove={(i) => setAttachments((prev) => prev.filter((_, idx) => idx !== i))}
      />
      <div className="flex items-center justify-center gap-2 mt-2">
        <Badge variant="outline">{model}</Badge>
        <Badge variant="success">Lokal</Badge>
      </div>
    </div>
  )
}
