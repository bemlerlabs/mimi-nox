/**
 * ◑ MiMiNox v2 — E2E Integration Test
 * QA-Audit: Prüft die gesamte Pipeline von Firma-Init bis Skill-XP.
 * Alle Module müssen zusammen funktionieren.
 */
import { describe, it, expect, afterEach } from 'vitest';
import { StateStore } from '../server/state/store.js';
import { ChatBus } from '../server/agents/chat-bus.js';
import { KanbanEngine } from '../server/agents/kanban.js';
import { SkillSystem } from '../server/agents/skill-system.js';
import { CommTools } from '../server/agents/comm-tools.js';
import { CorrectionJournal } from '../server/agents/correction-journal.js';
import { Orchestrator } from '../server/agents/orchestrator.js';
import { EventLog } from '../server/transparency/event-log.js';
import { ThoughtDecomposer } from '../server/transparency/thought-decomposer.js';
import { TopologyMetrics } from '../server/transparency/topology-metrics.js';
import { KnowledgeGraph } from '../server/transparency/knowledge-graph.js';
import { loadRole, getAllRoles, isToolAllowed } from '../server/agents/roles.js';
import { ThinkingStreamParser } from '../server/llm/thinking-parser.js';

describe('E2E: Vollständige Pipeline', () => {
  let store;

  afterEach(() => { try { store?.close(); } catch {} });

  it('Firma-Init → Auftrag → Delegation → Dev → QA → Approve → Skill-XP', () => {
    // ── SETUP ─────────────────────────────────────────────────────
    store = new StateStore(':memory:');
    const bus = new ChatBus(store);
    const kanban = new KanbanEngine(store);
    const skills = new SkillSystem(store);
    const comm = new CommTools({ store, bus, kanban, skills });
    const journal = new CorrectionJournal(store);
    const eventLog = new EventLog(store);
    const metrics = new TopologyMetrics(store);
    const graph = new KnowledgeGraph();
    const decomposer = new ThoughtDecomposer();
    const orch = new Orchestrator({ store, bus, kanban, skills, comm, journal });

    // ── 1. KRISEN-TEAM INIT ──────────────────────────────────────────
    orch.initFirma();
    const agents = store.getAllAgents();
    expect(agents).toHaveLength(4);
    expect(agents.every(a => a.status === 'idle')).toBe(true);

    // Alle haben Skill-Profile
    for (const a of agents) {
      const profile = skills.getProfile(a.id);
      expect(profile).toBeDefined();
      expect(profile.level).toBe(1);
      expect(Object.keys(profile.skills).length).toBeGreaterThanOrEqual(4);
    }

    // ── 2. AUFTRAG EINREICHEN ──────────────────────────────────────
    const taskId = orch.submitTask('Baue eine REST-API für Todos');
    expect(taskId).toBeDefined();

    // Ticket wurde erstellt
    const tickets = kanban.getAll();
    expect(tickets).toHaveLength(1);
    expect(tickets[0].assignee).toBe('bob_cto');
    expect(tickets[0].status).toBe('backlog');

    // Alice hat an Bob gesendet
    const history = bus.getHistory();
    expect(history.some(m => m.from === 'alice_ceo' && m.to === 'bob_cto')).toBe(true);

    // ── 3. BOB DELEGIERT AN CHARLIE ────────────────────────────────
    comm.assignTask({
      from: 'bob_cto',
      to: 'charlie_dev',
      task: 'Express Endpoints implementieren',
      description: 'GET/POST/PUT/DELETE für /api/todos',
    });

    expect(kanban.getAll()).toHaveLength(2);
    expect(kanban.getAll()[1].assignee).toBe('charlie_dev');

    // ── 4. CHARLIE ARBEITET ──────────────────────────────────────
    const devTicketId = kanban.getAll()[1].id;
    kanban.moveTicket(devTicketId, 'in_progress');
    store.updateAgent('charlie_dev', { status: 'running' });

    // Log Events
    eventLog.addEvent({ type: 'tool_call', agentId: 'charlie_dev', toolName: 'read_file' });
    eventLog.addEvent({ type: 'thinking', agentId: 'charlie_dev', content: 'REST oder GraphQL?' });

    // Thought Decomposition
    const tree = decomposer.decompose('REST oder GraphQL? REST für MVP. GraphQL für komplexe Queries.');
    expect(tree.root).toContain('?');
    expect(tree.children.length).toBeGreaterThanOrEqual(1);

    // Metrics
    metrics.recordThoughtFlow('charlie_dev');
    metrics.recordConnection('charlie_dev', 'express', 'todos');
    expect(metrics.getTF('charlie_dev')).toBe(1);
    expect(metrics.getKC('charlie_dev')).toBe(1);

    // Knowledge Graph
    graph.addNode({ id: 'charlie_dev', type: 'agent', label: 'Charlie' });
    graph.addNode({ id: 'express', type: 'technology', label: 'Express' });
    graph.addEdge({ from: 'charlie_dev', to: 'express', type: 'chose' });
    expect(graph.nodeCount).toBe(2);
    expect(graph.edgeCount).toBe(1);

    // Tool usage XP
    skills.onToolUsed('charlie_dev', 'web_search');
    expect(skills.getProfile('charlie_dev').skills.research).toBe(45); // 40 + 5

    // ── 5. CHARLIE REICHT EIN ────────────────────────────────────
    comm.submitWork({
      from: 'charlie_dev',
      ticketId: devTicketId,
      result: 'CRUD Endpoints fertig',
      code: 'app.get("/api/todos", ...)',
    });

    expect(kanban.getTicket(devTicketId).status).toBe('testing');

    // ── 6. DIANA LEHNT AB (Erste Runde) ──────────────────────────
    const cqBefore = skills.getProfile('charlie_dev').skills.codeQuality;
    const bdBefore = skills.getProfile('charlie_dev').skills.bugDetection;

    comm.rejectWork({
      from: 'diana_qa',
      ticketId: devTicketId,
      reason: 'Keine Input-Validierung',
      feedback: 'express-validator nutzen',
    });

    expect(kanban.getTicket(devTicketId).status).toBe('in_progress');
    // T-04 FIX: Kein XP bei Rejection — Developer hat noch nichts gefixt
    expect(skills.getProfile('charlie_dev').skills.bugDetection).toBe(bdBefore);

    // CorrectionJournal eintragen
    journal.addCorrection({
      agentId: 'charlie_dev',
      error: 'Keine Input-Validierung',
      fix: 'express-validator hinzugefügt',
      ticketId: devTicketId,
    });

    const prompt = journal.getContextPrompt('charlie_dev');
    expect(prompt).toContain('Input-Validierung');

    // Error Topology
    graph.generateErrorTopology({
      error: 'Keine Input-Validierung',
      file: 'todos-router.js',
      agent: 'charlie_dev', // Already exists
      sop: 'Input-Sanitization',
    });
    expect(graph.nodeCount).toBeGreaterThanOrEqual(4);

    // ── 7. CHARLIE FIXT UND REICHT ERNEUT EIN ────────────────────
    kanban.moveTicket(devTicketId, 'testing');

    // ── 8. DIANA GENEHMIGT ──────────────────────────────────────
    comm.approveWork({ from: 'diana_qa', ticketId: devTicketId });

    expect(kanban.getTicket(devTicketId).status).toBe('done');
    expect(skills.getProfile('charlie_dev').skills.codeQuality).toBe(cqBefore + 3);
    // T-04 FIX: bugDetection XP kommt JETZT beim Approve (Fix wurde geleistet)
    expect(skills.getProfile('charlie_dev').skills.bugDetection).toBe(bdBefore + 8);


    // ── 9. STATUS DASHBOARD ──────────────────────────────────────
    const status = orch.getStatus();
    expect(status.agents).toHaveLength(4);
    expect(status.kanban.done.length).toBeGreaterThanOrEqual(1);
    expect(status.chatHistory.length).toBeGreaterThan(0);

    // Graph serialization
    const graphJson = graph.toJSON();
    expect(graphJson.nodes.length).toBeGreaterThanOrEqual(4);
    expect(graphJson.edges.length).toBeGreaterThanOrEqual(3);

    // Event audit trail
    const events = eventLog.getEvents();
    expect(events.length).toBeGreaterThan(0);

    // Tool whitelist enforcement
    expect(isToolAllowed('alice_ceo', 'run_shell')).toBe(false);
    expect(isToolAllowed('charlie_dev', 'run_shell')).toBe(true);
    expect(isToolAllowed('diana_qa', 'reject_work')).toBe(true);

    // Delegation chain
    const chain = orch.getDelegationChain();
    expect(chain).toHaveLength(4);

    // Weakest skill
    const weakest = skills.getWeakestSkill('alice_ceo');
    expect(weakest.skill).toBe('testing'); // 10 is lowest for CEO

    // Thinking parser (Phase 1 - still works)
    const parser = new ThinkingStreamParser();
    parser.feed('<|think|>Test Gedanke<|/think|>Antwort');
    expect(parser.thinking).toBe('Test Gedanke');
    expect(parser.answer).toBe('Antwort');

    console.log('\n✅ E2E Pipeline komplett! Alle Module integriert.');
  });
});
