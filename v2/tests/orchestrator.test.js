/**
 * ◑ MiMiNox v2 — Test: Hierarchie-Orchestrator
 * Task 2.2: CEO dekomponiert → CTO plant → Dev implementiert → QA prüft
 * TDD: Tests FIRST.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { Orchestrator } from '../server/agents/orchestrator.js';
import { StateStore } from '../server/state/store.js';
import { ChatBus } from '../server/agents/chat-bus.js';
import { KanbanEngine } from '../server/agents/kanban.js';
import { SkillSystem } from '../server/agents/skill-system.js';
import { CommTools } from '../server/agents/comm-tools.js';
import { CorrectionJournal } from '../server/agents/correction-journal.js';
import { loadRole, getAllRoles } from '../server/agents/roles.js';

// ── Bestehende Orchestrator-Tests (unveränderter Regression-Guard) ────────────

describe('Task 2.2: Hierarchie-Orchestrator', () => {
  let store, bus, kanban, skills, comm, journal, orch;

  beforeEach(() => {
    store   = new StateStore(':memory:');
    bus     = new ChatBus(store);
    kanban  = new KanbanEngine(store);
    skills  = new SkillSystem(store);
    comm    = new CommTools({ store, bus, kanban, skills });
    journal = new CorrectionJournal(store);
    orch    = new Orchestrator({ store, bus, kanban, skills, comm, journal });
  });

  afterEach(() => store?.close());

  it('[D] GIVEN fresh orchestrator WHEN init THEN 4 crisis agents with idle status', () => {
    orch.initFirma();
    const agents = store.getAllAgents();
    expect(agents).toHaveLength(4);
    expect(agents.every(a => a.status === 'idle')).toBe(true);
    const ids = agents.map(a => a.id);
    expect(ids).toContain('medic_agent');
    expect(ids).toContain('engineer_agent');
    expect(ids).toContain('navigator_agent');
    expect(ids).toContain('sensor_agent');
  });

  it('[D] GIVEN initFirma THEN all agents have skill profiles', () => {
    orch.initFirma();
    for (const id of ['medic_agent', 'engineer_agent', 'navigator_agent', 'sensor_agent']) {
      const profile = skills.getProfile(id);
      expect(profile).toBeDefined();
      expect(profile.level).toBe(1);
      expect(Object.keys(profile.skills).length).toBeGreaterThanOrEqual(4);
    }
  });

  it('[D] GIVEN firma WHEN submitTask THEN creates tickets in kanban', () => {
    orch.initFirma();
    const taskId = orch.submitTask('Baue eine Todo-App');
    expect(taskId).toBeDefined();
    const tickets = kanban.getAll();
    expect(tickets.length).toBeGreaterThanOrEqual(1);
    expect(tickets[0].status).toBe('backlog');
  });

  it('[D] GIVEN firma WHEN submitTask THEN alice sends chat to bob', () => {
    orch.initFirma();
    orch.submitTask('Baue eine Todo-App');
    const history = bus.getHistory();
    expect(history.some(m => m.from === 'alice_ceo' && m.to === 'bob_cto')).toBe(true);
  });

  it('[D] GIVEN firma with task WHEN getStatus THEN returns full state', () => {
    orch.initFirma();
    orch.submitTask('Baue eine API');
    const status = orch.getStatus();
    expect(status.agents).toHaveLength(4);
    expect(status.kanban.backlog.length).toBeGreaterThanOrEqual(1);
    expect(status.chatHistory.length).toBeGreaterThan(0);
  });

  it('[D] GIVEN firma WHEN getDelegationChain THEN shows 4 crisis agents', () => {
    const chain = orch.getDelegationChain();
    expect(chain).toHaveLength(4);
    expect(chain[0].id).toBe('medic_agent');
    expect(chain[1].id).toBe('engineer_agent');
    expect(chain[2].id).toBe('navigator_agent');
    expect(chain[3].id).toBe('sensor_agent');
  });
});

// ── T-07: LLM-Provider Interface ─────────────────────────────────────────────

describe('T-07: Orchestrator — LLM-Provider Interface', () => {
  let store, bus, kanban, skills, comm, journal, orch;

  beforeEach(() => {
    store   = new StateStore(':memory:');
    bus     = new ChatBus(store);
    kanban  = new KanbanEngine(store);
    skills  = new SkillSystem(store);
    comm    = new CommTools({ store, bus, kanban, skills });
    journal = new CorrectionJournal(store);
    orch    = new Orchestrator({ store, bus, kanban, skills, comm, journal });
    orch.initFirma();
  });

  afterEach(() => store?.close());

  // GIVEN ein Orchestrator mit LLM-Provider
  // WHEN submitTask aufgerufen wird
  // THEN ruft der Orchestrator den LLM-Provider auf (nicht Stub)
  it('[T-07] GIVEN setLLMProvider WHEN submitTask THEN LLM is called with prompt', async () => {
    const llmCalls = [];

    orch.setLLMProvider({
      chat: async (messages, tools) => {
        llmCalls.push({ messages, tools });
        return {
          toolCall: 'assign_task',
          args: { from: 'alice_ceo', to: 'bob_cto',
                  task: 'REST API bauen', description: 'CRUD /api/todos' },
        };
      },
    });

    await orch.submitTask('Baue eine REST API für Todos');

    expect(llmCalls.length).toBeGreaterThan(0);
    expect(llmCalls[0].messages.some(m => m.content.includes('Todos'))).toBe(true);
    expect(llmCalls[0].tools).toBeDefined();
    expect(llmCalls[0].tools).toContain('assign_task');
  });

  // GIVEN LLM-Provider gibt assign_task zurück
  // WHEN submitTask ausgeführt
  // THEN Ticket hat LLM-generierte Daten (nicht hardcoded)
  it('[T-07] GIVEN LLM returns assign_task WHEN submitTask THEN ticket has LLM content', async () => {
    orch.setLLMProvider({
      chat: async () => ({
        toolCall: 'assign_task',
        args: { from: 'alice_ceo', to: 'bob_cto',
                task: 'KI-generierter Task', description: 'Von LLM erstellt' },
      }),
    });

    await orch.submitTask('Beliebiger Input');

    const llmTicket = kanban.getAll().find(t => t.title === 'KI-generierter Task');
    expect(llmTicket).toBeDefined();
    expect(llmTicket.description).toContain('Von LLM erstellt');
  });

  // GIVEN kein LLM-Provider (Fallback)
  // WHEN submitTask aufgerufen
  // THEN direktes assignTask wie bisher (kein Crash, rückwärtskompatibel)
  it('[T-07] GIVEN no LLM provider WHEN submitTask THEN fallback direct delegation', () => {
    const taskId = orch.submitTask('Beliebiger Task');
    expect(taskId).toBeDefined();
    expect(kanban.getAll().length).toBeGreaterThan(0);
  });
});

// ── T-08: CorrectionJournal — Prompt-Injection vor LLM-Call ──────────────────

describe('T-08: CorrectionJournal — getContextPrompt & LLM-Injection', () => {
  let store, bus, kanban, skills, comm, journal, orch;

  beforeEach(() => {
    store   = new StateStore(':memory:');
    bus     = new ChatBus(store);
    kanban  = new KanbanEngine(store);
    skills  = new SkillSystem(store);
    comm    = new CommTools({ store, bus, kanban, skills });
    journal = new CorrectionJournal(store);
    orch    = new Orchestrator({ store, bus, kanban, skills, comm, journal });
    orch.initFirma();
  });

  afterEach(() => store?.close());

  // GIVEN Journal hat Korrektur-Einträge für alice_ceo
  // WHEN getContextPrompt aufgerufen
  // THEN enthält der Prompt Fehler + Fix, beginnt mit ---
  it('[T-08] GIVEN journal has errors WHEN getContextPrompt THEN prompt has correct format', () => {
    journal.addCorrection({
      agentId:  'alice_ceo',
      error:    'Keine Zeitplanung für Sprints',
      fix:      'Sprint-Dauer in Ticket-Description angeben',
      ticketId: 1,
    });

    const prompt = journal.getContextPrompt('alice_ceo');
    expect(prompt).toContain('Keine Zeitplanung für Sprints');
    expect(prompt).toContain('Sprint-Dauer');
    expect(prompt.startsWith('\n---')).toBe(true);
  });

  // GIVEN leeres Journal
  // WHEN getContextPrompt aufgerufen
  // THEN leerer String (kein Phantom-Prompt)
  it('[T-08] GIVEN empty journal WHEN getContextPrompt THEN empty string', () => {
    expect(journal.getContextPrompt('alice_ceo')).toBe('');
  });

  // GIVEN Journal hat Fehler UND LLM-Provider gesetzt
  // WHEN submitTask ausgeführt
  // THEN System-Prompt enthält Journal-Context (Injection verifiziert)
  it('[T-08] GIVEN journal + LLM provider WHEN submitTask THEN journal injected in system prompt', async () => {
    journal.addCorrection({
      agentId:  'alice_ceo',
      error:    'Delegation zu vage',
      fix:      'Konkrete Akzeptanzkriterien benennen',
      ticketId: 2,
    });

    const captured = [];

    orch.setLLMProvider({
      chat: async (messages, tools) => {
        captured.push(...messages);
        return {
          toolCall: 'assign_task',
          args: { from: 'alice_ceo', to: 'bob_cto', task: 'Test', description: '' },
        };
      },
    });

    await orch.submitTask('Baue etwas');

    const systemMsg = captured.find(m => m.role === 'system');
    expect(systemMsg).toBeDefined();
    expect(systemMsg.content).toContain('Delegation zu vage');
    expect(systemMsg.content).toContain('Konkrete Akzeptanzkriterien');
  });
});

// ── T-13: Heartbeat-Scheduler ─────────────────────────────────────────────────

describe('T-13: Heartbeat — Agent Wake-Up', () => {
  let store, bus, kanban, skills, comm, journal, orch;

  beforeEach(() => {
    store   = new StateStore(':memory:');
    bus     = new ChatBus(store);
    kanban  = new KanbanEngine(store);
    skills  = new SkillSystem(store);
    comm    = new CommTools({ store, bus, kanban, skills });
    journal = new CorrectionJournal(store);
    orch    = new Orchestrator({ store, bus, kanban, skills, comm, journal });
    orch.initFirma();
  });

  afterEach(() => { orch.clearHeartbeat('alice_ceo'); store?.close(); });

  // GIVEN Heartbeat konfiguriert
  // WHEN Interval feuert 2x
  // THEN wake() genau 2x aufgerufen
  it('[T-13] GIVEN heartbeat WHEN interval fires THEN wake called N times', async () => {
    const wakeCalls = [];
    orch.configureHeartbeat('alice_ceo', {
      intervalMs: 50,
      onWake: () => wakeCalls.push(Date.now()),
    });
    await new Promise(r => setTimeout(r, 130)); // 2 vollständige Intervalle
    orch.clearHeartbeat('alice_ceo');
    expect(wakeCalls.length).toBeGreaterThanOrEqual(2);
  });

  // GIVEN leere Task-Queue
  // WHEN wake() aufgerufen
  // THEN Agent bleibt idle
  it('[T-13] GIVEN empty queue WHEN wake THEN agent stays idle', () => {
    orch.wake('alice_ceo');
    const agent = store.getAgent('alice_ceo');
    expect(agent.status).toBe('idle');
  });

  // GIVEN Heartbeat läuft
  // WHEN clearHeartbeat aufgerufen
  // THEN keine weiteren wake-Calls
  it('[T-13] GIVEN running heartbeat WHEN clearHeartbeat THEN stops', async () => {
    const wakeCalls = [];
    orch.configureHeartbeat('alice_ceo', {
      intervalMs: 30,
      onWake: () => wakeCalls.push(1),
    });
    await new Promise(r => setTimeout(r, 50));
    orch.clearHeartbeat('alice_ceo');
    const countAfterClear = wakeCalls.length;
    await new Promise(r => setTimeout(r, 80)); // nach Clear kein neuer Call
    expect(wakeCalls.length).toBe(countAfterClear);
  });
});

// ── T-16: BYOA — Externer HTTP-Agent Adapter ─────────────────────────────────

describe('T-16: BYOA — External HTTP-Agent', () => {
  let store, bus, kanban, skills, comm, journal, orch;

  beforeEach(() => {
    store   = new StateStore(':memory:');
    bus     = new ChatBus(store);
    kanban  = new KanbanEngine(store);
    skills  = new SkillSystem(store);
    comm    = new CommTools({ store, bus, kanban, skills });
    journal = new CorrectionJournal(store);
    orch    = new Orchestrator({ store, bus, kanban, skills, comm, journal });
    orch.initFirma();
  });

  afterEach(() => store?.close());

  // GIVEN externer HTTP-Agent registriert
  // WHEN delegateToAgent aufgerufen
  // THEN HTTP POST an Agent-URL gesendet
  it('[T-16] GIVEN external agent WHEN delegateToAgent THEN HTTP POST sent', async () => {
    const fetchCalls = [];
    const mockFetch = async (url, opts) => {
      fetchCalls.push({ url, method: opts.method });
      return { ok: true, json: async () => ({ result: 'External done', status: 'done' }) };
    };

    orch.registerExternalAgent({
      id:   'claude_coder',
      url:  'http://external-claude/api/run',
      role: 'developer',
      _fetch: mockFetch, // injizierbarer fetch
    });

    const result = await orch.delegateToAgent('claude_coder', { task: 'Write tests' });

    expect(fetchCalls.length).toBe(1);
    expect(fetchCalls[0].url).toBe('http://external-claude/api/run');
    expect(fetchCalls[0].method).toBe('POST');
    expect(result.result).toBe('External done');
  });

  // GIVEN externer Agent nicht erreichbar
  // WHEN delegateToAgent aufgerufen
  // THEN Error propagiert (kein Crash ohne Error-Handling)
  it('[T-16] GIVEN external agent unreachable WHEN delegateToAgent THEN throws', async () => {
    const mockFetch = async () => { throw new Error('ECONNREFUSED'); };

    orch.registerExternalAgent({
      id: 'offline_agent',
      url: 'http://offline/api/run',
      role: 'developer',
      _fetch: mockFetch,
    });

    await expect(orch.delegateToAgent('offline_agent', { task: 'fail' }))
      .rejects.toThrow();
  });
});
