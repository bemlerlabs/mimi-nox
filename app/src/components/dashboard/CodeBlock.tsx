import { useState, useCallback, type ReactNode } from 'react'
import { Check, Copy } from 'lucide-react'

/** Extrahiert den rohen Text aus React-Kindern (für den Copy-Button) */
function toText(node: ReactNode): string {
  if (node == null || typeof node === 'boolean') return ''
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(toText).join('')
  if (typeof node === 'object' && 'props' in node) {
    const p = node.props as { children?: ReactNode }
    return toText(p.children)
  }
  return ''
}

interface CodeBlockProps {
  children?: ReactNode
}

/** Fenced-Codeblock: Header mit Sprache + Copy, darunter das (von rehype-highlight
 *  bereits mit hljs-Klassen versehene) <pre>...</pre> des Kind-Elements. */
export default function CodeBlock({ children }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const text = toText(children)

  // Sprache aus dem className des inneren <code>-Elements (language-xxx)
  let lang: string | undefined
  let codeElement: ReactNode | null = null
  const child = Array.isArray(children) ? children[0] : children
  if (child != null && typeof child === 'object' && 'props' in child) {
    const props = child.props as { className?: string; children?: ReactNode }
    lang = props.className ? /language-(\S+)/.exec(props.className)?.[1] : undefined
    codeElement = child
  }

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [text])

  return (
    <div className="relative group/code my-3">
      <div className="flex items-center justify-between bg-black/40 border border-white/10 rounded-t-lg px-3 py-1.5">
        <span className="text-[10px] text-white/40 font-mono uppercase tracking-wide">
          {lang || 'text'}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[10px] text-white/30 hover:text-green-400 transition-colors"
          aria-label={copied ? 'Kopiert' : 'Code kopieren'}
        >
          {copied ? <Check className="h-3 w-3 text-green-400" /> : <Copy className="h-3 w-3" />}
          {copied ? 'Kopiert' : 'Kopieren'}
        </button>
      </div>
      {codeElement}
    </div>
  )
}
