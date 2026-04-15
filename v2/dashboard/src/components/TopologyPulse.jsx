/**
 * ◑ MiMiNox v2 — 3D Topology Pulse (Firmengehirn)
 * Task 4.6: 3D-Visualisierung, Puls-Animation, Audit-Klick
 * Task 4.7: Drag & Drop SOP Upload
 */
import { useEffect, useRef, useState, useCallback } from 'react';

// Demo-Graph für Offline-Betrieb — Krisen-Szenario
const DEMO_GRAPH = {
  nodes: [
    { id: 'medic_agent', label: '🚑 Medic', type: 'agent', color: '#76B900' },
    { id: 'engineer_agent', label: '🛠 Engineer', type: 'agent', color: '#8ACB00' },
    { id: 'navigator_agent', label: '🗺 Navigator', type: 'agent', color: '#76B900' },
    { id: 'sensor_agent', label: '⚡ Sensor', type: 'agent', color: '#5A8F00' },
    { id: 'task_burn', label: 'Verbrennung', type: 'task', color: '#555555' },
    { id: 'task_solar', label: 'Solar-Panel', type: 'task', color: '#555555' },
    { id: 'knowledge_med', label: 'KB: Medizin', type: 'sop', color: '#76B900' },
    { id: 'knowledge_eng', label: 'KB: Technik', type: 'sop', color: '#76B900' },
    { id: 'alert_power', label: 'Batterie niedrig', type: 'error', color: '#FF3B3B' },
    { id: 'route_1', label: 'Route: Dorf', type: 'decision', color: '#8ACB00' },
  ],
  edges: [
    { source: 'medic_agent', target: 'task_burn', type: 'assigned' },
    { source: 'task_burn', target: 'knowledge_med', type: 'consulted' },
    { source: 'knowledge_med', target: 'medic_agent', type: 'produced' },
    { source: 'engineer_agent', target: 'task_solar', type: 'assigned' },
    { source: 'task_solar', target: 'knowledge_eng', type: 'consulted' },
    { source: 'sensor_agent', target: 'alert_power', type: 'rejected' },
    { source: 'alert_power', target: 'engineer_agent', type: 'feedback' },
    { source: 'navigator_agent', target: 'route_1', type: 'produced' },
  ],
};

const EDGE_COLORS = {
  created: '#76B900',
  delegated: '#5A8F00',
  consulted: '#5A8F00',
  produced: '#8ACB00',
  assigned: '#555555',
  submitted: '#76B900',
  rejected: '#FF3B3B',
  feedback: '#FF8C00',
  default: '#222',
};

const NODE_SHAPES = {
  agent: '●',
  task: '◆',
  decision: '★',
  sop: '◼',
  error: '✕',
};

export function TopologyPulse({ graphData, pulseEvents = [], onNodeClick, onSopDrop }) {
  const containerRef = useRef(null);
  const graphRef = useRef(null);
  const [hoverNode, setHoverNode] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const data = graphData || DEMO_GRAPH;

  useEffect(() => {
    let graph;
    async function init() {
      if (!containerRef.current) return;

      const ForceGraph3D = (await import('3d-force-graph')).default;

      const gData = {
        nodes: data.nodes.map(n => ({
          ...n,
          val: n.type === 'agent' ? 3 : n.type === 'error' ? 1.5 : 2,
        })),
        links: data.edges.map(e => ({
          source: e.source,
          target: e.target,
          type: e.type,
          color: EDGE_COLORS[e.type] || EDGE_COLORS.default,
        })),
      };

      const rect = containerRef.current.getBoundingClientRect();

      graph = ForceGraph3D()(containerRef.current)
        .width(rect.width)
        .height(rect.height)
        .graphData(gData)
        .backgroundColor('#00000000')
        .nodeColor(n => n.color || '#666')
        .nodeVal(n => n.val)
        .nodeLabel(n => `${NODE_SHAPES[n.type] || '●'} ${n.label}`)
        .nodeOpacity(0.9)
        .linkColor(l => l.color)
        .linkOpacity(0.4)
        .linkWidth(1)
        .linkDirectionalParticles(l => l.type === 'rejected' ? 4 : 1)
        .linkDirectionalParticleSpeed(0.005)
        .linkDirectionalParticleColor(l => l.color)
        .linkDirectionalParticleWidth(2)
        .onNodeClick(node => {
          if (onNodeClick) onNodeClick(node);
          setHoverNode(node);
          // Zoom to node
          graph.cameraPosition(
            { x: node.x * 1.5, y: node.y * 1.5, z: node.z * 1.5 },
            node,
            1000
          );
        })
        .onNodeHover(node => setHoverNode(node));

      // Slow rotation
      let angle = 0;
      const dist = 180;
      const interval = setInterval(() => {
        angle += 0.002;
        graph.cameraPosition({
          x: dist * Math.sin(angle),
          z: dist * Math.cos(angle),
        });
      }, 30);

      graphRef.current = { graph, interval };
    }

    init();
    return () => {
      if (graphRef.current) {
        clearInterval(graphRef.current.interval);
        graphRef.current.graph?._destructor?.();
      }
    };
  }, [data, onNodeClick]);

  // Pulse events → particle burst
  useEffect(() => {
    if (!graphRef.current?.graph || !pulseEvents.length) return;
    const latest = pulseEvents[pulseEvents.length - 1];
    const g = graphRef.current.graph;
    // Increase particles on the matching link briefly
    g.linkDirectionalParticles(l => {
      if (l.source?.id === latest.from && l.target?.id === latest.to) return 8;
      if (l.type === 'rejected') return 4;
      return 1;
    });
    // Reset after 2s
    setTimeout(() => {
      g.linkDirectionalParticles(l => l.type === 'rejected' ? 4 : 1);
    }, 2000);
  }, [pulseEvents]);

  // Drag & Drop SOP
  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length && onSopDrop) {
      onSopDrop(files);
    }
  }, [onSopDrop]);

  return (
    <div
      className={`graph-container ${isDragOver ? 'graph-drop-active' : ''}`}
      id="topology-pulse"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      style={{ position: 'relative' }}
    >
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Drop zone overlay */}
      {isDragOver && (
        <div className="graph-drop-overlay">
          <div>📋 SOP hier ablegen</div>
        </div>
      )}

      {/* Hover info */}
      {hoverNode && (
        <div className="graph-node-info">
          <div style={{ fontSize: '11px', fontWeight: 600 }}>
            {NODE_SHAPES[hoverNode.type]} {hoverNode.label}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
            Typ: {hoverNode.type}
          </div>
        </div>
      )}
    </div>
  );
}
