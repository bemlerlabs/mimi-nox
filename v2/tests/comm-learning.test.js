/**
 * ◑ MiMiNox v2 — Test: Kommunikations-Tools + Agent-Selbstlernen
 * Tasks 2.3 + 2.8
 * TDD: Tests FIRST.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { CommTools } from '../server/agents/comm-tools.js';
import { CorrectionJournal } from '../server/agents/correction-journal.js';
import { StateStore } from '../server/state/store.js';
import { ChatBus } from '../server/agents/chat-bus.js';
import { KanbanEngine } from '../server/agents/kanban.js';
import { SkillSystem } from '../server/agents/skill-system.js';
import { loadRole } from '../server/agents/roles.js';

describe('Task 2.3: Kommunikations-Tools', () => {
  let store, bus, kanban, skills, comm;

  beforeEach(() => {
    store = new StateStore(':memory:');
    bus = new ChatBus(store);
    kanban = new KanbanEngine(store);
    skills = new SkillSystem(store);
    comm = new CommTools({ store, bus, kanban, skills });

    // Init agents
    for (const id of ['alice_ceo', 'bob_cto', 'charlie_dev', 'diana_qa']) {
      store.createAgent({ id, role: loadRole(id).role, status: 'running' });
      skills.initProfile(id, loadRole(id).skills);
    }
  });

  afterEach(() => store?.close());

  // ── assign_task ───────────────────────────────────────────────────

  // GIVEN alice_ceo ruft assign_task auf
  // WHEN to: "bob_cto", task: "API designen"
  // THEN neues Ticket im Kanban + Chat-Nachricht an Bob
  it('[D] GIVEN alice WHEN assign_task to bob THEN ticket + chat message', () => {
    const result = comm.assignTask({
      from: 'alice_ceo',
      to: 'bob_cto',
      task: 'API designen',
      description: 'REST-API für Todos mit Express',
    });

    expect(result.ticketId).toBeGreaterThan(0);

    const tickets = kanban.getAll();
    expect(tickets).toHaveLength(1);
    expect(tickets[0].title).toBe('API designen');
    expect(tickets[0].assignee).toBe('bob_cto');
    expect(tickets[0].status).toBe('backlog');

    const history = bus.getHistory();
    expect(history.some(m => m.content.includes('API designen'))).toBe(true);
  });

  // ── submit_work ───────────────────────────────────────────────────

  // GIVEN charlie_dev hat Ticket bearbeitet
  // WHEN submit_work aufgerufen wird
  // THEN Ticket → testing, Diana erhält Nachricht
  it('[D] GIVEN charlie with ticket WHEN submit_work THEN ticket to testing', () => {
    const ticketId = kanban.createTicket({
      title: 'API bauen', assignee: 'charlie_dev', createdBy: 'bob_cto',
    });
    kanban.moveTicket(ticketId, 'in_progress');

    comm.submitWork({
      from: 'charlie_dev',
      ticketId,
      result: 'Code fertig',
      code: 'app.get("/api/todos", ...)',
    });

    expect(kanban.getTicket(ticketId).status).toBe('testing');

    const history = bus.getHistory();
    expect(history.some(m => m.to === 'diana_qa' && m.content.includes('Code fertig'))).toBe(true);
  });

  // ── reject_work ───────────────────────────────────────────────────

  // T-04 RED: GIVEN diana_qa reviewed Ticket
  // WHEN reject_work aufgerufen wird
  // THEN Ticket → in_progress, Charlie erhält Feedback
  // THEN Charlie bekommt KEINE bugDetection-XP (noch kein Fix geleistet!)
  it('[T-04] GIVEN diana rejects WHEN rejectWork THEN NO bugDetection XP', () => {
    const ticketId = kanban.createTicket({
      title: 'API bauen', assignee: 'charlie_dev', createdBy: 'bob_cto',
    });
    kanban.moveTicket(ticketId, 'in_progress');
    kanban.moveTicket(ticketId, 'testing');

    const bugBefore = skills.getProfile('charlie_dev').skills.bugDetection;

    comm.rejectWork({
      from: 'diana_qa',
      ticketId,
      reason: 'Keine Tests',
      feedback: 'Bitte pytest hinzufügen',
    });

    expect(kanban.getTicket(ticketId).status).toBe('in_progress');

    const history = bus.getHistory();
    expect(history.some(m => m.to === 'charlie_dev' && m.content.includes('Keine Tests'))).toBe(true);

    // ← KORRIGIERT: Kein XP bei purer Rejection (noch kein Fix!)
    const bugAfter = skills.getProfile('charlie_dev').skills.bugDetection;
    expect(bugAfter).toBe(bugBefore); // KEIN XP-Anstieg
  });

  // T-04 RED: GIVEN Ticket wurde vorher rejected
  // WHEN approve_work aufgerufen wird (Fix wurde geliefert)
  // THEN erhält Charlie bugDetection XP (Fix war erfolgreich)
  it('[T-04] GIVEN prior rejection WHEN approve after fix THEN bugDetection XP', () => {
    const ticketId = kanban.createTicket({
      title: 'API bauen', assignee: 'charlie_dev', createdBy: 'bob_cto',
    });
    kanban.moveTicket(ticketId, 'in_progress');
    kanban.moveTicket(ticketId, 'testing');

    // Erst rejection
    comm.rejectWork({ from: 'diana_qa', ticketId, reason: 'Keine Tests' });
    // Charlie fixt → wieder in testing
    kanban.moveTicket(ticketId, 'testing');

    const bugBefore = skills.getProfile('charlie_dev').skills.bugDetection;
    const cqBefore  = skills.getProfile('charlie_dev').skills.codeQuality;

    // Diana approved den Fix
    comm.approveWork({ from: 'diana_qa', ticketId });

    expect(kanban.getTicket(ticketId).status).toBe('done');

    const bugAfter = skills.getProfile('charlie_dev').skills.bugDetection;
    const cqAfter  = skills.getProfile('charlie_dev').skills.codeQuality;

    // Fix-XP wird bei Approve vergeben, wenn Ticket vorher rejected war
    expect(bugAfter).toBe(bugBefore + 8);  // bugDetection XP für den Fix
    expect(cqAfter).toBe(cqBefore + 3);    // codeQuality XP wie immer
  });

  // ── approve_work (ohne vorherige Rejection) ───────────────────────

  it('[D] GIVEN diana approves fresh WHEN approve_work THEN ticket done + codeQuality XP only', () => {
    const ticketId = kanban.createTicket({
      title: 'API bauen', assignee: 'charlie_dev', createdBy: 'bob_cto',
    });
    kanban.moveTicket(ticketId, 'in_progress');
    kanban.moveTicket(ticketId, 'testing');

    const bugBefore = skills.getProfile('charlie_dev').skills.bugDetection;
    const cqBefore  = skills.getProfile('charlie_dev').skills.codeQuality;

    comm.approveWork({ from: 'diana_qa', ticketId });

    expect(kanban.getTicket(ticketId).status).toBe('done');

    const bugAfter = skills.getProfile('charlie_dev').skills.bugDetection;
    const cqAfter  = skills.getProfile('charlie_dev').skills.codeQuality;

    expect(cqAfter).toBe(cqBefore + 3);  // codeQuality immer
    expect(bugAfter).toBe(bugBefore);     // kein bugDetection (kein Fix nötig)
  });
});

describe('Task 2.8: Agent-Selbstlernen', () => {
  let store, journal;

  beforeEach(() => {
    store = new StateStore(':memory:');
    journal = new CorrectionJournal(store);
  });

  afterEach(() => store?.close());

  // ── CorrectionJournal ─────────────────────────────────────────────

  // GIVEN charlie macht Fehler (QA-Rejection)
  // WHEN der Fehler ins Journal geschrieben wird
  // THEN enthält getRecent den Eintrag
  it('[D] GIVEN error WHEN addCorrection THEN getRecent returns it', () => {
    journal.addCorrection({
      agentId: 'charlie_dev',
      error: 'Keine Tests geschrieben',
      fix: 'pytest Tests hinzugefügt',
      ticketId: 3,
    });

    const corrections = journal.getRecent('charlie_dev', 5);
    expect(corrections).toHaveLength(1);
    expect(corrections[0].error).toBe('Keine Tests geschrieben');
    expect(corrections[0].fix).toBe('pytest Tests hinzugefügt');
  });

  // GIVEN mehrere Korrekturen
  // WHEN getRecent(3) aufgerufen wird
  // THEN maximal 3 zurück, neueste zuerst
  it('[D] GIVEN 5 corrections WHEN getRecent(3) THEN returns 3 newest', () => {
    for (let i = 1; i <= 5; i++) {
      journal.addCorrection({
        agentId: 'charlie_dev',
        error: `Fehler ${i}`,
        fix: `Fix ${i}`,
        ticketId: i,
      });
    }

    const corrections = journal.getRecent('charlie_dev', 3);
    expect(corrections).toHaveLength(3);
    expect(corrections[0].error).toBe('Fehler 5'); // newest first
  });

  // ── Context-Injection ─────────────────────────────────────────────

  // GIVEN Korrekturen im Journal
  // WHEN getContextPrompt aufgerufen wird
  // THEN kommt ein Prompt-Snippet zurück
  it('[D] GIVEN corrections WHEN getContextPrompt THEN returns prompt snippet', () => {
    journal.addCorrection({
      agentId: 'charlie_dev',
      error: 'SQL-Injection nicht verhindert',
      fix: 'Parameterized Queries verwendet',
      ticketId: 1,
    });

    const prompt = journal.getContextPrompt('charlie_dev');
    expect(prompt).toContain('SQL-Injection');
    expect(prompt).toContain('Parameterized Queries');
    expect(prompt).toContain('Fehler');
  });

  // GIVEN keine Korrekturen
  // WHEN getContextPrompt aufgerufen wird
  // THEN kommt leerer String
  it('[D] GIVEN no corrections WHEN getContextPrompt THEN returns empty', () => {
    const prompt = journal.getContextPrompt('charlie_dev');
    expect(prompt).toBe('');
  });

  // ── Schwächen-Erkennung ───────────────────────────────────────────

  it('[D] GIVEN agent with weak architecture WHEN getWeakestSkill THEN returns architecture', () => {
    const skills = new SkillSystem(store);
    skills.initProfile('charlie_dev', loadRole('charlie_dev').skills);

    const weakest = skills.getWeakestSkill('charlie_dev');
    expect(weakest.skill).toBe('architecture'); // 25 is lowest for charlie
    expect(weakest.value).toBe(25);
  });
});
