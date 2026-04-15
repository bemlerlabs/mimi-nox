/**
 * ◑ MiMiNox v2 — Test: Chat-Bus + Kanban-Engine
 * Tasks 2.4 + 2.5: Firmen-Chat und Kanban-Board
 * TDD: Tests FIRST.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { ChatBus } from '../server/agents/chat-bus.js';
import { KanbanEngine } from '../server/agents/kanban.js';
import { StateStore } from '../server/state/store.js';

describe('Task 2.4: Firmen-Chat Bus', () => {
  let store, bus;

  beforeEach(() => {
    store = new StateStore(':memory:');
    bus = new ChatBus(store);
  });

  afterEach(() => store?.close());

  // GIVEN der Chat-Bus
  // WHEN bus.send aufgerufen wird
  // THEN wird die Nachricht persistiert
  it('[D] GIVEN bus WHEN send THEN message persisted in store', () => {
    bus.send({ from: 'alice_ceo', to: 'bob_cto', content: 'Sprint starten', type: 'directive' });
    const history = store.getChatHistory();
    expect(history).toHaveLength(1);
    expect(history[0].from).toBe('alice_ceo');
    expect(history[0].content).toBe('Sprint starten');
  });

  // GIVEN der Chat-Bus
  // WHEN bus.send aufgerufen wird
  // THEN erhalten alle Subscriber ein Event
  it('[D] GIVEN bus with subscriber WHEN send THEN subscriber notified', () => {
    const events = [];
    bus.onMessage((msg) => events.push(msg));

    bus.send({ from: 'alice_ceo', to: 'bob_cto', content: 'Los', type: 'directive' });

    expect(events).toHaveLength(1);
    expect(events[0].from).toBe('alice_ceo');
    expect(events[0].content).toBe('Los');
  });

  // GIVEN der Chat-Bus mit 4 Agenten
  // WHEN bus.broadcast aufgerufen wird
  // THEN erhalten alle die Nachricht
  it('[D] GIVEN bus WHEN broadcast THEN stored as to="all"', () => {
    bus.broadcast({ from: 'alice_ceo', content: 'Alle auf Sprint fokussieren' });
    const history = store.getChatHistory();
    expect(history).toHaveLength(1);
    expect(history[0].to).toBe('all');
  });

  // GIVEN Nachrichten im Chat
  // WHEN getHistory aufgerufen wird
  // THEN chronologisch sortiert
  it('[D] GIVEN multiple messages WHEN getHistory THEN chronological', () => {
    bus.send({ from: 'alice_ceo', to: 'bob_cto', content: 'Msg 1', type: 'directive' });
    bus.send({ from: 'bob_cto', to: 'charlie_dev', content: 'Msg 2', type: 'task' });
    bus.send({ from: 'charlie_dev', to: 'bob_cto', content: 'Msg 3', type: 'result' });

    const history = bus.getHistory();
    expect(history).toHaveLength(3);
    expect(history[0].content).toBe('Msg 1');
    expect(history[2].content).toBe('Msg 3');
  });

  // Nachrichten für einen bestimmten Agent filtern
  it('[D] GIVEN messages WHEN getMessagesFor("bob_cto") THEN only his messages', () => {
    bus.send({ from: 'alice_ceo', to: 'bob_cto', content: 'Für Bob', type: 'directive' });
    bus.send({ from: 'alice_ceo', to: 'charlie_dev', content: 'Für Charlie', type: 'task' });
    bus.broadcast({ from: 'alice_ceo', content: 'Für alle' });

    const bobMsgs = bus.getMessagesFor('bob_cto');
    expect(bobMsgs).toHaveLength(2); // Direct + broadcast
    expect(bobMsgs.every(m => m.to === 'bob_cto' || m.to === 'all')).toBe(true);
  });
});

describe('Task 2.5: Kanban-Engine', () => {
  let store, kanban;

  beforeEach(() => {
    store = new StateStore(':memory:');
    kanban = new KanbanEngine(store);
  });

  afterEach(() => store?.close());

  // GIVEN eine leere Kanban-Engine
  // WHEN createTicket aufgerufen wird
  // THEN hat Status "backlog" und eine ID
  it('[D] GIVEN empty kanban WHEN createTicket THEN has backlog status', () => {
    const id = kanban.createTicket({ title: 'API designen', assignee: 'charlie_dev', createdBy: 'bob_cto' });
    expect(id).toBeGreaterThan(0);
    const tickets = kanban.getAll();
    expect(tickets).toHaveLength(1);
    expect(tickets[0].status).toBe('backlog');
    expect(tickets[0].title).toBe('API designen');
  });

  // GIVEN ein Ticket
  // WHEN moveTicket durch gültige Status wechselt
  // THEN wird ticket_moved Event emittiert
  it('[D] GIVEN ticket WHEN valid transitions THEN events emitted', () => {
    const events = [];
    store.subscribe((e) => { if (e.type === 'ticket_moved') events.push(e); });

    const id = kanban.createTicket({ title: 'Test', assignee: 'charlie_dev', createdBy: 'bob_cto' });

    kanban.moveTicket(id, 'in_progress');
    kanban.moveTicket(id, 'testing');
    kanban.moveTicket(id, 'done');

    expect(events).toHaveLength(3);
    expect(events[0].status).toBe('in_progress');
    expect(events[1].status).toBe('testing');
    expect(events[2].status).toBe('done');
  });

  // GIVEN ein Ticket mit Status "backlog"
  // WHEN ungültiger Übergang versucht wird
  // THEN wird ein Error geworfen
  it('[D] GIVEN backlog ticket WHEN move to done THEN throws', () => {
    const id = kanban.createTicket({ title: 'Test', assignee: 'charlie_dev', createdBy: 'bob_cto' });
    expect(() => kanban.moveTicket(id, 'done')).toThrow();
  });

  // GIVEN rejected Ticket
  // WHEN zurück nach in_progress
  // THEN erlaubt (Fix-Zyklus)
  it('[D] GIVEN testing ticket WHEN rejected back to in_progress THEN allowed', () => {
    const id = kanban.createTicket({ title: 'Test', assignee: 'charlie_dev', createdBy: 'bob_cto' });
    kanban.moveTicket(id, 'in_progress');
    kanban.moveTicket(id, 'testing');
    kanban.moveTicket(id, 'in_progress'); // QA rejection → back to dev
    expect(kanban.getTicket(id).status).toBe('in_progress');
  });

  // Grouped by status
  it('[D] GIVEN tickets in various states WHEN getGrouped THEN returns categories', () => {
    const id1 = kanban.createTicket({ title: 'T1', assignee: 'c', createdBy: 'b' });
    const id2 = kanban.createTicket({ title: 'T2', assignee: 'c', createdBy: 'b' });
    const id3 = kanban.createTicket({ title: 'T3', assignee: 'c', createdBy: 'b' });

    kanban.moveTicket(id2, 'in_progress');
    kanban.moveTicket(id3, 'in_progress');
    kanban.moveTicket(id3, 'testing');

    const grouped = kanban.getGrouped();
    expect(grouped.backlog).toHaveLength(1);
    expect(grouped.in_progress).toHaveLength(1);
    expect(grouped.testing).toHaveLength(1);
    expect(grouped.done).toHaveLength(0);
  });
});
