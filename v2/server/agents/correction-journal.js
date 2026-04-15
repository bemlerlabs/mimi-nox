/**
 * ◑ MiMiNox v2 — CorrectionJournal (Hermes-Pattern)
 * server/agents/correction-journal.js
 *
 * Das Langzeitgedächtnis der Agenten. Speichert Fehler und deren Fixes,
 * um aus vergangenen Fehlern zu lernen (Hermes-Pattern).
 *
 * Features:
 *   - addCorrection: Fehler + Fix speichern
 *   - getRecent: Letzte N Korrekturen abrufen
 *   - getContextPrompt: System-Prompt-Snippet für LLM-Injection
 *
 * Design: SQLite-basiert für Persistenz über Sessions hinweg.
 * Der Context-Prompt wird dem Agent-System-Prompt vor jedem LLM-Call
 * angefügt, damit er aus eigenen Fehlern lernt.
 */

export class CorrectionJournal {
  /**
   * @param {import('../state/store.js').StateStore} store
   */
  constructor(store) {
    this._store = store;
    this._initSchema();
  }

  _initSchema() {
    this._store._db.exec(`
      CREATE TABLE IF NOT EXISTS correction_journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT NOT NULL,
        error TEXT NOT NULL,
        fix TEXT NOT NULL,
        ticket_id INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
      );
    `);
  }

  /**
   * Log a correction (error → fix pair).
   * @param {{ agentId: string, error: string, fix: string, ticketId?: number }} entry
   */
  addCorrection({ agentId, error, fix, ticketId = null }) {
    this._store._db.prepare(
      `INSERT INTO correction_journal (agent_id, error, fix, ticket_id) VALUES (?, ?, ?, ?)`
    ).run(agentId, error, fix, ticketId);
  }

  /**
   * Get recent corrections for an agent (newest first).
   * @param {string} agentId
   * @param {number} [limit=5]
   * @returns {Object[]}
   */
  getRecent(agentId, limit = 5) {
    return this._store._db.prepare(
      `SELECT * FROM correction_journal WHERE agent_id = ? ORDER BY id DESC LIMIT ?`
    ).all(agentId, limit);
  }

  /**
   * Generate a context prompt snippet from recent corrections.
   * This gets injected into the agent's system prompt before each LLM call.
   * @param {string} agentId
   * @param {number} [limit=3]
   * @returns {string}
   */
  getContextPrompt(agentId, limit = 3) {
    const corrections = this.getRecent(agentId, limit);
    if (corrections.length === 0) return '';

    const entries = corrections.map((c, i) =>
      `${i + 1}. Fehler: ${c.error}\n   Fix: ${c.fix}`
    ).join('\n');

    return `\n--- Gelernte Lektionen (Correction Journal) ---\nAus deinen vergangenen Fehlern:\n${entries}\nWende diese Lektionen auf zukünftige Aufgaben an.\n---`;
  }
}
