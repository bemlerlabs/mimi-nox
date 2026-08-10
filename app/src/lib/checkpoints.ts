/**
 * MiMi Nox — Checkpoints & Rollback (P2-7)
 *
 * Snapshot-System für Sessions: eine Nachrichtenliste kann jederzeit als
 * Checkpoint gesichert und später per ID zurückgerollt werden.
 *
 * Reine Funktionen ohne DOM-/Store-Abhängigkeit → leicht testbar.
 */

import type { ChatMessage } from '@/types'

export interface ChatCheckpoint {
  id: string
  label: string
  createdAt: number
  messages: ChatMessage[]
}

/** Erstellt einen Checkpoint-Snapshot (deep copy) der Messages. */
export function createCheckpoint(
  messages: ChatMessage[],
  label = 'Checkpoint',
): ChatCheckpoint {
  return {
    id: crypto.randomUUID(),
    label,
    createdAt: Date.now(),
    messages: messages.map((m) => ({ ...m })),
  }
}

/** Rollt eine Session auf den Checkpoint-Zustand zurück (deep copy). */
export function rollbackToCheckpoint(
  checkpointId: string,
  checkpoints: ChatCheckpoint[],
): ChatMessage[] | null {
  const cp = checkpoints.find((c) => c.id === checkpointId)
  if (!cp) return null
  return cp.messages.map((m) => ({ ...m }))
}

/** Checkpoints absteigend nach Erstellzeit sortiert (neueste zuerst). */
export function listCheckpoints(checkpoints: ChatCheckpoint[]): ChatCheckpoint[] {
  return [...checkpoints].sort((a, b) => b.createdAt - a.createdAt)
}

/** Entfernt einen Checkpoint. */
export function deleteCheckpoint(
  checkpoints: ChatCheckpoint[],
  checkpointId: string,
): ChatCheckpoint[] {
  return checkpoints.filter((c) => c.id !== checkpointId)
}
