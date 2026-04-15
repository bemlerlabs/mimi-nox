/**
 * ◑ MiMiNox v2 — QA-Audit Tests: Fehlende Features
 * Tests für 5 als "erledigt" markierte Tasks die unvollständig waren.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { KnowledgeGraph } from '../server/transparency/knowledge-graph.js';
import { TopologyMetrics } from '../server/transparency/topology-metrics.js';
import { SkillSystem } from '../server/agents/skill-system.js';
import { ChatBus } from '../server/agents/chat-bus.js';
import { StateStore } from '../server/state/store.js';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

function tmpPath(ext) {
  return path.join(os.tmpdir(), `miminox-${Date.now()}-${Math.random().toString(36).slice(2)}.${ext}`);
}

describe('QA-Audit: Graph Persistierung', () => {
  it('[D] GIVEN graph with data WHEN save+load THEN identical', () => {
    const graph = new KnowledgeGraph();
    graph.addNode({ id: 'a', type: 'agent', label: 'Alice' });
    graph.addNode({ id: 'b', type: 'tech', label: 'Express' });
    graph.addEdge({ from: 'a', to: 'b', type: 'chose' });

    const file = tmpPath('json');
    graph.save(file);

    const graph2 = new KnowledgeGraph();
    graph2.load(file);

    expect(graph2.nodeCount).toBe(2);
    expect(graph2.edgeCount).toBe(1);
    expect(graph2.getNode('a').label).toBe('Alice');

    try { fs.unlinkSync(file); } catch {}
  });
});

describe('QA-Audit: Puls-Farben', () => {
  it('[D] GIVEN edge types WHEN pulse emitted THEN has correct color', () => {
    const graph = new KnowledgeGraph();
    const pulses = [];
    graph.onPulse(p => pulses.push(p));

    graph.addNode({ id: 'a', type: 'agent', label: 'A' });
    graph.addNode({ id: 'b', type: 'sop', label: 'B' });
    graph.addNode({ id: 'c', type: 'decision', label: 'C' });
    graph.addNode({ id: 'd', type: 'ticket', label: 'D' });

    graph.addEdge({ from: 'a', to: 'b', type: 'consulted' });
    graph.addEdge({ from: 'b', to: 'c', type: 'decided' });
    graph.addEdge({ from: 'c', to: 'd', type: 'rejected' });

    const edgePulses = pulses.filter(p => p.type === 'edge_added');
    expect(edgePulses).toHaveLength(3);
    expect(edgePulses[0].pulseColor).toBe('#00D4FF'); // blue for consulted
    expect(edgePulses[1].pulseColor).toBe('#00FF88'); // green for decided
    expect(edgePulses[2].pulseColor).toBe('#FF4444'); // red for rejected
  });
});

describe('QA-Audit: Fehler-Topologie als Chat', () => {
  let store, bus;

  beforeEach(() => {
    store = new StateStore(':memory:');
    bus = new ChatBus(store);
  });

  afterEach(() => store?.close());

  it('[D] GIVEN error topology WHEN posted to chat THEN message has topology data', () => {
    const graph = new KnowledgeGraph();

    graph.generateErrorTopology({
      error: 'Login Crashed',
      file: 'scraper.py',
      agent: 'charlie_dev',
      sop: 'Bot-Schutz',
    });

    const topoJson = graph.toJSON();

    bus.send({
      from: 'diana_qa',
      to: 'charlie_dev',
      content: JSON.stringify({
        type: 'error_topology',
        nodes: topoJson.nodes,
        edges: topoJson.edges,
      }),
      type: 'error_topology',
    });

    const history = bus.getHistory();
    const topoMsg = history.find(m => m.type === 'error_topology');
    expect(topoMsg).toBeDefined();
    const parsed = JSON.parse(topoMsg.content);
    expect(parsed.nodes.length).toBeGreaterThanOrEqual(3);
    expect(parsed.edges.length).toBeGreaterThanOrEqual(2);
  });
});

describe('QA-Audit: Skill-XP aus Metriken', () => {
  let store, metrics, skills;

  beforeEach(() => {
    store = new StateStore(':memory:');
    metrics = new TopologyMetrics(store);
    skills = new SkillSystem(store);
    skills.initProfile('charlie_dev', {
      codeQuality: 50, bugDetection: 30, architecture: 25, research: 40,
      speed: 45, toolMastery: 35, communication: 30, testing: 40,
    });
  });

  afterEach(() => store?.close());

  it('[D] GIVEN metrics + skills WHEN recordWithSkillXP THEN research skill grows', () => {
    metrics.recordConnectionWithSkills('charlie_dev', 'express', 'todos', skills);

    expect(metrics.getKC('charlie_dev')).toBe(1);
    expect(skills.getProfile('charlie_dev').skills.research).toBe(45); // +5
  });
});
