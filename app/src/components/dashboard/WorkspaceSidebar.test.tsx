import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { WorkspaceSidebar, SIDEBAR_TABS } from './WorkspaceSidebar'

describe('WorkspaceSidebar — 4 Bereiche (eigene MiMi-Nox-Navigation, nicht Hermes)', () => {
  it('definiert die 4 Bereiche: Sessions, Artefakte, Messenger, Capability', () => {
    const ids = SIDEBAR_TABS.map((t) => t.id)
    expect(ids).toEqual(['sessions', 'artifacts', 'messenger', 'capability'])
  })

  it('rendert alle 4 Tabs in der Sidebar', () => {
    render(<WorkspaceSidebar />)
    expect(screen.getByTestId('tab-sessions')).toBeInTheDocument()
    expect(screen.getByTestId('tab-artifacts')).toBeInTheDocument()
    expect(screen.getByTestId('tab-messenger')).toBeInTheDocument()
    expect(screen.getByTestId('tab-capability')).toBeInTheDocument()
  })

  it('zeigt oben den New-Session-Button', () => {
    render(<WorkspaceSidebar />)
    expect(screen.getByTestId('new-session')).toBeInTheDocument()
  })

  it('zeigt unten die Option "Projekt anlegen"', () => {
    render(<WorkspaceSidebar />)
    expect(screen.getByTestId('new-project')).toBeInTheDocument()
  })

  it('listet Sessions im Sessions-Tab (Default)', () => {
    const sessions = [
      { id: 's1', title: 'Refactor', messages: [], createdAt: Date.now() },
    ]
    render(<WorkspaceSidebar sessions={sessions} />)
    expect(screen.getByText('Refactor')).toBeInTheDocument()
  })

  it('wechselt den aktiven Bereich per Klick', () => {
    render(<WorkspaceSidebar activeTab="sessions" />)
    fireEvent.click(screen.getByTestId('tab-artifacts'))
    expect(screen.getByTestId('artifacts-view')).toBeInTheDocument()
  })

  it('pinned Sessions werden oben angezeigt', () => {
    const pinned = [
      { id: 'p1', title: 'Wichtig', messages: [], createdAt: Date.now(), pinned: true },
      { id: 's2', title: 'Normal', messages: [], createdAt: Date.now() },
    ]
    render(<WorkspaceSidebar sessions={pinned} />)
    const items = screen.getAllByTestId('session-item')
    expect(items[0]).toHaveTextContent('Wichtig')
  })
})

describe('WorkspaceSidebar — Pin-Funktion', () => {
  it('rendert Pin-Button auf jeder Session', () => {
    const sessions = [{ id: 's1', title: 'A', messages: [], createdAt: Date.now() }]
    render(<WorkspaceSidebar sessions={sessions} />)
    expect(screen.getAllByTestId('pin-btn').length).toBe(1)
  })

  it('Pin-Toggle ruft onTogglePin mit der Session-ID auf', () => {
    let pinned = false
    const onTogglePin = (_id: string) => {
      pinned = true
    }
    const sessions = [{ id: 's1', title: 'A', messages: [], createdAt: Date.now() }]
    render(<WorkspaceSidebar sessions={sessions} onTogglePin={onTogglePin} />)
    fireEvent.click(screen.getByTestId('pin-btn'))
    expect(pinned).toBe(true)
  })
})
