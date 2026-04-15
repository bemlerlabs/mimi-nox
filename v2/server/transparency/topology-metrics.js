/**
 * ◑ MiMiNox v2 — Topologie-Metriken
 * server/transparency/topology-metrics.js
 *
 * TF (Thought Flows) und KC (Knowledge Connections) Counter.
 * Metriken für das Firmengehirn-Dashboard.
 *
 * TF: Wie viele "Denk-Zyklen" hat ein Agent durchlaufen?
 * KC: Wie viele Wissensgraph-Kanten hat ein Agent erzeugt?
 */

export class TopologyMetrics {
  /**
   * @param {import('../state/store.js').StateStore} store
   */
  constructor(store) {
    this._store = store;
    this._initSchema();
  }

  _initSchema() {
    this._store._db.exec(`
      CREATE TABLE IF NOT EXISTS topology_metrics (
        agent_id TEXT NOT NULL,
        metric TEXT NOT NULL,
        value INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (agent_id, metric)
      );

      CREATE TABLE IF NOT EXISTS topology_connections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT NOT NULL,
        from_node TEXT NOT NULL,
        to_node TEXT NOT NULL,
        timestamp TEXT DEFAULT (datetime('now'))
      );
    `);
  }

  /**
   * Record a thought flow for an agent.
   * @param {string} agentId
   */
  recordThoughtFlow(agentId) {
    this._upsertMetric(agentId, 'tf', 1);
  }

  /**
   * Record a knowledge connection.
   * @param {string} agentId
   * @param {string} fromNode
   * @param {string} toNode
   */
  recordConnection(agentId, fromNode, toNode) {
    this._store._db.prepare(
      `INSERT INTO topology_connections (agent_id, from_node, to_node) VALUES (?, ?, ?)`
    ).run(agentId, fromNode, toNode);

    this._upsertMetric(agentId, 'kc', 1);
  }

  /**
   * Get Thought Flow count for an agent.
   * @param {string} agentId
   * @returns {number}
   */
  getTF(agentId) {
    return this._getMetric(agentId, 'tf');
  }

  /**
   * Get Knowledge Connection count for an agent.
   * @param {string} agentId
   * @returns {number}
   */
  getKC(agentId) {
    return this._getMetric(agentId, 'kc');
  }

  /**
   * Get a snapshot of all agents' metrics for the dashboard.
   * @returns {Object} - { agentId: { tf, kc }, ... }
   */
  getSnapshot() {
    const rows = this._store._db.prepare(
      `SELECT agent_id, metric, value FROM topology_metrics ORDER BY agent_id`
    ).all();

    const result = {};
    for (const row of rows) {
      if (!result[row.agent_id]) result[row.agent_id] = { tf: 0, kc: 0 };
      result[row.agent_id][row.metric] = row.value;
    }
    return result;
  }

  // ── Helpers ───────────────────────────────────────────────────────

  /** @private */
  _upsertMetric(agentId, metric, delta) {
    this._store._db.prepare(`
      INSERT INTO topology_metrics (agent_id, metric, value) VALUES (?, ?, ?)
      ON CONFLICT(agent_id, metric) DO UPDATE SET value = value + ?
    `).run(agentId, metric, delta, delta);
  }

  /** @private */
  _getMetric(agentId, metric) {
    const row = this._store._db.prepare(
      `SELECT value FROM topology_metrics WHERE agent_id = ? AND metric = ?`
    ).get(agentId, metric);
    return row?.value || 0;
  }

  /**
   * Record a connection AND grant XP to the agent's research skill.
   * Used when knowledge graph connections should feed back into skill growth.
   * @param {string} agentId
   * @param {string} fromNode
   * @param {string} toNode
   * @param {import('../agents/skill-system.js').SkillSystem} skills
   */
  recordConnectionWithSkills(agentId, fromNode, toNode, skills) {
    this.recordConnection(agentId, fromNode, toNode);
    skills.addSkillXP(agentId, 'research', 5);
    skills.addXP(agentId, 15);
  }
}
