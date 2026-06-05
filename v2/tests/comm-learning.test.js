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
    for (const id of ['medic_agent', 'engineer_agent', 'navigator_agent', 'sensor_agent']) {
      store.createAgent({ id, role: loadRole(id).role, status: 'running' });
      skills.initProfile(id, loadRole(id).skills);
    }
  });

  afterEach(() => store?.close());

  // ── assign_task ───────────────────────────────────────────────────

  // GIVEN medic_agent ruft assign_task auf
  // WHEN to: "engineer_agent", task: "Solar prüfen"
  // THEN neues Ticket im Kanban + Chat-Nachricht an Engineer
  it('[D] GIVEN medic WHEN assign_task to engineer THEN ticket + chat message', () => {
    const result = comm.assignTask({
      from: 'medic_agent',
      to: 'engineer_agent',
      task: 'Solar prüfen',
      description: 'Off-Grid Solaranlage liefert keinen Strom',
    });

    expect(result.ticketId).toBeGreaterThan(0);

    const tickets = kanban.getAll();
    expect(tickets).toHaveLength(1);
    expect(tickets[0].title).toBe('Solar prüfen');
    expect(tickets[0].assignee).toBe('engineer_agent');
    expect(tickets[0].status).toBe('backlog');

    const history = bus.getHistory();
    expect(history.some(m => m.content.includes('Solar prüfen'))).toBe(true);
  });

  // ── submit_work ───────────────────────────────────────────────────

  // GIVEN engineer_agent hat Ticket bearbeitet
  // WHEN submit_work aufgerufen wird
  // THEN Ticket → testing, Sensor erhält Nachricht
  it('[D] GIVEN engineer with ticket WHEN submit_work THEN ticket to testing', () => {
    const ticketId = kanban.createTicket({
      title: 'Solar prüfen', assignee: 'engineer_agent', createdBy: 'medic_agent',
    });
    kanban.moveTicket(ticketId, 'in_progress');

    comm.submitWork({
      from: 'engineer_agent',
      ticketId,
      result: 'Steckverbindungen gereinigt',
      code: 'MC4-Kontakte geprüft',
    });

    expect(kanban.getTicket(ticketId).status).toBe('testing');

    const history = bus.getHistory();
    expect(history.some(m => m.to === 'sensor_agent' && m.content.includes('Steckverbindungen'))).toBe(true);
  });

  // ── reject_work ───────────────────────────────────────────────────

  // T-04 RED: GIVEN sensor_agent reviewed Ticket
  // WHEN reject_work aufgerufen wird
  // THEN Ticket → in_progress, Engineer erhält Feedback
  // THEN Engineer bekommt KEINE bugDetection-XP (noch kein Fix geleistet!)
  it('[T-04] GIVEN sensor rejects WHEN rejectWork THEN NO bugDetection XP', () => {
    const ticketId = kanban.createTicket({
      title: 'Solar prüfen', assignee: 'engineer_agent', createdBy: 'medic_agent',
    });
    kanban.moveTicket(ticketId, 'in_progress');
    kanban.moveTicket(ticketId, 'testing');

    const bugBefore = skills.getProfile('engineer_agent').skills.bugDetection;

    comm.rejectWork({
      from: 'sensor_agent',
      ticketId,
      reason: 'Spannung nicht gemessen',
      feedback: 'Bitte Multimeter-Werte nachtragen',
    });

    expect(kanban.getTicket(ticketId).status).toBe('in_progress');

    const history = bus.getHistory();
    expect(history.some(m => m.to === 'engineer_agent' && m.content.includes('Spannung'))).toBe(true);

    // ← KORRIGIERT: Kein XP bei purer Rejection (noch kein Fix!)
    const bugAfter = skills.getProfile('engineer_agent').skills.bugDetection;
    expect(bugAfter).toBe(bugBefore); // KEIN XP-Anstieg
  });

  // T-04 RED: GIVEN Ticket wurde vorher rejected
  // WHEN approve_work aufgerufen wird (Fix wurde geliefert)
  // THEN erhält Charlie bugDetection XP (Fix war erfolgreich)
  it('[T-04] GIVEN prior rejection WHEN approve after fix THEN bugDetection XP', () => {
    const ticketId = kanban.createTicket({
      title: 'Solar prüfen', assignee: 'engineer_agent', createdBy: 'medic_agent',
    });
    kanban.moveTicket(ticketId, 'in_progress');
    kanban.moveTicket(ticketId, 'testing');

    // Erst rejection
    comm.rejectWork({ from: 'sensor_agent', ticketId, reason: 'Spannung nicht gemessen' });
    // Engineer fixt → wieder in testing
    kanban.moveTicket(ticketId, 'testing');

    const bugBefore = skills.getProfile('engineer_agent').skills.bugDetection;
    const cqBefore  = skills.getProfile('engineer_agent').skills.codeQuality;

    // Sensor approved den Fix
    comm.approveWork({ from: 'sensor_agent', ticketId });

    expect(kanban.getTicket(ticketId).status).toBe('done');

    const bugAfter = skills.getProfile('engineer_agent').skills.bugDetection;
    const cqAfter  = skills.getProfile('engineer_agent').skills.codeQuality;

    // Fix-XP wird bei Approve vergeben, wenn Ticket vorher rejected war
    expect(bugAfter).toBe(bugBefore + 8);  // bugDetection XP für den Fix
    expect(cqAfter).toBe(cqBefore + 3);    // codeQuality XP wie immer
  });

  // ── approve_work (ohne vorherige Rejection) ───────────────────────

  it('[D] GIVEN sensor approves fresh WHEN approve_work THEN ticket done + codeQuality XP only', () => {
    const ticketId = kanban.createTicket({
      title: 'Solar prüfen', assignee: 'engineer_agent', createdBy: 'medic_agent',
    });
    kanban.moveTicket(ticketId, 'in_progress');
    kanban.moveTicket(ticketId, 'testing');

    const bugBefore = skills.getProfile('engineer_agent').skills.bugDetection;
    const cqBefore  = skills.getProfile('engineer_agent').skills.codeQuality;

    comm.approveWork({ from: 'sensor_agent', ticketId });

    expect(kanban.getTicket(ticketId).status).toBe('done');

    const bugAfter = skills.getProfile('engineer_agent').skills.bugDetection;
    const cqAfter  = skills.getProfile('engineer_agent').skills.codeQuality;

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

  // GIVEN engineer_agent macht Fehler (Review-Rejection)
  // WHEN der Fehler ins Journal geschrieben wird
  // THEN enthält getRecent den Eintrag
  it('[D] GIVEN error WHEN addCorrection THEN getRecent returns it', () => {
    journal.addCorrection({
      agentId: 'engineer_agent',
      error: 'Spannung nicht gemessen',
      fix: 'Multimeter-Werte ergänzt',
      ticketId: 3,
    });

    const corrections = journal.getRecent('engineer_agent', 5);
    expect(corrections).toHaveLength(1);
    expect(corrections[0].error).toBe('Spannung nicht gemessen');
    expect(corrections[0].fix).toBe('Multimeter-Werte ergänzt');
  });

  // GIVEN mehrere Korrekturen
  // WHEN getRecent(3) aufgerufen wird
  // THEN maximal 3 zurück, neueste zuerst
  it('[D] GIVEN 5 corrections WHEN getRecent(3) THEN returns 3 newest', () => {
    for (let i = 1; i <= 5; i++) {
      journal.addCorrection({
        agentId: 'engineer_agent',
        error: `Fehler ${i}`,
        fix: `Fix ${i}`,
        ticketId: i,
      });
    }

    const corrections = journal.getRecent('engineer_agent', 3);
    expect(corrections).toHaveLength(3);
    expect(corrections[0].error).toBe('Fehler 5'); // newest first
  });

  // ── Context-Injection ─────────────────────────────────────────────

  // GIVEN Korrekturen im Journal
  // WHEN getContextPrompt aufgerufen wird
  // THEN kommt ein Prompt-Snippet zurück
  it('[D] GIVEN corrections WHEN getContextPrompt THEN returns prompt snippet', () => {
    journal.addCorrection({
      agentId: 'engineer_agent',
      error: 'MC4-Kontakt nicht isoliert',
      fix: 'Stecker gereinigt und isoliert',
      ticketId: 1,
    });

    const prompt = journal.getContextPrompt('engineer_agent');
    expect(prompt).toContain('MC4-Kontakt');
    expect(prompt).toContain('Stecker gereinigt');
    expect(prompt).toContain('Fehler');
  });

  // GIVEN keine Korrekturen
  // WHEN getContextPrompt aufgerufen wird
  // THEN kommt leerer String
  it('[D] GIVEN no corrections WHEN getContextPrompt THEN returns empty', () => {
    const prompt = journal.getContextPrompt('engineer_agent');
    expect(prompt).toBe('');
  });

  // ── Schwächen-Erkennung ───────────────────────────────────────────

  it('[D] GIVEN agent with weak architecture WHEN getWeakestSkill THEN returns architecture', () => {
    const skills = new SkillSystem(store);
    skills.initProfile('engineer_agent', loadRole('engineer_agent').skills);

    const weakest = skills.getWeakestSkill('engineer_agent');
    expect(weakest.skill).toBe('architecture');
    expect(weakest.value).toBe(25);
  });
});
