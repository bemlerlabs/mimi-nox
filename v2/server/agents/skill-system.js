/**
 * ◑ MiMiNox v2 — RPG-Skill-System
 * server/agents/skill-system.js
 *
 * Das Herz der Agent-Evolution. Jeder Agent hat 8 Skills (0-100)
 * die durch Aufgaben, QA-Feedback und Tool-Nutzung wachsen.
 *
 * Skills:
 *   ⚔️ codeQuality    — Tasks ohne QA-Rejection
 *   🛡️ bugDetection   — QA-Feedback → Fix → Re-Approve
 *   🧠 architecture   — SOP-Konsultation
 *   🔍 research       — web_search / browser_go
 *   ⚡ speed          — Inferenzzeit unter Median
 *   🔧 toolMastery    — Neue Tools / eigene Skills generiert
 *   💬 communication  — Klare Inter-Agent-Nachrichten
 *   🧪 testing        — Tests geschrieben / grün
 *
 * XP/Leveling:
 *   - XP = Summe aller Skill-Gewinne * 10
 *   - Level-Up Threshold = level * 1000
 *   - Skill-Cap: 100
 */

// Tools that count towards specific skills
const RESEARCH_TOOLS = ['web_search', 'browser_go', 'file_search'];

const DEFAULT_SKILLS = {
  codeQuality: 50,
  bugDetection: 30,
  architecture: 25,
  research: 40,
  speed: 45,
  toolMastery: 35,
  communication: 30,
  testing: 40,
};

export class SkillSystem {
  /**
   * @param {import('../state/store.js').StateStore} store
   */
  constructor(store) {
    this._store = store;
    this._initSchema();
  }

  // ── Schema ────────────────────────────────────────────────────────

  _initSchema() {
    this._store._db.exec(`
      CREATE TABLE IF NOT EXISTS agent_skills (
        agent_id TEXT PRIMARY KEY,
        level INTEGER NOT NULL DEFAULT 1,
        xp INTEGER NOT NULL DEFAULT 0,
        code_quality INTEGER NOT NULL DEFAULT 50,
        bug_detection INTEGER NOT NULL DEFAULT 30,
        architecture INTEGER NOT NULL DEFAULT 25,
        research INTEGER NOT NULL DEFAULT 40,
        speed INTEGER NOT NULL DEFAULT 45,
        tool_mastery INTEGER NOT NULL DEFAULT 35,
        communication INTEGER NOT NULL DEFAULT 30,
        testing INTEGER NOT NULL DEFAULT 40,
        tools_used TEXT NOT NULL DEFAULT '[]',
        updated_at TEXT DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS skill_learnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT NOT NULL,
        skill TEXT NOT NULL,
        delta INTEGER NOT NULL,
        reason TEXT NOT NULL,
        timestamp TEXT DEFAULT (datetime('now'))
      );
    `);
  }

  // ── Profile Management ────────────────────────────────────────────

  /**
   * Initialize a skill profile for an agent.
   * @param {string} agentId
   * @param {Object} initialSkills - { codeQuality, bugDetection, ... }
   */
  initProfile(agentId, initialSkills) {
    const skills = { ...DEFAULT_SKILLS, ...(initialSkills || {}) };
    this._store._db.prepare(`
      INSERT OR REPLACE INTO agent_skills
        (agent_id, code_quality, bug_detection, architecture, research, speed, tool_mastery, communication, testing)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      agentId,
      skills.codeQuality,
      skills.bugDetection,
      skills.architecture,
      skills.research,
      skills.speed,
      skills.toolMastery,
      skills.communication,
      skills.testing,
    );
  }

  /**
   * Get the full skill profile for an agent.
   * @param {string} agentId
   * @returns {{ skills, level, xp, recentLearnings }|null}
   */
  getProfile(agentId) {
    const row = this._store._db.prepare(
      `SELECT * FROM agent_skills WHERE agent_id = ?`
    ).get(agentId);

    if (!row) return null;

    const learnings = this._store._db.prepare(
      `SELECT * FROM skill_learnings WHERE agent_id = ? ORDER BY timestamp DESC LIMIT 10`
    ).all(agentId);

    return {
      agentId,
      level: row.level,
      xp: row.xp,
      skills: {
        codeQuality: row.code_quality,
        bugDetection: row.bug_detection,
        architecture: row.architecture,
        research: row.research,
        speed: row.speed,
        toolMastery: row.tool_mastery,
        communication: row.communication,
        testing: row.testing,
      },
      recentLearnings: learnings.map(l => ({
        skill: l.skill,
        delta: l.delta,
        reason: l.reason,
        timestamp: l.timestamp,
      })),
    };
  }

  // ── XP Events ─────────────────────────────────────────────────────

  /**
   * Called when a task is completed.
   * @param {string} agentId
   * @param {{ rejected: boolean }} opts
   */
  onTaskCompleted(agentId, { rejected = false } = {}) {
    if (!rejected) {
      this.addSkillXP(agentId, 'codeQuality', 3);
      this._logLearning(agentId, 'codeQuality', 3, 'Task ohne QA-Rejection abgeschlossen');
    }
    this.addXP(agentId, 30);
  }

  /**
   * Called when a QA rejection is fixed and re-approved.
   * @param {string} agentId
   */
  onQARejectionFixed(agentId) {
    this.addSkillXP(agentId, 'bugDetection', 8);
    this._logLearning(agentId, 'bugDetection', 8, 'QA-Rejection gefixt und re-approved');
    this.addXP(agentId, 50);
  }

  /**
   * Called when a tool is used.
   * @param {string} agentId
   * @param {string} toolName
   */
  onToolUsed(agentId, toolName) {
    // Research tools boost research skill
    if (RESEARCH_TOOLS.includes(toolName)) {
      this.addSkillXP(agentId, 'research', 5);
      this._logLearning(agentId, 'research', 5, `Tool '${toolName}' für Recherche genutzt`);
    }

    // First-time tool usage boosts tool mastery
    const row = this._store._db.prepare(
      `SELECT tools_used FROM agent_skills WHERE agent_id = ?`
    ).get(agentId);

    if (row) {
      const usedTools = JSON.parse(row.tools_used);
      if (!usedTools.includes(toolName)) {
        usedTools.push(toolName);
        this._store._db.prepare(
          `UPDATE agent_skills SET tools_used = ? WHERE agent_id = ?`
        ).run(JSON.stringify(usedTools), agentId);

        this.addSkillXP(agentId, 'toolMastery', 4);
        this._logLearning(agentId, 'toolMastery', 4, `Neues Tool '${toolName}' erstmalig genutzt`);
      }
    }

    this.addXP(agentId, 10);
  }

  /**
   * Called when SOP is consulted.
   * @param {string} agentId
   */
  onSOPConsulted(agentId) {
    this.addSkillXP(agentId, 'architecture', 2);
    this._logLearning(agentId, 'architecture', 2, 'SOP konsultiert');
    this.addXP(agentId, 15);
  }

  /**
   * Called when tests are written and pass.
   * @param {string} agentId
   */
  onTestsWritten(agentId) {
    this.addSkillXP(agentId, 'testing', 5);
    this._logLearning(agentId, 'testing', 5, 'Tests geschrieben und bestanden');
    this.addXP(agentId, 25);
  }

  // ── Low-level XP Management ───────────────────────────────────────

  /**
   * Add XP to a specific skill (capped at 100).
   * @param {string} agentId
   * @param {string} skillName - camelCase skill name
   * @param {number} amount
   */
  addSkillXP(agentId, skillName, amount) {
    const column = this._skillColumn(skillName);
    this._store._db.prepare(
      `UPDATE agent_skills SET ${column} = MIN(100, ${column} + ?) WHERE agent_id = ?`
    ).run(amount, agentId);
  }

  /**
   * Add global XP and check for level-up.
   * @param {string} agentId
   * @param {number} amount
   */
  addXP(agentId, amount) {
    this._store._db.prepare(
      `UPDATE agent_skills SET xp = xp + ? WHERE agent_id = ?`
    ).run(amount, agentId);

    // Check level-up
    const row = this._store._db.prepare(
      `SELECT level, xp FROM agent_skills WHERE agent_id = ?`
    ).get(agentId);

    if (row) {
      const threshold = row.level * 1000;
      if (row.xp >= threshold) {
        const newLevel = row.level + 1;
        this._store._db.prepare(
          `UPDATE agent_skills SET level = ?, xp = xp - ? WHERE agent_id = ?`
        ).run(newLevel, threshold, agentId);

        this._store._notify({
          type: 'agent_level_up',
          agentId,
          newLevel,
          previousLevel: row.level,
        });
      }
    }
  }

  // ── Helpers (test support) ────────────────────────────────────────

  /** @internal - for testing */
  _setXP(agentId, xp) {
    this._store._db.prepare(
      `UPDATE agent_skills SET xp = ? WHERE agent_id = ?`
    ).run(xp, agentId);
  }

  /** @internal - for testing */
  _setLevel(agentId, level) {
    this._store._db.prepare(
      `UPDATE agent_skills SET level = ? WHERE agent_id = ?`
    ).run(level, agentId);
  }

  /** @private */
  _logLearning(agentId, skill, delta, reason) {
    this._store._db.prepare(
      `INSERT INTO skill_learnings (agent_id, skill, delta, reason) VALUES (?, ?, ?, ?)`
    ).run(agentId, skill, delta, reason);
  }

  /** Convert camelCase skill name to snake_case column name */
  _skillColumn(name) {
    return name.replace(/([A-Z])/g, '_$1').toLowerCase();
  }

  // ── Analysis ──────────────────────────────────────────────────────

  /**
   * Get the weakest skill for an agent (for focus training).
   * @param {string} agentId
   * @returns {{ skill: string, value: number }|null}
   */
  getWeakestSkill(agentId) {
    const profile = this.getProfile(agentId);
    if (!profile) return null;

    let weakest = { skill: '', value: 101 };
    for (const [skill, value] of Object.entries(profile.skills)) {
      if (value < weakest.value) {
        weakest = { skill, value };
      }
    }
    return weakest;
  }
}
