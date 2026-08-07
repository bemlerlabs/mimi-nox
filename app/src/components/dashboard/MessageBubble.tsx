import { useState, useCallback } from 'react'
import { Check, Copy, Sparkles } from 'lucide-react'
import { formatTime } from '@/lib/utils'
import type { ToolCall } from '@/store/chatStore'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import CodeBlock from './CodeBlock'
import ToolCallDisplay from './ToolCallDisplay'

interface MessageBubbleProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  tool_calls?: ToolCall[]
}

export default function MessageBubble({ role, content, timestamp, tool_calls }: MessageBubbleProps) {
  const isUser = role === 'user'
  const isAssistant = role === 'assistant'
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [content])

  return (
    <div className={`flex gap-3 mb-4 ${isUser ? 'flex-row-reverse' : ''} group`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? 'bg-green-500/20' : 'liquid-glass forest-glow-subtle'
      }`}>
        {isUser ? (
          <span className="text-sm font-medium text-green-400">U</span>
        ) : (
          <Sparkles className="h-4 w-4 text-green-400" />
        )}
      </div>

      {/* Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? 'text-right' : ''}`}>
        <div className={`rounded-2xl p-4 ${
          isUser
            ? 'bg-green-500/10 border border-green-500/20 rounded-tr-sm'
            : isAssistant
            ? 'liquid-glass rounded-tl-sm'
            : 'bg-yellow-500/10 border border-yellow-500/20 rounded-2xl'
        }`}>
          {isAssistant ? (
            <>
              <div className="text-sm text-white/90 prose prose-invert max-w-none prose-p:mb-2 prose-code:bg-white/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-strong:text-white prose-em:text-white/90">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                  components={{
                    pre: (props) => <CodeBlock>{props.children}</CodeBlock>,
                  }}
                >
                  {content}
                </ReactMarkdown>
              </div>
              {/* Copy Button */}
              <button
                onClick={handleCopy}
                className="mt-2 flex items-center gap-1.5 text-xs text-white/30 hover:text-green-400 transition-colors"
                aria-label={copied ? 'Kopiert' : 'Inhalte kopieren'}
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-green-400" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
                {copied ? 'Kopiert' : 'Kopieren'}
              </button>
            </>
          ) : (
            <div className="text-sm text-white/80">{content}</div>
          )}
        </div>

        {/* Tool Calls */}
        {tool_calls && tool_calls.length > 0 && <ToolCallDisplay tool_calls={tool_calls} />}

        {/* Timestamp */}
        <span className="text-xs text-white/30 mt-1 block">
          {formatTime(new Date(timestamp))}
        </span>
      </div>
    </div>
  )
}
