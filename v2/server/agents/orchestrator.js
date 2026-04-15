/**
 * ◑ MiMiNox v2 — Krisen-Orchestrator
 * server/agents/orchestrator.js
 *
 * Outdoor-Krisen-KI System. 100% offline-fähig.
 * Powered by Gemma 4 E4B über Ollama.
 *
 * Krisen-Team:
 *   Medic · Engineer · Navigator · Sensor
 *
 * Pipeline:
 *   1. User-Prompt → Crisis-Router bestimmt den Spezial-Agenten
 *   2. Prompt → Agent mit RAG-Kontext
 *   3. Agent antwortet → Skill-XP vergeben
 *
 * T-07: Injizierbarer LLM-Provider via setLLMProvider().
 * T-08: CorrectionJournal wird vor jedem LLM-Call in den System-Prompt injiziert.
 */

import { loadRole, getAllRoles } from './roles.js';
import { routeCrisisPrompt } from './crisis-router.js';
import { searchKnowledge } from '../knowledge/search.js';

// ── Crisis Agent Routing ────────────────────────────────────────────

const DELEGATION_CHAIN = [
  { id: 'medic_agent',     delegatesTo: [] },
  { id: 'engineer_agent',  delegatesTo: [] },
  { id: 'navigator_agent', delegatesTo: [] },
  { id: 'sensor_agent',    delegatesTo: [] },
];

// T-07: Tool-Set das dem LLM kommuniziert wird
const AGENT_TOOLS = ['search_knowledge', 'analyze_image'];

export class Orchestrator {
  /**
   * @param {Object} deps - All dependencies injected
   */
  constructor({ store, bus, kanban, skills, comm, journal }) {
    this._store       = store;
    this._bus         = bus;
    this._kanban      = kanban;
    this._skills      = skills;
    this._comm        = comm;
    this._journal     = journal;
    this._llm         = null;   // T-07: Optional LLM-Provider
    this._initialized = false;
    this._mode        = 'crisis';  // always crisis mode
    this.crisisTeam   = [];        // active experts
    this.powerPolicy  = 'balanced'; 
  }

  /**
   * T-5.1: Monitoring systems for resource-constrained scenarios.
   */
  async checkPowerResilience() {
    try {
      const res = await fetch('http://localhost:8000/api/system/health');
      const data = await res.json();
      if (data.airGapped && data.cpu_usage > 90) {
        this.powerPolicy = 'resilience';
      } else {
        this.powerPolicy = 'balanced';
      }
    } catch (e) {
      this.powerPolicy = 'balanced';
    }
  }

  // ── T-07: LLM-Provider (injizierbares Interface) ──────────────────

  /**
   * T-07: Setzt den LLM-Provider für echte LLM-Calls.
   *
   * Interface:
   *   provider.chat(messages: [{role, content}], tools: string[])
   *     → Promise<{ toolCall: string, args: Object }>
   *
   * @param {{ chat: Function }} provider
   */
  setLLMProvider(provider) {
    this._llm = provider;
  }

  // ── Team initialisieren ────────────────────────────────────────────

  /**
   * Initialize the crisis team: create 4 specialized agents + skill profiles.
   * Backward-compatible alias: initFirma() also calls this.
   */
  init() {
    if (this._initialized) return;

    const roles = getAllRoles();
    for (const role of roles) {
      this._store.createAgent({
        id:           role.id,
        role:         role.role,
        status:       'idle',
        systemPrompt: role.systemPrompt,
      });
      this._skills.initProfile(role.id, role.skills);
    }

    this._bus.broadcast({
      from:    'system',
      content: '🚨 MiMiNox im Krisen-Modus. Team (Medic, Engineer, Navigator, Sensor) ist bereit.',
    });

    this._initialized = true;
    this._mode        = 'crisis';
  }

  /** Backward-compatible alias */
  initFirma() { this.init(); }
  initCrisisTeam() { this.init(); }

  // ── Auftrags-Verarbeitung ─────────────────────────────────────────

  /**
   * Submit a new task to the company.
   *
   * T-07: Mit LLM-Provider → echter Ollama-Call für CEO-Entscheidung.
   * T-08: Journal-Context in System-Prompt injiziert.
   * Fallback: Direkte Delegation wie bisher (synchron, rückwärtskompatibel).
   *
   * @param {string} prompt - The user's task description
   * @param {string[]} [images] - Optional base64-encoded image chunks
   * @returns {Promise<string|Object>} taskId or error block
   */
  async submitTask(prompt, images = []) {
    await this.checkPowerResilience();

    // Energie-Sparmodus: Nur Krisen-Befehle
    const isCrisisPrompt = prompt.startsWith('/') || /hilfe|notfall|kaputt|defekt|medic|verbrenn|blut|herzstill|verletzt|ohnm|atemnot/i.test(prompt);
    if (this.powerPolicy === 'resilience' && !isCrisisPrompt) {
      return {
        content: '⚠️ ENERGIE-SPARMODUS: Nur Krisen-Befehle erlaubt. Benutze /medic, /engineer, /nav oder /sensor.',
        type: 'error'
      };
    }

    const taskId = `task_${Date.now()}`;

    // ── 1. Crisis-Router: Bestimme Ziel-Agenten ───────────────────────
    const routing = routeCrisisPrompt(prompt);
    const targetAgent = routing.agentId || 'medic_agent'; // Fallback: Medic (Krisen-First)
    const cleanPrompt = routing.sanitizedPrompt || prompt;

    // User-Nachricht ins Chat-Log
    this._bus.send({
      from:    'user',
      to:      targetAgent,
      content: cleanPrompt,
      images:  images,
      type:    'task',
    });
    this._store.updateAgent(targetAgent, { status: 'working' });

    // ── 2. RAG-Suche: Relevante Chunks laden ──────────────────────────
    let ragContext = [];
    try {
      ragContext = searchKnowledge(cleanPrompt, { limit: 4 });
    } catch (e) {
      // KB nicht verfügbar — graceful degradation
    }

    // ── 3a. Ollama verfügbar → LLM mit RAG-Kontext ────────────────────
    if (this._llm) {
      await this._delegateViaLLM(cleanPrompt, images, targetAgent, ragContext);
    } else {
      // ── 3b. OFFLINE-Fallback: RAG-Chunks direkt formatieren ─────────
      const offlineResponse = this._buildOfflineResponse(cleanPrompt, targetAgent, ragContext);
      this._bus.send({
        from:    targetAgent,
        to:      'user',
        content: offlineResponse,
        type:    'message',
      });
    }

    this._store.updateAgent(targetAgent, { status: 'idle' });
    return taskId;
  }

  /**
   * Offline-RAG-Antwort: Formatiert Knowledge-Chunks als strukturierte Antwort.
   * Keine KI nötig — direkt aus offiziellen deutschen Quellen (BBK, DRK, THW).
   */
  _buildOfflineResponse(prompt, agentId, chunks) {
    const agentEmoji = {
      medic_agent:     '🚑',
      engineer_agent:  '🛠️',
      navigator_agent: '🗺️',
      sensor_agent:    '⚡',
    }[agentId] || '🤖';

    if (chunks.length === 0) {
      return `${agentEmoji} Keine spezifischen Informationen in der Wissensbasis gefunden für: "${prompt}"\n\nNotruf: 112`;
    }

    // SOFORT-Chunks zuerst
    const sorted = [...chunks].sort((a, b) => {
      const priority = { SOFORT: 0, ANLEITUNG: 1, HINTERGRUND: 2 };
      return (priority[a.priority] ?? 2) - (priority[b.priority] ?? 2);
    });

    const lines = [];

    // Triage-Badge bei Notfall
    const hasSofort = sorted.some(c => c.priority === 'SOFORT');
    if (hasSofort) {
      lines.push('🚨 **SOFORTMASSNAHMEN** (aus offiziellen dt. Quellen: BBK/DRK/THW)');
      lines.push('');
    }

    for (const chunk of sorted.slice(0, 3)) {
      const badge = chunk.priority === 'SOFORT' ? '🚨' : chunk.priority === 'ANLEITUNG' ? '📋' : '📖';
      lines.push(`${badge} **${chunk.title || chunk.source}**`);
      lines.push(chunk.text.slice(0, 600) + (chunk.text.length > 600 ? '…' : ''));
      lines.push('');
    }

    lines.push(`_Quelle: Offizielle deutsche Krisenratgeber (§ 5 UrhG) | Offline-Modus_`);
    if (prompt.toLowerCase().includes('notfall') || hasSofort) {
      lines.push('**📞 Notruf: 112**');
    }

    return lines.join('\n');
  }

  /**
   * LLM-gestützte Antwort mit RAG-Kontext.
   */
  async _delegateViaLLM(prompt, images = [], targetAgent = 'medic_agent', ragContext = []) {
    const role = loadRole(targetAgent);

    // Journal-Context
    const journalContext = this._journal
      ? this._journal.getContextPrompt(targetAgent)
      : '';

    // RAG-Context als System-Prompt-Anhang
    let ragSection = '';
    if (ragContext.length > 0) {
      ragSection = '\n\n## Relevante Wissensbasis-Einträge (offizielle dt. Quellen):\n';
      for (const chunk of ragContext.slice(0, 3)) {
        ragSection += `\n### ${chunk.title}\n${chunk.text.slice(0, 500)}\n`;
      }
    }

    const systemContent = role.systemPrompt + ragSection + (journalContext || '');

    const userMessage = { role: 'user', content: prompt };
    if (images && images.length > 0) userMessage.images = images;

    try {
      const response = await this._llm.chat({
        messages: [
          { role: 'system', content: systemContent },
          userMessage,
        ],
        tools: role.toolWhitelist,
      });

      if (response?.content) {
        this._bus.send({
          from:    targetAgent,
          to:      'user',
          content: response.content,
          type:    'message',
        });
      }
    } catch (err) {
      // Ollama nicht erreichbar → offline fallback
      const fallback = this._buildOfflineResponse(prompt, targetAgent, ragContext);
      this._bus.send({
        from:    targetAgent,
        to:      'user',
        content: fallback,
        type:    'message',
      });
    }
  }

  // ── Status-Abfrage ────────────────────────────────────────────────

  /**
   * Get the full company status for the dashboard.
   * @returns {{ agents: Object[], kanban: Object, chatHistory: Object[] }}
   */
  getStatus() {
    const agents      = this._store.getAllAgents();
    const kanban      = this._kanban.getGrouped();
    const chatHistory = this._bus.getHistory();

    const agentSkills = agents.map(a => ({
      ...a,
      skills:      this._skills.getProfile(a.id),
      corrections: this._journal.getRecent(a.id, 3),
    }));

    return { agents: agentSkills, kanban, chatHistory };
  }

  /**
   * Get the delegation chain hierarchy.
   * @returns {Object[]}
   */
  getDelegationChain() {
    return DELEGATION_CHAIN.map(entry => ({
      ...entry,
      ...loadRole(entry.id),
    }));
  }

  // ── T-13: Heartbeat-Scheduler ─────────────────────────────────────

  /**
   * T-13: Konfiguriert einen periodischen Heartbeat für einen Agenten.
   * Bei jedem Tick wird onWake() aufgerufen (und intern wake(agentId)).
   *
   * @param {string} agentId
   * @param {{ intervalMs: number, onWake?: Function }} opts
   */
  configureHeartbeat(agentId, { intervalMs, onWake } = {}) {
    this.clearHeartbeat(agentId); // kein doppelter Timer
    if (!this._heartbeats) this._heartbeats = new Map();

    const timer = setInterval(() => {
      this.wake(agentId);
      if (onWake) onWake(agentId);
    }, intervalMs);

    this._heartbeats.set(agentId, timer);
  }

  /**
   * T-13: Stoppt den Heartbeat-Timer für einen Agenten.
   * @param {string} agentId
   */
  clearHeartbeat(agentId) {
    if (!this._heartbeats) return;
    const timer = this._heartbeats.get(agentId);
    if (timer) {
      clearInterval(timer);
      this._heartbeats.delete(agentId);
    }
  }

  /**
   * T-13: Weckt einen Agenten auf.
   * Wenn keine Tasks in der Queue → Agent kehrt zu 'idle' zurück.
   * @param {string} agentId
   */
  wake(agentId) {
    // Prüfe ob Tasks in Queue vorhanden
    const pendingTickets = this._kanban.getAll()
      .filter(t => t.assignee === agentId && t.status === 'backlog');

    if (pendingTickets.length === 0) {
      // Queue leer → idle
      this._store.updateAgent(agentId, { status: 'idle' });
    } else {
      // Queue hat Tasks → aktiv
      this._store.updateAgent(agentId, { status: 'working' });
    }
  }

  // ── T-16: BYOA — Externe HTTP-Agenten ──────────────────────────────

  /**
   * T-16: Registriert einen externen HTTP-Agenten.
   *
   * @param {{ id: string, url: string, role: string, _fetch?: Function }} agent
   */
  registerExternalAgent({ id, url, role, _fetch }) {
    if (!this._externalAgents) this._externalAgents = new Map();
    this._externalAgents.set(id, { id, url, role, _fetch: _fetch || fetch });
  }

  /**
   * T-16: Delegiert eine Aufgabe an einen registrierten externen HTTP-Agenten.
   * POST {task, agentId} → agent URL → { result, status }
   *
   * @param {string} agentId   - ID des externen Agenten
   * @param {{ task: string }} payload
   * @returns {Promise<Object>} Agent-Antwort
   */
  async delegateToAgent(agentId, payload) {
    if (!this._externalAgents || !this._externalAgents.has(agentId)) {
      throw new Error(`Externer Agent '${agentId}' nicht registriert`);
    }

    const agent = this._externalAgents.get(agentId);
    const fetchFn = agent._fetch;

    const response = await fetchFn(agent.url, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ agentId, ...payload }),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => '');
      throw new Error(`External agent HTTP ${response.status}: ${text.slice(0, 200)}`);
    }

    return response.json();
  }
}
