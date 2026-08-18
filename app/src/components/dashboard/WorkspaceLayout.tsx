'use client'

import { useState, useEffect } from 'react'
import { LayoutGrid, Focus, PanelTop, Boxes, Minimize2 } from 'lucide-react'

export interface LayoutPreset {
  id: 'focus' | 'dev' | 'swarm' | 'minimal'
  name: string
  description: string
}

// 4 semantische Layout-Presets (2026 Best-Practice, eigene MiMi-Nox-Identität)
export const PRESETS: LayoutPreset[] = [
  {
    id: 'focus',
    name: 'Focus',
    description: 'Chat groß + Kontext-Rail — nur Agent',
  },
  {
    id: 'dev',
    name: 'Dev',
    description: 'Chat + Terminal + Explorer — Standard-Coding',
  },
  {
    id: 'swarm',
    name: 'Swarm',
    description: 'Agent-Panel links + Chat rechts — Multi-Agent',
  },
  {
    id: 'minimal',
    name: 'Minimal',
    description: 'Nur Chat — schmal, Fokus',
  },
]

const PRESET_ICONS: Record<LayoutPreset['id'], typeof LayoutGrid> = {
  focus: Focus,
  dev: PanelTop,
  swarm: Boxes,
  minimal: Minimize2,
}

interface WorkspaceLayoutProps {
  preset: LayoutPreset['id']
  onPresetChange?: (id: LayoutPreset['id']) => void
  /** Echte Chat-UI (WS, Messages, Input) — wird im zentralen Chat-Panel gerendert */
  chatContent?: React.ReactNode
}

export function WorkspaceLayout({ preset, onPresetChange, chatContent }: WorkspaceLayoutProps) {
  const [activePreset, setActivePreset] = useState<LayoutPreset['id']>(preset)

  // Sync externe Prop-Änderung (controlled/uncontrolled)
  useEffect(() => {
    setActivePreset(preset)
  }, [preset])

  const current = PRESETS.find((p) => p.id === activePreset) ?? PRESETS[0]!

  const selectPreset = (id: LayoutPreset['id']) => {
    setActivePreset(id)
    onPresetChange?.(id)
  }

  // Pane-Sichtbarkeit pro Layout
  const showTerminal = activePreset === 'dev'
  const showFiles = activePreset === 'dev'
  const showAgent = activePreset === 'swarm'
  const showExplorer = activePreset !== 'minimal'
  const showContextRail = activePreset !== 'minimal'

  return (
    <div data-testid={`layout-${activePreset}`} className="flex h-full w-full flex-col">
      {/* Layout-Umschalter */}
      <div className="flex items-center gap-1 border-b border-white/10 px-3 py-2">
        <LayoutGrid className="mr-1 h-4 w-4 text-white/50" />
        {PRESETS.map((p) => {
          const Icon = PRESET_ICONS[p.id]
          return (
            <button
              key={p.id}
              data-testid={`preset-${p.id}`}
              onClick={() => selectPreset(p.id)}
              className={`rounded px-2 py-1 text-xs font-medium transition ${
                activePreset === p.id
                  ? 'bg-white/15 text-white'
                  : 'text-white/60 hover:bg-white/10 hover:text-white'
              }`}
              title={p.description}
            >
              <Icon className="mr-1 inline h-3 w-3" />
              {p.name}
            </button>
          )
        })}
        <span className="ml-auto hidden text-[10px] text-white/40 sm:block">{current.description}</span>
      </div>

      {/* Panes-Grid */}
      <div className="grid flex-1 gap-0 overflow-hidden" style={{ gridTemplateColumns: 'auto 1fr auto' }}>
        {/* Explorer links — ab lg (1024px); auf Mobile bleibt der Chat vollflächig */}
        {showExplorer && (
          <div data-testid="panel-explorer" className="w-48 hidden border-r border-white/10 lg:block">
            <ExplorerPanel />
          </div>
        )}

        {/* Zentrale Panes */}
        <div className="grid min-w-0 flex-1" style={{ gridTemplateColumns: showAgent ? '1fr 1fr' : '1fr' }}>
          {showAgent && (
            <div data-testid="panel-agent" className="border-r border-white/10">
              <AgentPanel />
            </div>
          )}
          <div className="flex min-w-0 flex-col">
            <div data-testid="panel-chat" className="flex-1 overflow-hidden">
              <ChatPanel chatContent={chatContent} />
            </div>
            {(showTerminal || showFiles) && (
              <div className="grid h-48 border-t border-white/10" style={{ gridTemplateColumns: showTerminal && showFiles ? '1fr 1fr' : '1fr' }}>
                {showTerminal && (
                  <div data-testid="panel-terminal" className="border-r border-white/10">
                    <TerminalPanel />
                  </div>
                )}
                {showFiles && (
                  <div data-testid="panel-files">
                    <FilesPanel />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Kontext-Rail (Attach/Context) rechts — ab xl (1280px) */}
        {showContextRail && (
          <div data-testid="context-rail" className="w-56 hidden border-l border-white/10 xl:block">
            <ContextRail />
          </div>
        )}
      </div>
    </div>
  )
}

function ExplorerPanel() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <PanelHeader title="Explorer" />
      <div className="flex-1 overflow-auto p-2">
        <p className="text-xs text-white/50">Projektordner & Dateien</p>
      </div>
    </div>
  )
}

function ChatPanel({ chatContent }: { chatContent?: React.ReactNode }) {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      {chatContent ? (
        <div className="flex-1 min-h-0 overflow-hidden">{chatContent}</div>
      ) : (
        <>
          <PanelHeader title="Chat" />
          <div className="flex-1 overflow-auto p-2">
            <p className="text-xs text-white/50">Agent-Chat — lokal Ollama</p>
          </div>
        </>
      )}
    </div>
  )
}

function TerminalPanel() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <PanelHeader title="Terminal" />
      <div className="flex-1 overflow-auto p-2">
        <p className="text-xs text-white/50">Shell via Backend-Agent (validiert)</p>
      </div>
    </div>
  )
}

function FilesPanel() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <PanelHeader title="Dateien" />
      <div className="flex-1 overflow-auto p-2">
        <p className="text-xs text-white/50">Files & Diff</p>
      </div>
    </div>
  )
}

function AgentPanel() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <PanelHeader title="Agent" />
      <div className="flex-1 overflow-auto p-2">
        <p className="text-xs text-white/50">Swarm — Planer/Ausführer</p>
      </div>
    </div>
  )
}

function ContextRail() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <PanelHeader title="Kontext" />
      <div className="flex-1 overflow-auto p-2">
        <p className="text-xs text-white/50">Attachments & Notizen</p>
      </div>
    </div>
  )
}

function PanelHeader({ title }: { title: string }) {
  return (
    <div className="border-b border-white/10 px-3 py-1.5 text-[11px] font-medium uppercase tracking-wide text-white/50">
      {title}
    </div>
  )
}
