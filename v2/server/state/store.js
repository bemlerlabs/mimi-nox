/**
 * ◑ MiMiNox v2 — SQLite State Store
 * server/state/store.js
 *
 * Persistenter Shared State für das Agenten-System.
 * Port von Python core/swarm_state.py SwarmStateStore.
 *
 * Features:
 *   - Agent CRUD (create, read, update)
 *   - Chat message persistence
 *   - Ticket/Kanban management
 *   - Pub/Sub event system (Subscriber callbacks)
 *   - Survives server restarts (SQLite file-based)
 */

import Database from 'better-sqlite3';
import { encryptField, safeDecrypt, shouldEncrypt } from './memory-crypto.js';

export class StateStore {
  /**
   * @param {string} dbPath - Path to SQLite database file
   */
  constructor(dbPath = ':memory:') {
    this._db = new Database(dbPath);
    this._db.pragma('journal_mode = WAL');
    this._db.pragma('foreign_keys = ON');
    this._subscribers = [];
    this._initSchema();
  }

  // ── Schema ────────────────────────────────────────────────────────

  _initSchema() {
    this._db.exec(`
      CREATE TABLE IF NOT EXISTS agents (
        id TEXT PRIMARY KEY,
        role TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'spawned',
        result TEXT,
        system_prompt TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        "from" TEXT NOT NULL,
        "to" TEXT NOT NULL,
        content TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'message',
        timestamp TEXT DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'backlog',
        assignee TEXT,
        created_by TEXT,
        description TEXT,
        result TEXT,
        was_rejected INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS personal_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        category TEXT DEFAULT 'allgemein',
        created_at TEXT DEFAULT (datetime('now'))
      );
    `);
  }

  // ── Agent CRUD ────────────────────────────────────────────────────

  /**
   * Create a new agent.
   * @param {{ id: string, role: string, status?: string, systemPrompt?: string }} data
   */
  createAgent({ id, role, status = 'spawned', systemPrompt = '' }) {
    this._db.prepare(
      `INSERT INTO agents (id, role, status, system_prompt) VALUES (?, ?, ?, ?)`
    ).run(id, role, status, systemPrompt);

    this._notify({ type: 'agent_created', agentId: id, role, status });
  }

  /**
   * Get a single agent by ID.
   * @param {string} id
   * @returns {Object|undefined}
   */
  getAgent(id) {
    return this._db.prepare(`SELECT * FROM agents WHERE id = ?`).get(id);
  }

  /**
   * Get all agents.
   * @returns {Object[]}
   */
  getAllAgents() {
    return this._db.prepare(`SELECT * FROM agents ORDER BY created_at`).all();
  }

  /**
   * Update agent fields.
   * @param {string} id
   * @param {Object} updates - Fields to update (status, result, etc.)
   */
  updateAgent(id, updates) {
    const fields = Object.keys(updates);
    const sets = fields.map(f => `"${f}" = ?`).join(', ');
    const values = fields.map(f => updates[f]);

    this._db.prepare(
      `UPDATE agents SET ${sets}, updated_at = datetime('now') WHERE id = ?`
    ).run(...values, id);

    this._notify({ type: 'agent_updated', agentId: id, ...updates });
  }

  // ── Chat Messages ─────────────────────────────────────────────────

  /**
   * Add a chat message.
   * @param {{ from: string, to: string, content: string, type?: string }} msg
   */
  addChatMessage({ from, to, content, type = 'message' }) {
    this._db.prepare(
      `INSERT INTO chat_messages ("from", "to", content, type) VALUES (?, ?, ?, ?)`
    ).run(from, to, content, type);

    this._notify({ type: 'chat_message', from, to, content, messageType: type });
  }

  /**
   * Get all chat messages, chronologically.
   * @param {number} [limit=100]
   * @returns {Object[]}
   */
  getChatHistory(limit = 100) {
    return this._db.prepare(
      `SELECT * FROM chat_messages ORDER BY timestamp ASC LIMIT ?`
    ).all(limit);
  }

  // ── Tickets/Kanban ────────────────────────────────────────────────

  /**
   * Create a ticket.
   * @param {{ title: string, assignee?: string, createdBy?: string, description?: string }} data
   * @returns {number} ticket ID
   */
  createTicket({ title, assignee = null, createdBy = null, description = '' }) {
    const result = this._db.prepare(
      `INSERT INTO tickets (title, assignee, created_by, description) VALUES (?, ?, ?, ?)`
    ).run(title, assignee, createdBy, description);

    const id = result.lastInsertRowid;
    this._notify({ type: 'ticket_created', ticketId: id, title, assignee });
    return Number(id);
  }

  /**
   * Update ticket status.
   * @param {number} id
   * @param {string} status - backlog | in_progress | testing | done
   */
  updateTicketStatus(id, status) {
    const VALID = ['backlog', 'in_progress', 'testing', 'done'];
    if (!VALID.includes(status)) {
      throw new Error(`Ungültiger Ticket-Status: '${status}'. Erlaubt: ${VALID.join(', ')}`);
    }

    this._db.prepare(
      `UPDATE tickets SET status = ?, updated_at = datetime('now') WHERE id = ?`
    ).run(status, id);

    this._notify({ type: 'ticket_moved', ticketId: id, status });
  }

  /**
   * Mark a ticket as previously rejected (für T-04 Skill-Semantik).
   * Ermöglicht approveWork() zu unterscheiden ob ein Fix nötig war.
   * @param {number} id
   */
  markTicketRejected(id) {
    this._db.prepare(
      `UPDATE tickets SET was_rejected = 1, updated_at = datetime('now') WHERE id = ?`
    ).run(id);
    this._notify({ type: 'ticket_rejected', ticketId: id });
  }

  /**
   * Get all tickets.
   * @returns {Object[]}
   */
  getTickets() {
    return this._db.prepare(`SELECT * FROM tickets ORDER BY created_at`).all();
  }

  // ── Pub/Sub ───────────────────────────────────────────────────────

  /**
   * Subscribe to state events.
   * @param {(event: Object) => void} callback
   * @returns {() => void} unsubscribe function
   */
  subscribe(callback) {
    this._subscribers.push(callback);
    return () => {
      this._subscribers = this._subscribers.filter(s => s !== callback);
    };
  }

  /** @private */
  _notify(event) {
    for (const sub of this._subscribers) {
      try {
        sub(event);
      } catch {
        // Subscriber crash darf Store nicht crashen
      }
    }
  }

  // ── Lifecycle ─────────────────────────────────────────────────────

  close() {
    this._db?.close();
  }
  // ── Personal Memory (Feature #2) ──────────────────────────────

  /**
   * Store a personal fact.
   * @param {{ key: string, value: string, category?: string }} data
   * @returns {number} memory entry ID
   */
  addMemory({ key, value, category = 'allgemein' }) {
    // #1 Verschlüsselung: Persönliche Gesundheitsdaten (name, blutgruppe, allergie)
    // werden AES-256-GCM verschlüsselt gespeichert. System-Keys (__) im Klartext.
    const storedValue = shouldEncrypt(key) ? encryptField(value) : value;

    // UPSERT für System-Keys (__land__, __assistant_name__ etc.) — nie doppelt speichern.
    // Persönliche Fakten des Nutzers: normales INSERT (Verlauf bleibt erhalten).
    let lastInsertRowid;
    if (key.startsWith('__')) {
      const existing = this._db.prepare(
        `SELECT id FROM personal_memory WHERE key = ? LIMIT 1`
      ).get(key);
      if (existing) {
        this._db.prepare(
          `UPDATE personal_memory SET value = ?, category = ? WHERE key = ?`
        ).run(storedValue, category, key);
        lastInsertRowid = existing.id;
      } else {
        const r = this._db.prepare(
          `INSERT INTO personal_memory (key, value, category) VALUES (?, ?, ?)`
        ).run(key, storedValue, category);
        lastInsertRowid = r.lastInsertRowid;
      }
    } else {
      const r = this._db.prepare(
        `INSERT INTO personal_memory (key, value, category) VALUES (?, ?, ?)`
      ).run(key, storedValue, category);
      lastInsertRowid = r.lastInsertRowid;
    }

    this._notify({ type: 'memory_added', key, value, category }); // Notify with plaintext
    return Number(lastInsertRowid);
  }

  /**
   * Get all stored personal facts.
   * @returns {Object[]}
   */
  getAllMemories() {
    const rows = this._db.prepare(
      `SELECT * FROM personal_memory ORDER BY created_at ASC`
    ).all();
    // Decrypt values transparently — system keys and legacy plaintext pass through
    return rows.map(row => ({
      ...row,
      value: safeDecrypt(row.value),
    }));
  }

  /**
   * Delete a memory entry.
   * @param {number} id
   */
  deleteMemory(id) {
    this._db.prepare(`DELETE FROM personal_memory WHERE id = ?`).run(id);
    this._notify({ type: 'memory_deleted', id });
  }

  /**
   * Delete ALL personal memories.
   */
  clearAllMemories() {
    this._db.prepare(`DELETE FROM personal_memory`).run();
    this._notify({ type: 'memory_cleared' });
  }

  /**
   * Delete ALL chat history.
   */
  clearChatHistory() {
    this._db.prepare(`DELETE FROM chat_messages`).run();
    this._notify({ type: 'chat_cleared' });
  }
}
