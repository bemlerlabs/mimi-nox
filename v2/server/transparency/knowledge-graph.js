/**
 * ◑ MiMiNox v2 — Knowledge Graph Engine (Firmengehirn)
 * server/transparency/knowledge-graph.js
 *
 * In-Memory Graph mit Pub/Sub für Topologie-Puls.
 * Nutzt graphology.js als Basis (peer dependency).
 *
 * Features:
 *   - Knoten/Kanten CRUD
 *   - Topologie-Puls Events (node_added, edge_added)
 *   - Error-Topologie-Generator
 *   - Path-Query (BFS-basiert)
 *   - JSON-Export für 3d-force-graph
 *
 * Node Types: agent, decision, technology, sop, error, file, ticket
 * Edge Types: chose, made, consulted, resulted_in, based_on, caused_by
 */

import Graph from 'graphology';
import fs from 'node:fs';

export class KnowledgeGraph {
  constructor() {
    this._graph = new Graph({ multi: false, type: 'undirected' });
    this._pulseSubscribers = [];
  }

  // ── Nodes ─────────────────────────────────────────────────────────

  /**
   * Add a node to the graph.
   * @param {{ id: string, type: string, label: string }} node
   */
  addNode({ id, type, label }) {
    this._graph.addNode(id, { type, label });
    this._emitPulse({ type: 'node_added', id, nodeType: type, label });
  }

  /**
   * Get a node by ID.
   * @param {string} id
   * @returns {{ id, type, label }|undefined}
   */
  getNode(id) {
    if (!this._graph.hasNode(id)) return undefined;
    const attrs = this._graph.getNodeAttributes(id);
    return { id, ...attrs };
  }

  /** Number of nodes. */
  get nodeCount() {
    return this._graph.order;
  }

  // ── Edges ─────────────────────────────────────────────────────────

  /**
   * Add an edge between two nodes.
   * @param {{ from: string, to: string, type: string, label?: string }} edge
   */
  addEdge({ from, to, type, label = '' }) {
    this._graph.addEdge(from, to, { type, label });
    this._emitPulse({ type: 'edge_added', from, to, edgeType: type, pulseColor: this._pulseColor(type) });
  }

  /**
   * Get all edges for a node.
   * @param {string} nodeId
   * @returns {Object[]}
   */
  getEdgesFor(nodeId) {
    if (!this._graph.hasNode(nodeId)) return [];
    const edges = [];
    this._graph.forEachEdge(nodeId, (edge, attrs, source, target) => {
      edges.push({
        from: source,
        to: target,
        ...attrs,
      });
    });
    return edges;
  }

  /** Number of edges. */
  get edgeCount() {
    return this._graph.size;
  }

  // ── Queries ───────────────────────────────────────────────────────

  /**
   * Get all neighbors of a node.
   * @param {string} nodeId
   * @returns {Object[]}
   */
  getNeighbors(nodeId) {
    if (!this._graph.hasNode(nodeId)) return [];
    return this._graph.neighbors(nodeId).map(id => this.getNode(id));
  }

  /**
   * Query the path around a node (BFS, depth 2).
   * @param {string} nodeId
   * @param {number} [depth=2]
   * @returns {Object[]} nodes in the path
   */
  queryPath(nodeId, depth = 2) {
    if (!this._graph.hasNode(nodeId)) return [];

    const visited = new Set();
    const queue = [{ id: nodeId, d: 0 }];
    const result = [];

    while (queue.length > 0) {
      const { id, d } = queue.shift();
      if (visited.has(id)) continue;
      visited.add(id);

      result.push(this.getNode(id));

      if (d < depth) {
        for (const neighbor of this._graph.neighbors(id)) {
          if (!visited.has(neighbor)) {
            queue.push({ id: neighbor, d: d + 1 });
          }
        }
      }
    }

    return result;
  }

  // ── Error Topology Generator ──────────────────────────────────────

  /**
   * Generate a subgraph for an error event.
   * @param {{ error: string, file: string, agent: string, sop?: string }} data
   */
  generateErrorTopology({ error, file, agent, sop }) {
    const errorId = `error_${error.toLowerCase().replace(/\s+/g, '_')}`;
    const fileId = `file_${file}`;

    if (!this._graph.hasNode(errorId)) {
      this.addNode({ id: errorId, type: 'error', label: error });
    }
    if (!this._graph.hasNode(fileId)) {
      this.addNode({ id: fileId, type: 'file', label: file });
    }
    if (!this._graph.hasNode(agent)) {
      this.addNode({ id: agent, type: 'agent', label: agent });
    }

    this.addEdge({ from: errorId, to: fileId, type: 'in_file' });
    this.addEdge({ from: agent, to: errorId, type: 'discovered' });

    if (sop) {
      const sopId = `sop_${sop.toLowerCase().replace(/\s+/g, '-')}`;
      if (!this._graph.hasNode(sopId)) {
        this.addNode({ id: sopId, type: 'sop', label: `SOP: ${sop}` });
      }
      this.addEdge({ from: fileId, to: sopId, type: 'related_sop' });
    }
  }

  // ── Serialization ─────────────────────────────────────────────────

  /**
   * Export graph as JSON for 3d-force-graph.
   * @returns {{ nodes: Object[], edges: Object[] }}
   */
  toJSON() {
    const nodes = [];
    this._graph.forEachNode((id, attrs) => {
      nodes.push({ id, ...attrs });
    });

    const edges = [];
    this._graph.forEachEdge((edge, attrs, source, target) => {
      edges.push({ source, target, ...attrs });
    });

    return { nodes, edges };
  }

  // ── Pub/Sub (Topologie-Puls) ──────────────────────────────────────

  /**
   * Subscribe to topology pulse events.
   * @param {(pulse: Object) => void} callback
   * @returns {() => void} unsubscribe
   */
  onPulse(callback) {
    this._pulseSubscribers.push(callback);
    return () => {
      this._pulseSubscribers = this._pulseSubscribers.filter(s => s !== callback);
    };
  }

  /** @private */
  _emitPulse(pulse) {
    for (const sub of this._pulseSubscribers) {
      try { sub(pulse); } catch { /* safe */ }
    }
  }

  // ── Pulse Colors ──────────────────────────────────────────────────

  static PULSE_COLORS = {
    consulted:   '#00D4FF', // cyan/blue
    decided:     '#00FF88', // green
    rejected:    '#FF4444', // red
    chose:       '#00FF88', // green
    discovered:  '#FF8800', // orange
    in_file:     '#FFAA00', // yellow
    related_sop: '#00D4FF', // blue
    based_on:    '#AA88FF', // purple
    resulted_in: '#00FF88', // green
    caused_by:   '#FF4444', // red
    led_to:      '#00FF88', // green
  };

  /** @private */
  _pulseColor(edgeType) {
    return KnowledgeGraph.PULSE_COLORS[edgeType] || '#FFFFFF';
  }

  // ── Persistence ───────────────────────────────────────────────────

  /**
   * Save graph to a JSON file.
   * @param {string} filePath
   */
  save(filePath) {
    const data = this.toJSON();
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
  }

  /**
   * Load graph from a JSON file.
   * @param {string} filePath
   */
  load(filePath) {
    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));

    // Clear existing graph
    this._graph = new Graph({ multi: false, type: 'undirected' });

    // Restore nodes (without emitting pulses)
    for (const node of data.nodes) {
      const { id, ...attrs } = node;
      this._graph.addNode(id, attrs);
    }

    // Restore edges (without emitting pulses)
    for (const edge of data.edges) {
      const { source, target, ...attrs } = edge;
      this._graph.addEdge(source, target, attrs);
    }
  }
}
