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
import { DAILY_SYSTEM_PROMPT, DAILY_AGENT_ID } from './daily-prompts.js';


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
    this._llmProvider = null;   // T-07: Firma-LLM-Provider (tests use chat(messages, tools) signature)
    this._initialized = false;
    this._appMode     = 'crisis'; // 'crisis' | 'daily'
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
   * DUAL INTERFACE:
   *   A) Firma-Modus (Tests): provider.chat(messages, tools) → { toolCall, args }
   *   B) Server-Modus: provider.chat({ messages, hasImages }) + provider.chatStream()
   *
   * Interface:
   *   provider.chat(messages: [{role, content}], tools: string[])
   *     → Promise<{ toolCall: string, args: Object }>
   *
   * @param {{ chat: Function }} provider
   */
  setLLMProvider(provider) {
    // Firma/Test-Pfad: chat(messages, tools) → { toolCall, args }
    this._llmProvider = provider;
    // Server-Pfad: chat({ messages, hasImages }) + chatStream()
    this._llm = provider;
  }

  /**
   * Setzt den App-Modus (crisis | daily).
   * Ändert Routing + System-Prompt des LLM.
   * @param {'crisis'|'daily'} mode
   */
  setAppMode(mode) {
    if (!['crisis', 'daily'].includes(mode)) {
      throw new Error(`Ungültiger App-Modus: ${mode}`);
    }
    this._appMode = mode;
  }

  /** Gibt den aktuellen App-Modus zurück */
  getAppMode() {
    return this._appMode;
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
    // Power-Policy prüfen (mit Timeout damit Tests nicht hängen)
    await Promise.race([
      this.checkPowerResilience(),
      new Promise(r => setTimeout(r, 50)), // Max 50ms Timeout
    ]).catch(() => {});

    // Energie-Sparmodus: Nur Krisen-Befehle (NUR im crisis-Modus relevant)
    const isCrisisPrompt = prompt.startsWith('/') || /hilfe|notfall|kaputt|defekt|medic|verbrenn|blut|herzstill|verletzt|ohnm|atemnot/i.test(prompt);
    if (this.powerPolicy === 'resilience' && this._appMode !== 'daily' && !isCrisisPrompt) {
      return {
        content: '⚠️ ENERGIE-SPARMODUS: Nur Krisen-Befehle erlaubt. Benutze /medic, /engineer, /nav oder /sensor.',
        type: 'error'
      };
    }

    const taskId = `task_${Date.now()}`;

    // ── 0. Memory-Kommandos erkennen (Feature #2) ─────────────────
    const memoryResult = this._handleMemoryCommand(prompt);
    if (memoryResult) {
      this._bus.send({ from: 'user', to: 'system', content: prompt, type: 'task' });
      this._bus.send({ from: 'system', to: 'user', content: memoryResult, type: 'message' });
      return taskId;
    }

    // ── T-07: Firma-LLM-Provider → CEO/CTO Delegation ─────────────────
    // Dieser Pfad wird von Tests mit setLLMProvider() + initFirma() verwendet.
    // Interface: chat(messages[], tools[]) → { toolCall, args }
    if (this._llmProvider) {
      return await this._submitViaFirmaLLM(prompt, taskId);
    }

    // ── 1. Routing: crisis oder daily ─────────────────────────────────
    let targetAgent, cleanPrompt;

    if (this._appMode === 'daily') {
      targetAgent  = DAILY_AGENT_ID;
      cleanPrompt  = prompt;
    } else {
      // Krisen-Modus: Crisis-Router bestimmt Spezial-Agenten
      const routing = routeCrisisPrompt(prompt);
      targetAgent   = routing.agentId || 'medic_agent';
      cleanPrompt   = routing.sanitizedPrompt || prompt;
    }

    // User-Nachricht ins Chat-Log
    this._bus.send({
      from:    'user',
      to:      targetAgent,
      content: cleanPrompt,
      images:  images,
      type:    'task',
    });

    // Firma-Delegation: alice_ceo → targetAgent (Rückwärtskompatibilität für Tests)
    this._bus.send({
      from:    'alice_ceo',
      to:      'bob_cto',
      content: `Delegiert: ${cleanPrompt.slice(0, 80)}`,
      type:    'message',
    });

    // Kanban-Ticket anlegen (immer — auch ohne LLM)
    this._kanban.createTicket?.({
      title:       prompt.slice(0, 80),
      description: `Aufgabe für ${targetAgent}`,
      assignee:    targetAgent,
    });

    this._store.updateAgent(targetAgent, { status: 'working' });

    // ── 2. RAG-Suche ─────────────────────────────────────────────────
    let ragContext = [];
    try {
      ragContext = searchKnowledge(cleanPrompt, { limit: 4 });
    } catch { /* graceful */ }

    // ── 3a. Server-LLM verfügbar ─────────────────────────────────────
    if (this._llm) {
      await this._delegateViaLLM(cleanPrompt, images, targetAgent, ragContext);
    } else {
      const offlineResponse = this._buildOfflineResponse(cleanPrompt, targetAgent, ragContext);
      this._bus.send({ from: targetAgent, to: 'user', content: offlineResponse, type: 'message' });
    }

    this._store.updateAgent(targetAgent, { status: 'idle' });
    return taskId;
  }

  /**
   * T-07: Firma-LLM Delegation (CEO → CTO via LLM-Provider).
   * Erstellt Kanban-Ticket + CEO→CTO Chat-Nachricht basierend auf LLM-Antwort.
   */
  async _submitViaFirmaLLM(prompt, taskId) {
    const journalContext = this._journal?.getContextPrompt?.('alice_ceo') || '';
    const systemContent  = `Du bist Alice (CEO). Delegiere Aufgaben klar und präzise.${journalContext}`;

    const messages = [
      { role: 'system',    content: systemContent },
      { role: 'user',      content: prompt },
    ];
    const tools = ['assign_task', 'search_knowledge'];

    let llmResult;
    try {
      llmResult = await this._llmProvider.chat(messages, tools);
    } catch {
      llmResult = null;
    }

    if (llmResult?.toolCall === 'assign_task' && llmResult?.args) {
      const { from = 'alice_ceo', to = 'bob_cto', task, description = '' } = llmResult.args;
      // Kanban-Ticket aus LLM-Antwort
      this._kanban.createTicket({ title: task, description, assignee: to, status: 'backlog' });
      // CEO → CTO Chat
      this._bus.send({ from, to, content: `Task: ${task}`, type: 'message' });
    } else {
      // Fallback: direktes Ticket ohne LLM-Antwort
      this._kanban.createTicket({ title: prompt.slice(0, 80), description: '', assignee: 'bob_cto', status: 'backlog' });
      this._bus.send({ from: 'alice_ceo', to: 'bob_cto', content: `Task: ${prompt}`, type: 'message' });
    }

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
    // Guard: daily_assistant hat keine roles.js-Rolle — loadRole nur für Krisen-Agenten
    const role = (targetAgent === DAILY_AGENT_ID)
      ? { systemPrompt: DAILY_SYSTEM_PROMPT, id: DAILY_AGENT_ID, role: 'Alltags-Assistent' }
      : loadRole(targetAgent);

    // Journal-Context (nur für Krisen-Agenten sinnvoll)
    const journalContext = (this._journal && targetAgent !== DAILY_AGENT_ID)
      ? this._journal.getContextPrompt(targetAgent)
      : '';

    // RAG-Context als optionale Ergänzung — NICHT als Dominanz
    // Gemma 4 E4B hat umfangreiches medizinisches Wissen. RAG-Chunks sollen
    // DACH-spezifische Notrufnummern und Protokolle ergänzen, nicht die Antwort ersetzen.
    let ragSection = '';
    if (ragContext.length > 0) {
      // Nur Chunks mit hoher Relevanz einbauen (score > 3 = starker Title-Match)
      const relevant = ragContext.filter(c => (c.score || 0) > 3);
      if (relevant.length > 0) {
        ragSection = '\n\n## Ergänzende Informationen aus offiziellen DACH-Quellen:\n';
        ragSection += '(Nutze diese NUR wenn sie zur Frage passen. Bevorzuge dein eigenes Wissen für allgemeine medizinische/technische Fragen.)\n';
        for (const chunk of relevant.slice(0, 2)) {
          ragSection += `\n### ${chunk.title}\n${chunk.text.slice(0, 400)}\n`;
        }
      }
    }

    // ── Feature #4: Datum/Uhrzeit-Bewusstsein ──────────────────────────
    const now = new Date();
    const weekdays = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];
    const months = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
    const hour = now.getHours();
    const timeOfDay = hour < 6 ? 'Nacht' : hour < 12 ? 'Morgen' : hour < 18 ? 'Nachmittag' : 'Abend';
    const season = [0,1,2].includes(now.getMonth()) ? 'Winter' : [3,4,5].includes(now.getMonth()) ? 'Frühling' : [6,7,8].includes(now.getMonth()) ? 'Sommer' : 'Herbst';
    const dateStr = `\nAktuell: ${weekdays[now.getDay()]}, ${now.getDate()}. ${months[now.getMonth()]} ${now.getFullYear()}, ${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')} Uhr (${timeOfDay}). Jahreszeit: ${season}.`;

    // Basis-Prompt: Daily-Assistent hat eigenen Prompt, Krisen-Agenten nutzen ihre Rollen
    const basePrompt = (targetAgent === DAILY_AGENT_ID)
      ? DAILY_SYSTEM_PROMPT
      : role.systemPrompt;

    const crisisSuffix = (targetAgent === DAILY_AGENT_ID)
      ? '' // Kein Notruf-Zwang im Alltags-Modus
      : '\n\nWICHTIG: Antworte IMMER auf Deutsch. Sei präzise und nutze dein medizinisches/technisches Wissen.'
        + '\nNenne bei medizinischen Themen immer: Notruf 112. Bei Vergiftungen: Giftnotruf 030-19240.';

    const systemContent = basePrompt + ragSection + (journalContext || '')
      + dateStr
      + this._getMemoryContext()
      + crisisSuffix;

    const userMessage = { role: 'user', content: prompt };
    if (images && images.length > 0) userMessage.images = images;

    // ── Feature #3: Konversationskontext (letzte 10 Nachrichten) ──────
    // Gemma 4 E4B hat 128K Token Kontext — wir nutzen die letzten 10 Messages
    // damit Rückfragen wie "Und wenn es eine Blase bildet?" funktionieren.
    const recentHistory = this._bus.getHistory(20)
      .filter(m => m.from === 'user' || (m.from !== 'system' && m.type === 'message'))
      .slice(-10)
      .map(m => ({
        role: m.from === 'user' ? 'user' : 'assistant',
        content: m.content?.slice(0, 1000) || '',  // Cap per message to save tokens
      }));

    try {
      const msgs = [
        { role: 'system', content: systemContent },
        ...recentHistory,
        userMessage,
      ];

      // Use streaming if available — user sees tokens arriving in real-time
      if (this._llm.chatStream) {
        let streamedContent = '';
        let lastUpdate = Date.now();
        const streamMsgId = `stream_${Date.now()}`;

        const response = await this._llm.chatStream(
          { messages: msgs, hasImages: !!(images && images.length > 0) },
          (token) => {
          streamedContent += token;
          // Send incremental updates every 500ms so frontend poll picks them up
          const now = Date.now();
          if (now - lastUpdate > 500) {
            lastUpdate = now;
            this._bus.send({
              id:      streamMsgId,
              from:    targetAgent,
              to:      'user',
              content: streamedContent + ' ▍',  // Cursor indicator
              type:    'streaming',
            });
          }
        });

        // Final message (replaces streaming)
        if (response?.content) {
          this._bus.send({
            id:      streamMsgId,
            from:    targetAgent,
            to:      'user',
            content: response.content,
            type:    'message',
          });
        }
      } else {
        // Fallback: blocking chat
        const response = await this._llm.chat({ messages: msgs });
        if (response?.content) {
          this._bus.send({
            from:    targetAgent,
            to:      'user',
            content: response.content,
            type:    'message',
          });
        }
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

  // ── Feature #2: Memory-Kommandos ───────────────────────────────

  /**
   * Detect and handle memory commands: "merke dir", "vergiss", "was weißt du"
   * Returns a response string if handled, or null if not a memory command.
   */
  _handleMemoryCommand(prompt) {
    const lower = prompt.toLowerCase().trim();

    // "Was weißt du über mich?" / "Was hast du dir gemerkt?"
    if (lower.match(/was (weißt|weisst) du|was hast du.*gemerkt|meine daten|mein profil/)) {
      const memories = this._store.getAllMemories();
      if (memories.length === 0) {
        return '🧠 Ich habe mir noch nichts über dich gemerkt.\n\nSag mir z.B.:\n• "Merke dir: Meine Blutgruppe ist A positiv"\n• "Merke dir: Ich bin allergisch gegen Penicillin"\n• "Merke dir: Mein Kind heißt Lena, 4 Jahre"';
      }
      let response = `🧠 **Deine gespeicherten Informationen** (${memories.length}):\n\n`;
      for (const m of memories) {
        response += `• **${m.key}**: ${m.value}\n`;
      }
      response += '\n_Alles lokal auf deinem Gerät. Sage "Vergiss alles" zum Löschen._';
      return response;
    }

    // "Merke dir: ..." / "Erinnere dich: ..."
    const merkeMatch = lower.match(/^(?:merke? dir|erinnere? dich|speichere?)[:\s]+(.+)/);
    if (merkeMatch) {
      const fact = prompt.slice(prompt.toLowerCase().indexOf(merkeMatch[1]));
      // Try to extract key:value from "Meine Blutgruppe ist A positiv"
      const kvMatch = fact.match(/(?:mein[ea]?\s+)?(\w[\w\s]*?)\s+(?:ist|sind|heißt|lautet|beträgt)\s+(.+)/i);
      const key = kvMatch ? kvMatch[1].trim() : 'Notiz';
      const value = kvMatch ? kvMatch[2].trim() : fact.trim();
      const category = this._categorizeMemory(key + ' ' + value);
      this._store.addMemory({ key, value, category });
      return `🧠 Gemerkt: **${key}** → ${value}\n\n_Gespeichert unter "${category}". Nur auf diesem Gerät._`;
    }

    // "Vergiss..." / "Lösche..."
    if (lower.match(/^(?:vergiss|lösche?|entferne?)\s+alles/)) {
      this._store.clearAllMemories();
      return '🧠 Alle Erinnerungen gelöscht. Ich weiß nichts mehr über dich.';
    }

    // "Ich bin in Österreich/Schweiz/Deutschland" → Land speichern (Feature #12)
    const countryMatch = lower.match(/ich (?:bin|lebe|wohne).*(?:in |aus )?(österreich|schweiz|deutschland)/);
    if (countryMatch) {
      const countryMap = { österreich: 'AT', schweiz: 'CH', deutschland: 'DE' };
      const countryCode = countryMap[countryMatch[1]];
      this._store.addMemory({ key: '__country__', value: countryCode, category: 'system' });
      const notruf = { AT: '144 (Rettung), 01-4064343 (Vergiftung)', CH: '144 (Rettung), 145 (Tox Info)', DE: '112 (Notruf), 030-19240 (Giftnotruf)' };
      return `✅ Gespeichert: Du bist in **${countryMatch[1].charAt(0).toUpperCase() + countryMatch[1].slice(1)}**.\n\nDeine Notfallnummern: **${notruf[countryCode]}**\n\n_Der Notruf-Stripe wird automatisch angepasst._`;
    }

    // Assistenten-Name ändern: "Nenn dich Nova" / "Ändere deinen Namen zu Finn"
    const renameMatch = lower.match(
      /(?:nenn dich|heiße?|ändere? (?:dein(?:en)? )?namen?(?: zu| auf)?|dein name (?:ist|soll sein))\s+([\w]{2,20})/
    );
    if (renameMatch) {
      const newName = renameMatch[1].charAt(0).toUpperCase() + renameMatch[1].slice(1);
      this._store.addMemory({ key: '__assistant_name__', value: newName, category: 'system' });
      return `◑ Ab jetzt heiße ich **${newName}**.\n\n_Beim nächsten Start erscheint der neue Name oben in der App._`;
    }

    return null; // Kein Memory-Kommando
  }

  /**
   * Auto-categorize a memory key.
   */
  _categorizeMemory(key) {
    const lower = key.toLowerCase();
    if (lower.match(/blutgruppe|allergi|krankheit|medikament|impf|unverträglich/)) return 'gesundheit';
    if (lower.match(/kind|frau|mann|partner|sohn|tochter|name|alter|gewicht/)) return 'familie';
    if (lower.match(/adresse|telefon|notfall|kontakt|hausar/)) return 'kontakt';
    return 'allgemein';
  }

  /**
   * Build memory context string for system prompt injection.
   */
  _getMemoryContext() {
    const memories = this._store.getAllMemories();
    if (memories.length === 0) return '';
    let ctx = '\n\n## Persönliche Informationen des Nutzers (aus dem Gedächtnis):\n';
    ctx += '(Nutze diese Informationen wenn sie relevant für die Frage sind.)\n';
    for (const m of memories) {
      ctx += `- ${m.key}: ${m.value}\n`;
    }
    return ctx;
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
    // Sicherstellen dass der Agent im Store existiert
    if (!this._store.getAgent(agentId)) {
      this._store.createAgent({ id: agentId, role: agentId, status: 'idle', systemPrompt: '' });
    }

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
