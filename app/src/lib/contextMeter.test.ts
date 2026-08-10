import { describe, it, expect } from 'vitest'

import {
  estimateTokens,
  estimateContextUsage,
  CONTEXT_WINDOW_TOKENS,
} from '@/lib/contextMeter'

describe('contextMeter token estimation', () => {
  it('estimates tokens from text length (chars -> token ratio)', () => {
    // gemma: ~4.2 chars/token, konservative Schätzung
    const text = 'a'.repeat(420)
    const tokens = estimateTokens(text)
    expect(tokens).toBeGreaterThanOrEqual(90)
    expect(tokens).toBeLessThanOrEqual(110)
  })

  it('returns 0 tokens for empty text', () => {
    expect(estimateTokens('')).toBe(0)
    expect(estimateTokens('   ')).toBe(0)
  })

  it('counts system messages toward the total', () => {
    const messages = [
      { role: 'system' as const, content: 'sys'.repeat(100) },
      { role: 'user' as const, content: 'user'.repeat(100) },
      { role: 'assistant' as const, content: 'assistant'.repeat(100) },
    ]
    const usage = estimateContextUsage(messages, 2000)
    expect(usage.tokens.system).toBeGreaterThan(0)
    expect(usage.tokens.user).toBeGreaterThan(0)
    expect(usage.tokens.assistant).toBeGreaterThan(0)
    expect(usage.tokens.total).toBe(usage.tokens.system + usage.tokens.user + usage.tokens.assistant)
  })

  it('computes percent-full clamped to 100', () => {
    const huge = [{ role: 'user' as const, content: 'x'.repeat(500000) }]
    const usage = estimateContextUsage(huge, CONTEXT_WINDOW_TOKENS)
    expect(usage.percent).toBe(100)
    expect(usage.remaining).toBe(0)
  })

  it('returns zero usage for no messages', () => {
    const usage = estimateContextUsage([], CONTEXT_WINDOW_TOKENS)
    expect(usage.tokens.total).toBe(0)
    expect(usage.percent).toBe(0)
    expect(usage.remaining).toBe(CONTEXT_WINDOW_TOKENS)
  })

  it('exposes a sensible default context window', () => {
    expect(CONTEXT_WINDOW_TOKENS).toBeGreaterThan(0)
    expect(CONTEXT_WINDOW_TOKENS).toBeGreaterThan(1000)
  })

  it('breaks down tokens by role for the status bar', () => {
    const messages = [
      { role: 'user' as const, content: 'user'.repeat(50) },
      { role: 'assistant' as const, content: 'assistant'.repeat(50) },
    ]
    const usage = estimateContextUsage(messages, 4096)
    // Breakdown-Felder existieren und summieren korrekt
    expect(usage.tokens.user).toBeGreaterThan(0)
    expect(usage.tokens.assistant).toBeGreaterThan(0)
    expect(usage.tokens.system).toBe(0)
    expect(usage.percent).toBeGreaterThan(0)
    expect(usage.percent).toBeLessThanOrEqual(100)
  })
})
