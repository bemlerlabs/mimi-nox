/**
 * ◑ MiMiNox v2 — Event-Log
 * server/transparency/event-log.js
 *
 * Zentrales Event-Log für alle Firmen-Aktivitäten.
 * Persistiert in SQLite für Audit-Trail.
 *
 * T-17: tool_name, args (JSON), result werden als eigene Felder gespeichert
 * für bessere Filterbarkeit und Dashboard-Sichtbarkeit.
 *
 * Event-Typen:
 *   - thinking:   Agent denkt (<|think|>)
 *   - answer:     Agent-Antwort
 *   - tool_call:  Agent nutzt Tool
 *   - chat:       Agent-zu-Agent Nachricht
 *   - error:      Fehler
 *   - level_up:   Skill Level-Up
 */

export class EventLog {
  /**
   * @param {import('../state/store.js').StateStore} store
   */
  constructor(store) {
    this._store = store;
    this._subscribers = [];
    this._initSchema();
  }

  _initSchema() {
    this._store._db.exec(`
      CREATE TABLE IF NOT EXISTS event_log (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        type      TEXT    NOT NULL,
        agent_id  TEXT,
        tool_name TEXT,
        args      TEXT,
        result    TEXT,
        data      TEXT    NOT NULL DEFAULT '{}',
        timestamp TEXT    DEFAULT (datetime('now'))
      );
    `);

    // T-17: Fehlende Spalten ergänzen (für bestehende DBs ohne Migration-Stress)
    for (const col of [
      "ALTER TABLE event_log ADD COLUMN tool_name TEXT",
      "ALTER TABLE event_log ADD COLUMN args TEXT",
      "ALTER TABLE event_log ADD COLUMN result TEXT",
    ]) {
      try { this._store._db.exec(col); } catch { /* Spalte existiert bereits */ }
    }
  }

  /**
   * Add an event to the log.
   * T-17: toolName, args, result werden als erste-Klasse-Felder gespeichert.
   * @param {Object} event - { type, agentId, toolName?, args?, result?, ...rest }
   */
  addEvent(event) {
    const { type, agentId, toolName, args, result, ...rest } = event;

    this._store._db.prepare(`
      INSERT INTO event_log (type, agent_id, tool_name, args, result, data)
      VALUES (?, ?, ?, ?, ?, ?)
    `).run(
      type,
      agentId  || null,
      toolName || null,
      args     != null ? JSON.stringify(args) : null,
      result   != null ? String(result)       : null,
      JSON.stringify(rest),
    );

    const entry = {
      type,
      agent_id:  agentId,
      tool_name: toolName,
      args,
      result,
      ...rest,
    };
    for (const sub of this._subscribers) {
      try { sub(entry); } catch { /* subscriber crash safe */ }
    }
  }

  /**
   * Get events with optional filters.
   * @param {{ agentId?: string, type?: string, limit?: number }} [opts]
   * @returns {Object[]}
   */
  getEvents(opts = {}) {
    let sql = `SELECT * FROM event_log WHERE 1=1`;
    const params = [];

    if (opts.agentId) {
      sql += ` AND agent_id = ?`;
      params.push(opts.agentId);
    }
    if (opts.type) {
      sql += ` AND type = ?`;
      params.push(opts.type);
    }

    sql += ` ORDER BY id ASC LIMIT ?`;
    params.push(opts.limit || 500);

    const rows = this._store._db.prepare(sql).all(...params);
    return rows.map(r => ({
      id:        r.id,
      type:      r.type,
      agent_id:  r.agent_id,
      tool_name: r.tool_name  || undefined,
      args:      r.args       ? JSON.parse(r.args) : undefined,
      result:    r.result     ?? undefined,
      ...JSON.parse(r.data),
      timestamp: r.timestamp,
    }));
  }

  /**
   * Subscribe to new events.
   * @param {(event: Object) => void} callback
   * @returns {() => void} unsubscribe
   */
  onEvent(callback) {
    this._subscribers.push(callback);
    return () => {
      this._subscribers = this._subscribers.filter(s => s !== callback);
    };
  }
}
