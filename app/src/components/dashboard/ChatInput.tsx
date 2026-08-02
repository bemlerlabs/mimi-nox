import { useState, useRef } from 'react'
import { Send, Paperclip, Image, Mic, FileText, Command } from 'lucide-react'
import { Badge } from '@/components/ui'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
}

export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [message, setMessage] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim())
      setMessage('')
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
            <button className="p-2 rounded-lg hover:bg-green-500/5 text-white/40 hover:text-green-400 transition-colors">
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
      <div className="flex items-center justify-center gap-2 mt-2">
        <Badge variant="outline">gemma4:12b</Badge>
        <Badge variant="success">Lokal</Badge>
      </div>
    </div>
  )
}
