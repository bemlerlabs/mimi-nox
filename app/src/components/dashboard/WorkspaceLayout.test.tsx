import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WorkspaceLayout, PRESETS } from './WorkspaceLayout'

describe('WorkspaceLayout — 4 Layout-Presets (2026 Best-Practice)', () => {
  it('definiert genau 4 semantische Presets: Focus, Dev, Swarm, Minimal', () => {
    expect(PRESETS).toHaveLength(4)
    const names = PRESETS.map((p) => p.id)
    expect(names).toEqual(['focus', 'dev', 'swarm', 'minimal'])
  })

  it('rendert das Focus-Layout mit Chat-Panel als Hauptbereich', () => {
    render(<WorkspaceLayout preset="focus" />)
    expect(screen.getByTestId('panel-chat')).toBeInTheDocument()
    expect(screen.getByTestId('layout-focus')).toBeInTheDocument()
  })

  it('rendert das Dev-Layout mit Chat + Terminal + Explorer', () => {
    render(<WorkspaceLayout preset="dev" />)
    expect(screen.getByTestId('panel-terminal')).toBeInTheDocument()
    expect(screen.getByTestId('panel-files')).toBeInTheDocument()
    expect(screen.getByTestId('layout-dev')).toBeInTheDocument()
  })

  it('rendert das Swarm-Layout mit Agent-Panel links neben dem Chat', () => {
    render(<WorkspaceLayout preset="swarm" />)
    expect(screen.getByTestId('panel-agent')).toBeInTheDocument()
    expect(screen.getByTestId('layout-swarm')).toBeInTheDocument()
  })

  it('rendert das Minimal-Layout mit nur dem Chat (schmal)', () => {
    render(<WorkspaceLayout preset="minimal" />)
    expect(screen.getByTestId('layout-minimal')).toBeInTheDocument()
    expect(screen.queryByTestId('panel-terminal')).not.toBeInTheDocument()
  })

  it('erlaubt Layout-Umschalten über den Preset-Umschalter', () => {
    const { rerender } = render(<WorkspaceLayout preset="dev" />)
    expect(screen.getByTestId('layout-dev')).toBeInTheDocument()
    rerender(<WorkspaceLayout preset="swarm" />)
    expect(screen.getByTestId('layout-swarm')).toBeInTheDocument()
  })
})

describe('WorkspaceLayout — Panes & Kontext-Rail', () => {
  it('rendert die Kontext-Rail (Attach/Context) im Dev-Layout', () => {
    render(<WorkspaceLayout preset="dev" />)
    expect(screen.getByTestId('context-rail')).toBeInTheDocument()
  })

  it('rendert den Explorer links in allen Nicht-Minimal-Layouts', () => {
    render(<WorkspaceLayout preset="focus" />)
    expect(screen.getByTestId('panel-explorer')).toBeInTheDocument()
  })
})
