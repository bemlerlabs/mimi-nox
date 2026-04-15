/**
 * ◑ MiMiNox v2 — Test: Knowledge Graph + Topologie-Puls + Graph-Query
 * Tasks 3.4, 3.5, 3.6, 3.8
 * TDD: Tests FIRST.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { KnowledgeGraph } from '../server/transparency/knowledge-graph.js';
import { StateStore } from '../server/state/store.js';

// ═══════════════════════════════════════════════════════════════════
// 3.4 Knowledge Graph Engine
// ═══════════════════════════════════════════════════════════════════

describe('Task 3.4: Knowledge Graph Engine', () => {
  let graph;

  beforeEach(() => {
    graph = new KnowledgeGraph();
  });

  // Knoten erstellen
  it('[D] GIVEN empty graph WHEN addNode THEN nodeCount is 1', () => {
    graph.addNode({ id: 'bob_cto', type: 'agent', label: 'Bob CTO' });
    expect(graph.getNode('bob_cto')).toBeDefined();
    expect(graph.getNode('bob_cto').label).toBe('Bob CTO');
    expect(graph.nodeCount).toBe(1);
  });

  // Kante erstellen
  it('[D] GIVEN 2 nodes WHEN addEdge THEN edgeCount is 1', () => {
    graph.addNode({ id: 'charlie', type: 'agent', label: 'Charlie' });
    graph.addNode({ id: 'mongodb', type: 'technology', label: 'MongoDB' });

    graph.addEdge({ from: 'charlie', to: 'mongodb', type: 'chose', label: 'Datenbankwahl' });

    expect(graph.edgeCount).toBe(1);
    const edges = graph.getEdgesFor('charlie');
    expect(edges).toHaveLength(1);
    expect(edges[0].to).toBe('mongodb');
  });

  // Nachbarn abfragen
  it('[D] GIVEN connected nodes WHEN getNeighbors THEN returns connected', () => {
    graph.addNode({ id: 'a', type: 'agent', label: 'A' });
    graph.addNode({ id: 'b', type: 'decision', label: 'B' });
    graph.addNode({ id: 'c', type: 'sop', label: 'C' });

    graph.addEdge({ from: 'a', to: 'b', type: 'made' });
    graph.addEdge({ from: 'b', to: 'c', type: 'based_on' });

    const neighbors = graph.getNeighbors('b');
    expect(neighbors).toHaveLength(2); // a and c
  });

  // Serialisierung für 3D-Visualisierung
  it('[D] GIVEN graph WHEN toJSON THEN returns nodes + edges arrays', () => {
    graph.addNode({ id: 'a', type: 'agent', label: 'Alice' });
    graph.addNode({ id: 'b', type: 'decision', label: 'REST' });
    graph.addEdge({ from: 'a', to: 'b', type: 'decided' });

    const json = graph.toJSON();
    expect(json.nodes).toHaveLength(2);
    expect(json.edges).toHaveLength(1);
    expect(json.nodes[0]).toHaveProperty('id');
    expect(json.edges[0]).toHaveProperty('source');
    expect(json.edges[0]).toHaveProperty('target');
  });
});

// ═══════════════════════════════════════════════════════════════════
// 3.5 Topologie-Puls
// ═══════════════════════════════════════════════════════════════════

describe('Task 3.5: Topologie-Puls Backend', () => {
  it('[D] GIVEN graph with subscriber WHEN addEdge THEN topology_pulse emitted', () => {
    const graph = new KnowledgeGraph();
    const pulses = [];

    graph.onPulse(p => pulses.push(p));

    graph.addNode({ id: 'charlie', type: 'agent', label: 'Charlie' });
    graph.addNode({ id: 'mongodb', type: 'technology', label: 'MongoDB' });
    graph.addEdge({ from: 'charlie', to: 'mongodb', type: 'chose' });

    // 2 node_added + 1 edge_added = 3 pulses
    expect(pulses).toHaveLength(3);
    const edgePulse = pulses.find(p => p.type === 'edge_added');
    expect(edgePulse).toBeDefined();
    expect(edgePulse.from).toBe('charlie');
    expect(edgePulse.to).toBe('mongodb');
  });

  it('[D] GIVEN graph WHEN addNode THEN node_added pulse', () => {
    const graph = new KnowledgeGraph();
    const pulses = [];
    graph.onPulse(p => pulses.push(p));

    graph.addNode({ id: 'mongo', type: 'tech', label: 'MongoDB' });
    expect(pulses).toHaveLength(1);
    expect(pulses[0].type).toBe('node_added');
  });
});

// ═══════════════════════════════════════════════════════════════════
// 3.6 Fehler-Topologie
// ═══════════════════════════════════════════════════════════════════

describe('Task 3.6: Fehler-Topologie', () => {
  it('[D] GIVEN error WHEN generateErrorTopology THEN subgraph created', () => {
    const graph = new KnowledgeGraph();

    graph.generateErrorTopology({
      error: 'Login Crashed',
      file: 'scraper.py',
      agent: 'charlie_dev',
      sop: 'Bot-Schutz',
    });

    expect(graph.nodeCount).toBeGreaterThanOrEqual(3);
    expect(graph.getNode('error_login_crashed')).toBeDefined();
    expect(graph.getNode('file_scraper.py')).toBeDefined();
    expect(graph.getNode('sop_bot-schutz')).toBeDefined();

    // Edges connect them
    expect(graph.edgeCount).toBeGreaterThanOrEqual(2);
  });
});

// ═══════════════════════════════════════════════════════════════════
// 3.8 Graph-Query-API
// ═══════════════════════════════════════════════════════════════════

describe('Task 3.8: Graph-Query-API', () => {
  it('[D] GIVEN graph with decision WHEN queryPath THEN returns path', () => {
    const graph = new KnowledgeGraph();

    graph.addNode({ id: 'bob', type: 'agent', label: 'Bob CTO' });
    graph.addNode({ id: 'sop12', type: 'sop', label: 'SOP #12: Database' });
    graph.addNode({ id: 'decision_mongo', type: 'decision', label: 'MongoDB gewählt' });
    graph.addNode({ id: 'ticket_3', type: 'ticket', label: 'Ticket #3' });

    graph.addEdge({ from: 'bob', to: 'sop12', type: 'consulted' });
    graph.addEdge({ from: 'sop12', to: 'decision_mongo', type: 'led_to' });
    graph.addEdge({ from: 'decision_mongo', to: 'ticket_3', type: 'resulted_in' });

    const path = graph.queryPath('decision_mongo');
    expect(path.length).toBeGreaterThanOrEqual(2);
    // Path should include connected nodes
    const ids = path.map(n => n.id);
    expect(ids).toContain('decision_mongo');
  });

  it('[D] GIVEN graph WHEN queryPath for unknown node THEN returns empty', () => {
    const graph = new KnowledgeGraph();
    const path = graph.queryPath('nonexistent');
    expect(path).toHaveLength(0);
  });
});
