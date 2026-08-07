import { Badge } from '@/components/ui'
import type { ToolCall } from '@/store/chatStore'

/** Tool-Call-Anzeige innerhalb einer Assistant-Nachricht */
export default function ToolCallDisplay({ tool_calls }: { tool_calls: ToolCall[] }) {
  return (
    <div className="mt-2 space-y-1">
      {tool_calls.map((tool) => (
        <div key={tool.id} className="liquid-glass rounded-lg p-2 flex items-center gap-2">
          <Badge
            variant={
              tool.status === 'approved' ? 'success' :
              tool.status === 'denied' ? 'destructive' :
              tool.status === 'completed' ? 'info' : 'warning'
            }
          >
            {tool.name}
          </Badge>
          <span className="text-xs text-white/40">{tool.status}</span>
        </div>
      ))}
    </div>
  )
}
