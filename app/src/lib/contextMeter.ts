/**
 * MiMi Nox — Context Meter (P2-5)
 *
 * Schätzt die Kontext-Belegung einer Session deterministisch aus den
 * Nachrichten. Offline-first: keine Backend-Token-Usage nötig, die Schätzung
 * ist eine reine Funktion über die Messages.
 *
 * gemma-Modelle: ~4.2 Zeichen pro Token (konservativ, inkl. Whitespace).
 * Context-Fenster: 8192 Token (gemma4:12b Default), überschreibbar.
 */

/** Charakter-pro-Token-Ratio für gemma (konservativ) */
export const CHARS_PER_TOKEN = 4.2

/** Default Context-Fenster in Token (gemma4:12b) */
export const CONTEXT_WINDOW_TOKENS = 8192

export interface TokenBreakdown {
  system: number
  user: number
  assistant: number
  total: number
}

export interface ContextUsage {
  tokens: TokenBreakdown
  percent: number // 0..100, geklemmt
  remaining: number // verbleibende Token
  window: number
}

/** Schätzt die Token-Anzahl eines Texts. */
export function estimateTokens(text: string): number {
  if (!text) return 0
  const trimmed = text.trim()
  if (!trimmed) return 0
  // gemma-Tokenizer ~4.2 chars/token; Konservativ aufrunden für Sicherheitsmarge
  return Math.ceil(trimmed.length / CHARS_PER_TOKEN)
}

/** Schätzt die Kontext-Belegung über die Messages einer Session. */
export function estimateContextUsage(
  messages: Array<{ role: string; content: string }>,
  window = CONTEXT_WINDOW_TOKENS,
): ContextUsage {
  let system = 0
  let user = 0
  let assistant = 0

  for (const msg of messages || []) {
    const tokens = estimateTokens(msg.content || '')
    switch (msg.role) {
      case 'system':
        system += tokens
        break
      case 'user':
        user += tokens
        break
      case 'assistant':
        assistant += tokens
        break
      default:
        user += tokens // unbekannte Rolle → user-Nachricht (sicher)
    }
  }

  const total = system + user + assistant
  const percent = window > 0 ? Math.min(100, Math.round((total / window) * 100)) : 100
  const remaining = Math.max(0, window - total)

  return {
    tokens: { system, user, assistant, total },
    percent,
    remaining,
    window,
  }
}

/** Kuratierte Formatierung der Prozentanzeige (Status-Bar). */
export function formatPercent(percent: number): string {
  return `${percent}%`
}

/** Warnschwelle: ab dieser Belegung wird der Meter rot/„compact empfohlen". */
export const WARN_THRESHOLD = 0.75
