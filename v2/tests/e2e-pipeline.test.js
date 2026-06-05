/**
 * ◑ MiMiNox v2 — E2E Integration Test
 * QA-Audit: Prüft die gesamte Pipeline vom Krisen-Team bis Skill-XP.
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

  it('Krisen-Team → Auftrag → Delegation → Review → Approve → Skill-XP', async () => {
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
    const taskId = await orch.submitTask('Solaranlage liefert keinen Strom');
    expect(taskId).toBeDefined();

    // Ticket wurde erstellt
    const tickets = kanban.getAll();
    expect(tickets).toHaveLength(1);
    expect(tickets[0].assignee).toBe('engineer_agent');
    expect(tickets[0].status).toBe('backlog');

    // System hat an den passenden Spezial-Agenten delegiert
    const history = bus.getHistory();
    expect(history.some(m => m.from === 'system' && m.to === 'engineer_agent')).toBe(true);

    // ── 3. MEDIC DELEGIERT AN ENGINEER ──────────────────────────────
    comm.assignTask({
      from: 'medic_agent',
      to: 'engineer_agent',
      task: 'MC4-Stecker und Laderegler prüfen',
      description: 'Off-Grid Solarfehler diagnostizieren',
    });

    expect(kanban.getAll()).toHaveLength(2);
    expect(kanban.getAll()[1].assignee).toBe('engineer_agent');

    // ── 4. ENGINEER ARBEITET ───────────────────────────────────────
    const devTicketId = kanban.getAll()[1].id;
    kanban.moveTicket(devTicketId, 'in_progress');
    store.updateAgent('engineer_agent', { status: 'running' });

    // Log Events
    eventLog.addEvent({ type: 'tool_call', agentId: 'engineer_agent', toolName: 'read_file' });
    eventLog.addEvent({ type: 'thinking', agentId: 'engineer_agent', content: 'Laderegler oder Verkabelung?' });

    // Thought Decomposition
    const tree = decomposer.decompose('Laderegler oder Verkabelung? Erst Spannung messen. Dann Stecker reinigen.');
    expect(tree.root).toContain('?');
    expect(tree.children.length).toBeGreaterThanOrEqual(1);

    // Metrics
    metrics.recordThoughtFlow('engineer_agent');
    metrics.recordConnection('engineer_agent', 'solar', 'laderegler');
    expect(metrics.getTF('engineer_agent')).toBe(1);
    expect(metrics.getKC('engineer_agent')).toBe(1);

    // Knowledge Graph
    graph.addNode({ id: 'engineer_agent', type: 'agent', label: 'Mimi-Engineer' });
    graph.addNode({ id: 'solar', type: 'technology', label: 'Solar' });
    graph.addEdge({ from: 'engineer_agent', to: 'solar', type: 'diagnosed' });
    expect(graph.nodeCount).toBe(2);
    expect(graph.edgeCount).toBe(1);

    // Tool usage XP
    skills.onToolUsed('engineer_agent', 'web_search');
    expect(skills.getProfile('engineer_agent').skills.research).toBe(45); // 40 + 5

    // ── 5. ENGINEER REICHT EIN ─────────────────────────────────────
    comm.submitWork({
      from: 'engineer_agent',
      ticketId: devTicketId,
      result: 'Stecker gereinigt, Laderegler zeigt 12.7V',
      code: 'Messprotokoll: 12.7V Batterie, 18.4V Panel',
    });

    expect(kanban.getTicket(devTicketId).status).toBe('testing');

    // ── 6. SENSOR LEHNT AB (Erste Runde) ───────────────────────────
    const cqBefore = skills.getProfile('engineer_agent').skills.codeQuality;
    const bdBefore = skills.getProfile('engineer_agent').skills.bugDetection;

    comm.rejectWork({
      from: 'sensor_agent',
      ticketId: devTicketId,
      reason: 'Panelspannung fehlt',
      feedback: 'Bitte Panelspannung unter Last messen',
    });

    expect(kanban.getTicket(devTicketId).status).toBe('in_progress');
    // T-04 FIX: Kein XP bei Rejection — Developer hat noch nichts gefixt
    expect(skills.getProfile('engineer_agent').skills.bugDetection).toBe(bdBefore);

    // CorrectionJournal eintragen
    journal.addCorrection({
      agentId: 'engineer_agent',
      error: 'Panelspannung fehlt',
      fix: 'Panelspannung unter Last ergänzt',
      ticketId: devTicketId,
    });

    const prompt = journal.getContextPrompt('engineer_agent');
    expect(prompt).toContain('Panelspannung');

    // Error Topology
    graph.generateErrorTopology({
      error: 'Panelspannung fehlt',
      file: 'solar-checklist.md',
      agent: 'engineer_agent',
      sop: 'Solar-Diagnose',
    });
    expect(graph.nodeCount).toBeGreaterThanOrEqual(4);

    // ── 7. ENGINEER FIXT UND REICHT ERNEUT EIN ─────────────────────
    kanban.moveTicket(devTicketId, 'testing');

    // ── 8. SENSOR GENEHMIGT ────────────────────────────────────────
    comm.approveWork({ from: 'sensor_agent', ticketId: devTicketId });

    expect(kanban.getTicket(devTicketId).status).toBe('done');
    expect(skills.getProfile('engineer_agent').skills.codeQuality).toBe(cqBefore + 3);
    // T-04 FIX: bugDetection XP kommt JETZT beim Approve (Fix wurde geleistet)
    expect(skills.getProfile('engineer_agent').skills.bugDetection).toBe(bdBefore + 8);


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
    expect(isToolAllowed('medic_agent', 'run_shell')).toBe(false);
    expect(isToolAllowed('engineer_agent', 'read_file')).toBe(true);
    expect(isToolAllowed('sensor_agent', 'get_datetime')).toBe(true);

    // Delegation chain
    const chain = orch.getDelegationChain();
    expect(chain).toHaveLength(4);

    // Weakest skill
    const weakest = skills.getWeakestSkill('engineer_agent');
    expect(weakest.skill).toBe('architecture');

    // Thinking parser (Phase 1 - still works)
    const parser = new ThinkingStreamParser();
    parser.feed('<|think|>Test Gedanke<|/think|>Antwort');
    expect(parser.thinking).toBe('Test Gedanke');
    expect(parser.answer).toBe('Antwort');

    console.log('\n✅ E2E Pipeline komplett! Alle Module integriert.');
  });
});
