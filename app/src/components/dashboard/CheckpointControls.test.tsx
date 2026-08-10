import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CheckpointControls from './CheckpointControls'
import type { ChatCheckpoint } from '@/lib/checkpoints'

function makeCp(label: string): ChatCheckpoint {
  return {
    id: `cp-${label}`,
    label,
    createdAt: Date.now(),
    messages: [],
  }
}

describe('CheckpointControls', () => {
  it('renders the snapshot button', () => {
    render(<CheckpointControls checkpoints={[]} onCreate={vi.fn()} onRollback={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.getByTitle('Snapshot sichern')).toBeTruthy()
  })

  it('fires onCreate when the snapshot button is clicked', () => {
    const onCreate = vi.fn()
    render(<CheckpointControls checkpoints={[]} onCreate={onCreate} onRollback={vi.fn()} onDelete={vi.fn()} />)
    fireEvent.click(screen.getByTitle('Snapshot sichern'))
    expect(onCreate).toHaveBeenCalled()
  })

  it('lists existing checkpoints', () => {
    const { container } = render(
      <CheckpointControls checkpoints={[makeCp('a'), makeCp('b')]} onCreate={vi.fn()} onRollback={vi.fn()} onDelete={vi.fn()} />,
    )
    expect(container.querySelectorAll('[title="Rollback zu a"]').length).toBe(1)
    expect(container.querySelectorAll('[title="Rollback zu b"]').length).toBe(1)
  })

  it('fires onRollback with the checkpoint id', () => {
    const onRollback = vi.fn()
    render(<CheckpointControls checkpoints={[makeCp('a')]} onCreate={vi.fn()} onRollback={onRollback} onDelete={vi.fn()} />)
    fireEvent.click(screen.getByTitle('Rollback zu a'))
    expect(onRollback).toHaveBeenCalledWith('cp-a')
  })

  it('fires onDelete for a checkpoint', () => {
    const onDelete = vi.fn()
    render(<CheckpointControls checkpoints={[makeCp('a')]} onCreate={vi.fn()} onRollback={vi.fn()} onDelete={onDelete} />)
    fireEvent.click(screen.getByTitle('Checkpoint a löschen'))
    expect(onDelete).toHaveBeenCalledWith('cp-a')
  })
})
