import { useState, useEffect, useCallback, useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { motion } from 'framer-motion'
import { Menu, Settings, Wifi, WifiOff, Sparkles, X, Check, AlertTriangle } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { WSClient } from '@/lib/websocket'
import { sendMessage } from '@/lib/api'
import Sidebar from './Sidebar'
import ChatInput from './ChatInput'
import MessageBubble from './MessageBubble'
import SettingsPanel from './SettingsPanel'
import ErrorBoundary from '@/components/ui/ErrorBoundary'
import { useTranslation } from 'react-i18next'

interface PendingToolCall {
  id: string
  tool_name: string
  tool_args: Record<string, unknown>
  description: string
  session_id: string
}

export default function ChatLayout() {
  const { t } = useTranslation()
  const { currentSession, isTyping, createSession, addMessage, setTyping, setPendingToolCall, pendingToolCall } = useChatStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [lastStatus, setLastStatus] = useState<'connected' | 'disconnected' | 'reconnecting'>('disconnected')
  const wsClientRef = useRef<WSClient | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const pendingToolRef = useRef<PendingToolCall | null>(null)

  // Virtualization — only render visible messages
  const parentRef = useRef<HTMLDivElement>(null)
  const rowVirtualizer = useVirtualizer({
    count: currentSession?.messages.length ?? 0,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 120,
    overscan: 5,
  })

  // Auto-scroll on new messages (last item)
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentSession?.messages, pendingToolCall])

  // Init WSClient
  useEffect(() => {
    const client = new WSClient(import.meta.env.VITE_WS_URL || 'ws://localhost:8765')

    client.onMessage((data) => {
      if (data.type === 'error') {
        addMessage('system', t('chat.errorUnknown'))
        setTyping(false)
      } else {
        addMessage('assistant', data.content || '')
      }
    })

    client.onStatus((status) => {
      setLastStatus(status)
      setWsConnected(status === 'connected')
      if (status === 'reconnecting') {
        addMessage('system', t('chat.reconnecting'))
      }
    })

    client.onToolApproval((request) => {
      const toolCall: PendingToolCall = {
        id: `tool-${Date.now()}`,
        tool_name: request.tool_name,
        tool_args: request.tool_args || {},
        description: request.description || t('chat.toolWillRun', { toolName: request.tool_name }),
        session_id: request.session_id || '',
      }
      pendingToolRef.current = toolCall
      setPendingToolCall(toolCall)
    })

    wsClientRef.current = client
    client.connect().then(() => {
      setWsConnected(true)
    }).catch(() => {
      setWsConnected(false)
    })

    return () => client.disconnect()
  }, [t, addMessage, setTyping, setPendingToolCall])

  const handleSend = useCallback((message: string) => {
    if (!currentSession) {
      createSession()
    }

    addMessage('user', message)
    setTyping(true)

    if (wsClientRef.current) {
      wsClientRef.current.send(message)
    } else {
      sendViaApi(message).finally(() => setTyping(false))
    }
  }, [currentSession, createSession, addMessage, setTyping])

  async function sendViaApi(message: string) {
    try {
      let streamedContent = ''
      const handleChunk = (chunk: string) => {
        streamedContent += chunk
        addMessage('assistant', streamedContent)
      }

      await sendMessage(message, undefined, handleChunk)
      addMessage('assistant', streamedContent || t('chat.responseReceived'))
    } catch (err) {
      addMessage('system', t('chat.apiError', { message: err instanceof Error ? err.message : String(err) }))
    }
  }

  // Tool approval handlers
  const handleToolApprove = useCallback(() => {
    if (!pendingToolRef.current || !wsClientRef.current) return
    const { session_id, tool_name } = pendingToolRef.current
    wsClientRef.current.approveTool(session_id, tool_name, true)
    setPendingToolCall(null)
    pendingToolRef.current = null
  }, [])

  const handleToolDeny = useCallback(() => {
    if (!pendingToolRef.current || !wsClientRef.current) return
    const { session_id, tool_name } = pendingToolRef.current
    wsClientRef.current.approveTool(session_id, tool_name, false)
    addMessage('system', t('chat.toolDenied', { toolName: tool_name }))
    setPendingToolCall(null)
    pendingToolRef.current = null
  }, [addMessage, t])

  const dismissToolRequest = useCallback(() => {
    setPendingToolCall(null)
    pendingToolRef.current = null
  }, [])

  return (
    <ErrorBoundary>
      <div className="h-screen flex bg-black">
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative">
        {/* Header */}
        <header className="border-b border-white/5 px-4 h-14 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden"
            >
              <Menu className="h-5 w-5 text-green-400/60" />
            </button>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md liquid-glass flex items-center justify-center">
                <Sparkles className="h-3 w-3 text-green-400" />
              </div>
              <h1 className="text-sm font-semibold text-white/90">
                {currentSession?.title || t('nav.appName')}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              {lastStatus === 'reconnecting' ? (
                <span className="flex items-center gap-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-40" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400" />
                  </span>
                  <span className="text-[10px] text-amber-400/60 font-medium">{t('chat.connecting')}</span>
                </span>
              ) : wsConnected ? (
                <span className="flex items-center gap-1.5">
                  <Wifi className="h-3.5 w-3.5 text-green-400" />
                  <span className="text-[10px] text-green-400/60 font-medium">{t('chat.connected')}</span>
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <WifiOff className="h-3.5 w-3.5 text-red-400/60" />
                  <span className="text-[10px] text-white/20 font-medium">{t('chat.disconnected')}</span>
                </span>
              )}
            </div>
            <button
              onClick={() => setSettingsOpen(true)}
              className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"
            >
              <Settings className="h-4 w-4" />
            </button>
          </div>
        </header>

        {/* Messages — virtualized (only render visible items) */}
        {!currentSession || currentSession.messages.length === 0 ? (
          <EmptyState onSuggestion={(text) => handleSend(text)} />
        ) : (
          <>
            <div ref={parentRef} className="flex-1 overflow-y-auto">
              <div className="max-w-3xl mx-auto px-4 py-6 relative" style={{ height: `${rowVirtualizer.getTotalSize()}px` }}>
                {rowVirtualizer.getVirtualItems().map((virtualItem) => {
                  const msg = currentSession?.messages[virtualItem.index]
                  if (!msg) return null
                  return (
                    <div
                      key={msg.id}
                      ref={rowVirtualizer.measureElement}
                      data-index={virtualItem.index}
                      className="absolute left-0 w-full"
                      style={{ transform: `translateY(${virtualItem.start}px)` }}
                    >
                      {/* Tool Approval Banner */}
                      {pendingToolCall && virtualItem.index === 0 && (
                        <motion.div
                          initial={{ opacity: 0, y: -10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -10 }}
                          className="mb-4 liquid-glass-strong rounded-xl p-4 border border-amber-400/15"
                        >
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                              <AlertTriangle className="h-4 w-4 text-amber-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-white/90 mb-1">
                                {t('chat.toolApproval.title')}
                              </p>
                              <p className="text-xs text-white/50 mb-3">
                                <code className="text-amber-400/80 font-mono">{pendingToolCall.tool_name}</code>
                                {' '}— {pendingToolCall.description}
                              </p>
                              {Object.keys(pendingToolCall.tool_args).length > 0 && (
                                <pre className="text-[10px] font-mono bg-black/40 rounded-lg p-2 mb-3 text-white/30 overflow-x-auto">
                                  {JSON.stringify(pendingToolCall.tool_args, null, 2)}
                                </pre>
                              )}
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={handleToolApprove}
                                  className="liquid-glass rounded-lg px-3 py-1.5 text-xs font-medium text-green-400 hover:bg-green-500/10 transition-all flex items-center gap-1.5"
                                >
                                  <Check className="h-3 w-3" />
                                  {t('chat.toolApproval.approve')}
                                </button>
                                <button
                                  onClick={handleToolDeny}
                                  className="liquid-glass rounded-lg px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/10 transition-all flex items-center gap-1.5"
                                >
                                  <X className="h-3 w-3" />
                                  {t('chat.toolApproval.deny')}
                                </button>
                                <button
                                  onClick={dismissToolRequest}
                                  className="text-[10px] text-white/20 hover:text-white/40 transition-colors px-2 py-1"
                                >
                                  {t('chat.toolApproval.later')}
                                </button>
                              </div>
                            </div>
                            <button
                              onClick={dismissToolRequest}
                              className="text-white/20 hover:text-white/40 transition-colors flex-shrink-0"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        </motion.div>
                      )}

                      <MessageBubble
                        role={msg.role}
                        content={msg.content}
                        timestamp={msg.timestamp}
                        tool_calls={msg.tool_calls}
                      />
                    </div>
                  )
                })}
              </div>
            </div>
            <div ref={messagesEndRef} />
          </>
        )}

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          disabled={isTyping}
        />
      </div>
      {/* Settings Panel */}
      <SettingsPanel
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </div>
    </ErrorBoundary>
  )
}

function EmptyState({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  const { t } = useTranslation()
  const suggestions = [
    { title: t('chat.suggestions.0.title'), desc: t('chat.suggestions.0.desc') },
    { title: t('chat.suggestions.1.title'), desc: t('chat.suggestions.1.desc') },
    { title: t('chat.suggestions.2.title'), desc: t('chat.suggestions.2.desc') },
    { title: t('chat.suggestions.3.title'), desc: t('chat.suggestions.3.desc') },
  ]
  return (
    <motion.div
      initial={{ filter: 'blur(10px)', opacity: 0, y: 20 }}
      animate={{ filter: 'blur(0px)', opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="flex flex-col items-center justify-center h-full min-h-[60vh] text-center"
    >
      <div className="w-16 h-16 rounded-2xl liquid-glass-strong flex items-center justify-center mb-6 forest-glow">
        <Sparkles className="h-8 w-8 text-green-400" />
      </div>
      <h2 className="text-2xl font-bold text-white/90 mb-2">{t('chat.emptyStateTitle')}</h2>
      <p className="text-white/40 mb-8 max-w-md">
        {t('chat.emptyStateDesc')}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
        {suggestions.map((s: {title: string; desc: string}, i: number) => (
          <button
            key={i}
            className="liquid-glass-strong rounded-xl p-4 text-left hover:bg-green-500/5 transition-colors group"
            onClick={() => onSuggestion(s.title)}
          >
            <p className="text-sm text-white/70 group-hover:text-white/90 transition-colors">{s.title}</p>
            <p className="text-xs text-white/30 mt-1">{s.desc}</p>
          </button>
        ))}
      </div>
    </motion.div>
  )
}