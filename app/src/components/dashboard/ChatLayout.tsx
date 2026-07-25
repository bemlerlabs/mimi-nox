import { useState, useEffect, useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import { Menu, Settings, Wifi, WifiOff, Sparkles } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { WSClient } from '@/lib/websocket'
import { sendMessage } from '@/lib/api'
import Sidebar from './Sidebar'
import ChatInput from './ChatInput'
import MessageBubble from './MessageBubble'
import TypingIndicator from './TypingIndicator'

const suggestions = [
  { title: 'Erkläre mir mein Projekt', desc: 'Analysiere deinen Code' },
  { title: 'Schreibe eine E-Mail', desc: 'Reviewe meinen Code' },
  { title: 'Analysiere dieses Bild', desc: 'Erstelle ein Diagramm' },
  { title: 'Suche Online', desc: 'Recherche zu einem Thema' },
]

export default function ChatLayout() {
  const { currentSession, isTyping, createSession, addMessage, setTyping } = useChatStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const wsClientRef = useRef<WSClient | null>(null)
  const sessionIdRef = useRef<string>('')

  // Auto-scroll on new messages
  const messagesEndRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentSession?.messages])

  // Init WSClient
  useEffect(() => {
    const client = new WSClient(import.meta.env.VITE_WS_URL || 'ws://localhost:8765')
    
    client.onMessage((data) => {
      if (data.type === 'error') {
        addMessage('system', `Error: ${data.content || 'Unbekannter Fehler'}`)
        setTyping(false)
      } else {
        addMessage('assistant', data.content || '')
      }
    })

    client.onStatus((status) => {
      setWsConnected(status === 'connected')
      if (status === 'reconnecting') {
        addMessage('system', 'Verbindung getrennt — versuche erneut zu verbinden...')
      }
    })

    client.onToolApproval(async (request) => {
      console.log('Tool approval needed:', request)
      // Auto-approve for now
      client.approveTool(request.session_id, request.tool_name, true)
    })

    wsClientRef.current = client
    client.connect().then(() => {
      setWsConnected(true)
    }).catch(() => {
      setWsConnected(false)
    })

    return () => client.disconnect()
  }, [])

  const handleSend = useCallback((message: string) => {
    // Create session if none exists
    if (!currentSession) {
      createSession()
    }

    // Add user message to store
    addMessage('user', message)
    setTyping(true)

    // Send via WS if connected, else REST API
    if (wsClientRef.current) {
      wsClientRef.current.send(message)
    } else {
      // Fallback: REST API mit Streaming
      console.log('No WS available, using REST API')
      sendViaApi(message).finally(() => setTyping(false))
    }
  }, [currentSession, createSession, addMessage, setTyping])

  async function sendViaApi(message: string) {
    try {
      // Track streaming content
      let streamedContent = ''
      const handleChunk = (chunk: string) => {
        streamedContent += chunk
        // Update last assistant message with streamed content
        addMessage('assistant', streamedContent)
      }
      
      const response = await sendMessage(message, sessionIdRef.current, handleChunk)
      addMessage('assistant', response.content || 'Antwort erhalten')
    } catch (err) {
      addMessage('system', `❌ API-Fehler: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  return (
    <div className="h-screen flex bg-black">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="border-b border-green-500/10 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden"
            >
              <Menu className="h-5 w-5 text-green-400" />
            </button>
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-green-400" />
              <h1 className="font-semibold text-white">
                {currentSession?.title || 'MiMi Nox'}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              {wsConnected ? (
                <Wifi className="h-3 w-3 text-green-400" />
              ) : (
                <WifiOff className="h-3 w-3 text-red-400" />
              )}
              <span className="text-xs text-green-400/60">
                {wsConnected ? 'Verbunden' : 'Getrennt'}
              </span>
            </div>
            <button className="text-white/40 hover:text-green-400 transition-colors">
              <Settings className="h-5 w-5" />
            </button>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="max-w-3xl mx-auto">
            {!currentSession || currentSession.messages.length === 0 ? (
              <EmptyState onSuggestion={(text) => handleSend(text)} />
            ) : (
              <>
                {currentSession.messages.map((msg) => (
                  <MessageBubble
                    key={msg.id}
                    role={msg.role}
                    content={msg.content}
                    timestamp={msg.timestamp}
                    tool_calls={msg.tool_calls}
                  />
                ))}
                <TypingIndicator />
                <div ref={messagesEndRef} />
              </>
            )}
          </div>
        </div>

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          disabled={isTyping}
        />
      </div>
    </div>
  )
}

function EmptyState({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  return (
    <motion.div
      initial={{ filter: 'blur(10px)', opacity: 0, y: 20 }}
      animate={{ filter: 'blur(0px)', opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="flex flex-col items-center justify-center h-full text-center"
    >
      <div className="w-20 h-20 rounded-3xl liquid-glass-strong flex items-center justify-center mb-6 forest-glow">
        <Sparkles className="h-10 w-10 text-green-400" />
      </div>
      <h2 className="text-2xl font-bold text-white mb-2">MiMi Nox</h2>
      <p className="text-white/50 mb-8 max-w-md">
        Dein lokaler KI-Assistent. Privat. Lokal. Dein.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg">
        {suggestions.map((s, i) => (
          <button 
            key={i} 
            className="liquid-glass rounded-xl p-4 text-left hover:bg-green-500/5 transition-colors"
            onClick={() => onSuggestion(s.title)}
          >
            <p className="text-sm text-white/70">{s.title}</p>
            <p className="text-xs text-white/40 mt-1">{s.desc}</p>
          </button>
        ))}
      </div>
    </motion.div>
  )
}