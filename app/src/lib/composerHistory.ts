/**
 * MiMi Nox — Composer History (P2-6)
 *
 * Terminal-artige Recall-Historie für den Composer:
 *  - ↑/↓ blättert durch bereits gesendete Nachrichten
 *  - Queue-Editing: mehrere Nachrichten können vorbereitet werden
 *    (Enter sendet die aktuelle; Alt+Enter o.ä. stellt sie in die Queue)
 *
 * Reine Klasse ohne DOM-Abhängigkeit → leicht testbar.
 */

export interface QueueEntry {
  text: string
  attachments?: unknown[]
}

export class ComposerHistory {
  private entries: string[] = []
  private cursor = -1 // -1 = neutral (leerer Composer)
  private queue: QueueEntry[] = []
  private draft = ''

  /** Neue gesendete Nachricht in die History aufnehmen (dedup: keine direkten Duplikate). */
  add(text: string): void {
    const trimmed = text.trim()
    if (!trimmed) return
    if (this.entries[this.entries.length - 1] !== trimmed) {
      this.entries.push(trimmed)
    }
    // Nach dem Senden: Cursor zurücksetzen auf neutral
    this.cursor = -1
    this.draft = ''
  }

  /** ↑ — ältere Nachricht; liefert die Nachricht oder null am Anfang. */
  prev(): string | null {
    if (this.entries.length === 0) return null
    if (this.cursor === -1 && this.draft) {
      // Draft als Basis merken (nur beim ersten ↑)
      this.draft = this.draft
    }
    this.cursor = this.cursor === -1 ? this.entries.length - 1 : Math.max(0, this.cursor - 1)
    return this.entries[this.cursor] ?? null
  }

  /** ↓ — neuere Nachricht; null wenn am Ende (neutral). */
  next(): string | null {
    if (this.cursor === -1) return null
    this.cursor += 1
    if (this.cursor >= this.entries.length) {
      this.cursor = -1
      return this.draft || null
    }
    return this.entries[this.cursor] ?? null
  }

  /** Aktueller History-Index (für Anzeige "3/5"). */
  index(): { pos: number; total: number } {
    const total = this.entries.length
    const pos = this.cursor === -1 ? 0 : this.cursor + 1
    return { pos, total }
  }

  /** Cursor auf neutral setzen (Escape). */
  reset(): void {
    this.cursor = -1
    this.draft = ''
  }

  /** Draft setzen (aktueller Composer-Inhalt, für Recall-Basis). */
  setDraft(text: string): void {
    this.draft = text
  }

  /** Aktuelle Nachricht in die Queue stellen (Queue-Editing). */
  enqueue(text: string, attachments?: unknown[]): void {
    if (text.trim()) {
      this.queue.push({ text: text.trim(), attachments })
    }
  }

  /** Nächste Queue-Nachricht nehmen; null wenn leer. */
  dequeue(): QueueEntry | null {
    if (this.queue.length === 0) return null
    return this.queue.shift()!
  }

  /** Queue-Inhalt (für Anzeige "2 in Queue"). */
  queueCount(): number {
    return this.queue.length
  }

  /** Queue leeren. */
  clearQueue(): void {
    this.queue = []
  }
}
