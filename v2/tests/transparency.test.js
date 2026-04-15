/**
 * ◑ MiMiNox v2 — Test: Event-Log + Topologie-Metriken + Gedankenbaum
 * Tasks 3.1, 3.2, 3.3, 3.7
 * TDD: Tests FIRST.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { EventLog } from '../server/transparency/event-log.js';
import { ThoughtDecomposer } from '../server/transparency/thought-decomposer.js';
import { TopologyMetrics } from '../server/transparency/topology-metrics.js';
import { StateStore } from '../server/state/store.js';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

function tmpDbPath() {
  return path.join(os.tmpdir(), `miminox-events-${Date.now()}-${Math.random().toString(36).slice(2)}.db`);
}

// ═══════════════════════════════════════════════════════════════════
// 3.2 Event-Log
// ═══════════════════════════════════════════════════════════════════

describe('Task 3.2: Real-time Event Log', () => {
  let store, log;

  beforeEach(() => {
    store = new StateStore(':memory:');
    log = new EventLog(store);
  });

  afterEach(() => store?.close());

  // GIVEN Event-Logger
  // WHEN ein Agent einen Tool-Call macht
  // THEN wird Event gespeichert
  it('[D] GIVEN log WHEN addEvent tool_call THEN persisted', () => {
    log.addEvent({
      type: 'tool_call',
      agentId: 'charlie_dev',
      toolName: 'read_file',
      args: { path: '/app/main.py' },
      result: 'content...',
    });

    const events = log.getEvents();
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('tool_call');
    expect(events[0].agent_id).toBe('charlie_dev');
  });

  // GIVEN mehrere Events
  // WHEN getEvents(agentId) aufgerufen wird
  // THEN nur Events dieses Agents
  it('[D] GIVEN events WHEN getEvents filtered THEN only matching', () => {
    log.addEvent({ type: 'thinking', agentId: 'charlie_dev', content: 'Hmm...' });
    log.addEvent({ type: 'tool_call', agentId: 'bob_cto', toolName: 'list_dir' });
    log.addEvent({ type: 'answer', agentId: 'charlie_dev', content: 'Done.' });

    const charlie = log.getEvents({ agentId: 'charlie_dev' });
    expect(charlie).toHaveLength(2);
    expect(charlie.every(e => e.agent_id === 'charlie_dev')).toBe(true);
  });

  // GIVEN Events
  // WHEN getEvents(type) aufgerufen wird
  // THEN nur Events dieses Typs
  it('[D] GIVEN events WHEN getEvents by type THEN filtered', () => {
    log.addEvent({ type: 'tool_call', agentId: 'charlie_dev', toolName: 'read_file' });
    log.addEvent({ type: 'thinking', agentId: 'charlie_dev', content: 'Hmm' });
    log.addEvent({ type: 'tool_call', agentId: 'bob_cto', toolName: 'list_dir' });

    const tools = log.getEvents({ type: 'tool_call' });
    expect(tools).toHaveLength(2);
  });

  // Subscriber
  it('[D] GIVEN log with subscriber WHEN addEvent THEN subscriber notified', () => {
    const events = [];
    log.onEvent(e => events.push(e));

    log.addEvent({ type: 'thinking', agentId: 'charlie_dev', content: 'Test' });

    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('thinking');
  });
});

// ═══════════════════════════════════════════════════════════════════
// 3.7 Audit-Trail Persistence
// ═══════════════════════════════════════════════════════════════════

describe('Task 3.7: Audit-Trail Persistence', () => {
  it('[D] GIVEN 10 events WHEN store closed and reopened THEN all events persist', () => {
    const dbPath = tmpDbPath();
    const store1 = new StateStore(dbPath);
    const log1 = new EventLog(store1);

    for (let i = 0; i < 10; i++) {
      log1.addEvent({ type: 'tool_call', agentId: 'charlie_dev', toolName: `tool_${i}` });
    }

    store1.close();

    const store2 = new StateStore(dbPath);
    const log2 = new EventLog(store2);
    const events = log2.getEvents();

    expect(events).toHaveLength(10);
    store2.close();
    try { fs.unlinkSync(dbPath); } catch {}
  });
});

// ═══════════════════════════════════════════════════════════════════
// 3.1 Thought Decomposer
// ═══════════════════════════════════════════════════════════════════

describe('Task 3.1: Thinking-Splitter + Dekomposition', () => {
  it('[D] GIVEN thinking text WHEN decompose THEN returns tree', () => {
    const decomposer = new ThoughtDecomposer();

    const text = 'Soll ich REST oder GraphQL nehmen? REST ist besser für MVPs. GraphQL ist für komplexe Queries.';
    const tree = decomposer.decompose(text);

    expect(tree).toBeDefined();
    expect(tree.root).toBeDefined();
    expect(tree.children.length).toBeGreaterThanOrEqual(1);
  });

  it('[D] GIVEN simple thinking WHEN decompose THEN has root text', () => {
    const decomposer = new ThoughtDecomposer();
    const tree = decomposer.decompose('REST ist besser.');

    expect(tree.root).toContain('REST');
    expect(tree.children).toHaveLength(0); // Simple = no children
  });

  it('[D] GIVEN multi-sentence WHEN decompose THEN splits into children', () => {
    const decomposer = new ThoughtDecomposer();
    const tree = decomposer.decompose(
      'Erst muss ich das Problem analysieren. Dann den Code schreiben. Danach Tests erstellen.'
    );

    expect(tree.children.length).toBeGreaterThanOrEqual(2);
  });

  it('[D] GIVEN thinking with question WHEN decompose THEN root is question', () => {
    const decomposer = new ThoughtDecomposer();
    const tree = decomposer.decompose(
      'Welche Datenbank? MongoDB ist flexibel. PostgreSQL hat ACID.'
    );

    expect(tree.root).toContain('?');
    expect(tree.children.length).toBeGreaterThanOrEqual(1);
  });
});

// ═══════════════════════════════════════════════════════════════════
// 3.3 Topologie-Metriken (TF/KC)
// ═══════════════════════════════════════════════════════════════════

describe('Task 3.3: Topologie-Metriken', () => {
  let store, metrics;

  beforeEach(() => {
    store = new StateStore(':memory:');
    metrics = new TopologyMetrics(store);
  });

  afterEach(() => store?.close());

  // GIVEN Agent mit 3 Gedankenflüssen
  // WHEN getTF aufgerufen
  // THEN gibt 3 zurück
  it('[D] GIVEN 3 thought flows WHEN getTF THEN returns 3', () => {
    metrics.recordThoughtFlow('charlie_dev');
    metrics.recordThoughtFlow('charlie_dev');
    metrics.recordThoughtFlow('charlie_dev');

    expect(metrics.getTF('charlie_dev')).toBe(3);
  });

  // GIVEN Agent mit 5 Kanten im Wissensgraph
  // WHEN getKC aufgerufen
  // THEN gibt 5 zurück
  it('[D] GIVEN 5 knowledge connections WHEN getKC THEN returns 5', () => {
    for (let i = 0; i < 5; i++) {
      metrics.recordConnection('charlie_dev', `node_${i}`, `node_${i + 1}`);
    }

    expect(metrics.getKC('charlie_dev')).toBe(5);
  });

  // Dashboard-Snapshot
  it('[D] GIVEN metrics WHEN getSnapshot THEN returns all agents', () => {
    metrics.recordThoughtFlow('charlie_dev');
    metrics.recordThoughtFlow('bob_cto');
    metrics.recordConnection('charlie_dev', 'a', 'b');

    const snapshot = metrics.getSnapshot();
    expect(snapshot.charlie_dev).toBeDefined();
    expect(snapshot.charlie_dev.tf).toBe(1);
    expect(snapshot.charlie_dev.kc).toBe(1);
    expect(snapshot.bob_cto.tf).toBe(1);
  });
});

// ── T-17: Vollständiger Audit-Log — args + result persistent ──────────────────

describe('T-17: Audit-Log — Tool-Call Metadata', () => {
  let store, log;
  beforeEach(() => { store = new StateStore(':memory:'); log = new EventLog(store); });
  afterEach(() => store?.close());

  // GIVEN tool_call mit args und result
  // WHEN Event persistiert
  // THEN tool_name, args (als String), result, timestamp alle abrufbar
  it('[T-17] GIVEN tool action WHEN logged THEN full metadata persisted', () => {
    log.addEvent({
      type:     'tool_call',
      agentId:  'charlie_dev',
      toolName: 'web_search',
      args:     { query: 'Express.js tutorial' },
      result:   '3 results found',
    });

    const events = log.getEvents({ agentId: 'charlie_dev' });
    expect(events[0].tool_name).toBe('web_search');
    expect(JSON.stringify(events[0].args)).toContain('Express.js');
    expect(events[0].result).toBe('3 results found');
    expect(events[0].timestamp).toBeDefined();
  });

  // GIVEN Events von mehreren Agenten mit toolName
  // WHEN getEvents({ agentId }) gefiltert
  // THEN nur Charlie's Events
  it('[T-17] GIVEN multiple agents WHEN filter by agentId THEN only correct events', () => {
    log.addEvent({ type: 'tool_call', agentId: 'charlie_dev', toolName: 'read_file', result: 'ok' });
    log.addEvent({ type: 'tool_call', agentId: 'bob_cto',    toolName: 'list_dir',  result: 'ok' });
    log.addEvent({ type: 'tool_call', agentId: 'charlie_dev', toolName: 'run_shell', result: 'ok' });

    const charlieEvents = log.getEvents({ agentId: 'charlie_dev' });
    expect(charlieEvents).toHaveLength(2);
    expect(charlieEvents.every(e => e.agent_id === 'charlie_dev')).toBe(true);
  });
});

// ── T-19: ThoughtDecomposer — LLM-gestützte Dekomposition ────────────────────

describe('T-19: ThoughtDecomposer — decomposeWithLLM', () => {
  const decomposer = new ThoughtDecomposer();

  // GIVEN LLM-Provider gibt typenreiche Baumstruktur zurück
  // WHEN decomposeWithLLM aufgerufen
  // THEN tree hat conclusion-Knoten und dependsOn-Referenzen
  it('[T-19] GIVEN mock LLM WHEN decomposeWithLLM THEN returns rich typed tree', async () => {
    const mockLLM = {
      chat: async () => ({
        message: {
          content: JSON.stringify({
            root: 'Wie soll die API aufgebaut werden?',
            children: [
              { text: 'REST ist einfacher',    type: 'reasoning',     dependsOn: [] },
              { text: 'GraphQL ist flexibler', type: 'consideration', dependsOn: [] },
              { text: 'REST für MVP',          type: 'conclusion',    dependsOn: [0, 1] },
            ],
          }),
        },
      }),
    };

    const tree = await decomposer.decomposeWithLLM(
      'REST oder GraphQL? REST ist einfacher. GraphQL ist flexibler. REST für MVP.',
      mockLLM,
    );

    expect(tree.children.some(c => c.type === 'conclusion')).toBe(true);
    expect(tree.children.some(c => c.dependsOn?.length > 0)).toBe(true);
    expect(tree.root).toContain('API');
  });

  // GIVEN LLM schlägt fehl (invalid JSON)
  // WHEN decomposeWithLLM aufgerufen
  // THEN Fallback auf heuristischen decompose()
  it('[T-19] GIVEN LLM returns invalid JSON WHEN decomposeWithLLM THEN falls back to heuristic', async () => {
    const brokenLLM = {
      chat: async () => ({ message: { content: 'kein json' } }),
    };

    const text = 'REST oder GraphQL? REST ist einfacher.';
    const tree = await decomposer.decomposeWithLLM(text, brokenLLM);

    // Fallback muss immer etwas zurückgeben
    expect(tree.root).toBeDefined();
    expect(Array.isArray(tree.children)).toBe(true);
  });

  // GIVEN kein LLM-Provider
  // WHEN decomposeWithLLM null übergeben
  // THEN heuristischer Fallback (kein Crash)
  it('[T-19] GIVEN null LLM WHEN decomposeWithLLM THEN uses heuristic fallback', async () => {
    const tree = await decomposer.decomposeWithLLM('Was soll ich tun? Erst analysieren.', null);
    expect(tree.root).toBeDefined();
  });
});
