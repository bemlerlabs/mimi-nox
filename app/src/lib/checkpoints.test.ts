import { describe, it, expect } from 'vitest'
import {
  createCheckpoint,
  rollbackToCheckpoint,
  listCheckpoints,
  deleteCheckpoint,
} from '@/lib/checkpoints'
import type { ChatMessage } from '@/types'

function makeMsgs(n: number): ChatMessage[] {
  return Array.from({ length: n }, (_, i) => ({
    id: `m-${i}`,
    role: 'user',
    content: `msg ${i}`,
    timestamp: Date.now() + i,
  }))
}

describe('checkpoints', () => {
  it('creates a snapshot of the messages', () => {
    const msgs = makeMsgs(3)
    const cp = createCheckpoint(msgs, 'vor Refactor')
    expect(cp.messages).toEqual(msgs)
    expect(cp.label).toBe('vor Refactor')
    expect(cp.id).toBeTruthy()
    expect(cp.createdAt).toBeGreaterThan(0)
  })

  it('deep-copies so later mutations do not affect the snapshot', () => {
    const msgs = makeMsgs(2)
    const cp = createCheckpoint(msgs, 'snapshot')
    msgs[0]!.content = 'mutiert'
    expect(cp.messages[0]!.content).toBe('msg 0')
  })

  it('rolls back to a checkpoint by id', () => {
    const msgs = makeMsgs(5)
    const cp = createCheckpoint(msgs, 'punkt 2')
    const rolled = rollbackToCheckpoint(cp.id, [cp])
    expect(rolled).toEqual(cp.messages)
    expect(rolled![0]!.content).toBe('msg 0')
  })

  it('returns null when the checkpoint id is unknown', () => {
    const rolled = rollbackToCheckpoint('nope', [])
    expect(rolled).toBeNull()
  })

  it('lists checkpoints newest-first', () => {
    const msgs = makeMsgs(1)
    const a = createCheckpoint(msgs, 'a')
    const b = createCheckpoint(msgs, 'b')
    const list = listCheckpoints([b, a])
    expect(list[0]!.label).toBe('b')
    expect(list).toHaveLength(2)
  })

  it('deletes a checkpoint by id', () => {
    const msgs = makeMsgs(1)
    const cp = createCheckpoint(msgs, 'weg')
    const rest = deleteCheckpoint([cp], cp.id)
    expect(rest).toHaveLength(0)
  })
})
