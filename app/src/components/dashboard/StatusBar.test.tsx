import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import StatusBar from '@/components/dashboard/StatusBar'
import type { ChatMessage } from '@/types'

function makeMsgs(role: 'user' | 'assistant', text: string): ChatMessage[] {
  return [{ id: `${role}-1`, role, content: text, timestamp: Date.now() }]
}

describe('StatusBar', () => {
  it('renders a percent meter from the message estimate', () => {
    const msgs = makeMsgs('user', 'x'.repeat(4200)) // ~1000 tok
    render(<StatusBar messages={msgs} yolo={false} onYoloChange={vi.fn()} />)
    // Prozentwert sichtbar (1000/8192 ≈ 12%)
    expect(screen.getByText(/12%/)).toBeTruthy()
    expect(screen.getByText(/tok/)).toBeTruthy()
  })

  it('shows a compaction warning at high usage', () => {
    const msgs = makeMsgs('user', 'x'.repeat(70000)) // ~16k tok > 75%
    render(<StatusBar messages={msgs} yolo={false} onYoloChange={vi.fn()} />)
    expect(screen.getByText(/kompakt empfohlen/)).toBeTruthy()
  })

  it('toggles YOLO via the button', () => {
    const onYoloChange = vi.fn()
    render(<StatusBar messages={[]} yolo={false} onYoloChange={onYoloChange} />)
    fireEvent.click(screen.getByText('YOLO'))
    expect(onYoloChange).toHaveBeenCalledWith(true)
  })

  it('shows the breakdown when expanded', () => {
    const msgs = makeMsgs('assistant', 'a'.repeat(420)) // ~100 tok
    render(<StatusBar messages={msgs} yolo={false} onYoloChange={vi.fn()} />)
    fireEvent.click(screen.getByTitle(/Token-Breakdown/))
    expect(screen.getByText(/U \d|A \d|S \d/)).toBeTruthy()
  })
})
