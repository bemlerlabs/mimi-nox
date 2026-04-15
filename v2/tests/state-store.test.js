/**
 * ◑ MiMiNox v2 — Test: SQLite State Store
 * Task 1.4: Shared State Store
 * TDD: Tests FIRST, then implementation.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { StateStore } from '../server/state/store.js';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

function tmpDbPath() {
  return path.join(os.tmpdir(), `miminox-test-${Date.now()}-${Math.random().toString(36).slice(2)}.db`);
}

describe('Task 1.4: SQLite State Store', () => {
  let store, dbPath;

  beforeEach(() => {
    dbPath = tmpDbPath();
    store = new StateStore(dbPath);
  });

  afterEach(() => {
    store?.close();
    try { fs.unlinkSync(dbPath); } catch {}
  });

  // ── Agent CRUD ────────────────────────────────────────────────────

  // GIVEN ein leerer StateStore
  // WHEN createAgent aufgerufen wird
  // THEN gibt getAgent das Objekt zurück
  it('[D] GIVEN empty store WHEN createAgent THEN getAgent returns it', () => {
    store.createAgent({ id: 'charlie', role: 'developer', status: 'spawned' });
    const agent = store.getAgent('charlie');
    expect(agent).toBeDefined();
    expect(agent.id).toBe('charlie');
    expect(agent.role).toBe('developer');
    expect(agent.status).toBe('spawned');
  });

  // GIVEN ein leerer StateStore
  // WHEN createAgent aufgerufen wird
  // THEN enthält getAllAgents genau 1 Agent
  it('[D] GIVEN empty store WHEN createAgent THEN getAllAgents has 1', () => {
    store.createAgent({ id: 'charlie', role: 'developer', status: 'spawned' });
    const all = store.getAllAgents();
    expect(all).toHaveLength(1);
    expect(all[0].id).toBe('charlie');
  });

  // ── Agent Lifecycle ───────────────────────────────────────────────

  // GIVEN ein Agent mit Status "spawned"
  // WHEN updateAgent aufgerufen wird
  // THEN ändert sich der Status
  it('[D] GIVEN spawned agent WHEN updateAgent THEN status changes', () => {
    store.createAgent({ id: 'charlie', role: 'developer', status: 'spawned' });
    store.updateAgent('charlie', { status: 'running' });
    expect(store.getAgent('charlie').status).toBe('running');

    store.updateAgent('charlie', { status: 'done', result: 'Code fertig' });
    const agent = store.getAgent('charlie');
    expect(agent.status).toBe('done');
    expect(agent.result).toBe('Code fertig');
  });

  // ── Persistenz ────────────────────────────────────────────────────

  // GIVEN ein Store mit 3 Agenten und 5 Chat-Nachrichten
  // WHEN der Store geschlossen und neu geöffnet wird
  // THEN sind alle Daten noch da
  it('[D] GIVEN store with data WHEN closed and reopened THEN data persists', () => {
    store.createAgent({ id: 'alice', role: 'ceo', status: 'running' });
    store.createAgent({ id: 'bob', role: 'cto', status: 'running' });
    store.createAgent({ id: 'charlie', role: 'developer', status: 'spawned' });

    store.addChatMessage({ from: 'alice', to: 'bob', content: 'Sprint starten', type: 'directive' });
    store.addChatMessage({ from: 'bob', to: 'charlie', content: 'API bauen', type: 'task' });
    store.addChatMessage({ from: 'charlie', to: 'bob', content: 'Fertig', type: 'result' });
    store.addChatMessage({ from: 'bob', to: 'alice', content: 'Phase 1 done', type: 'status' });
    store.addChatMessage({ from: 'alice', to: 'all', content: 'Ship it', type: 'directive' });

    store.close();

    // Reopen
    const store2 = new StateStore(dbPath);
    expect(store2.getAllAgents()).toHaveLength(3);
    expect(store2.getChatHistory()).toHaveLength(5);
    store2.close();
  });

  // ── Pub/Sub Events ────────────────────────────────────────────────

  // GIVEN ein Store mit Subscriber
  // WHEN updateAgent aufgerufen wird
  // THEN erhält der Subscriber ein Event
  it('[D] GIVEN store with subscriber WHEN updateAgent THEN subscriber gets event', () => {
    const events = [];
    store.subscribe((event) => events.push(event));

    store.createAgent({ id: 'charlie', role: 'developer', status: 'spawned' });
    store.updateAgent('charlie', { status: 'running' });

    expect(events.length).toBeGreaterThanOrEqual(1);
    const updateEvent = events.find(e => e.type === 'agent_updated');
    expect(updateEvent).toBeDefined();
    expect(updateEvent.agentId).toBe('charlie');
    expect(updateEvent.status).toBe('running');
  });

  // ── Chat Messages ─────────────────────────────────────────────────

  it('[D] GIVEN store WHEN addChatMessage THEN getChatHistory returns it', () => {
    store.addChatMessage({ from: 'alice', to: 'bob', content: 'Hallo', type: 'greeting' });
    const history = store.getChatHistory();
    expect(history).toHaveLength(1);
    expect(history[0].from).toBe('alice');
    expect(history[0].to).toBe('bob');
    expect(history[0].content).toBe('Hallo');
    expect(history[0].timestamp).toBeDefined();
  });

  // ── Tickets ───────────────────────────────────────────────────────

  it('[D] GIVEN store WHEN createTicket THEN getTickets returns it', () => {
    store.createTicket({ title: 'API bauen', assignee: 'charlie', createdBy: 'bob' });
    const tickets = store.getTickets();
    expect(tickets).toHaveLength(1);
    expect(tickets[0].title).toBe('API bauen');
    expect(tickets[0].status).toBe('backlog');
    expect(tickets[0].assignee).toBe('charlie');
  });

  it('[D] GIVEN ticket WHEN updateTicketStatus THEN status changes', () => {
    const id = store.createTicket({ title: 'API bauen', assignee: 'charlie', createdBy: 'bob' });
    store.updateTicketStatus(id, 'in_progress');
    expect(store.getTickets()[0].status).toBe('in_progress');
  });
});
