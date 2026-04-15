/**
 * ◑ MiMiNox v2 — Inline Error Topology (Mini-Graph im Chat)
 * Task 4.3b: Fehler-Topologie inline
 */

export function ErrorTopologyInline({ data }) {
  let parsed;
  try {
    parsed = typeof data === 'string' ? JSON.parse(data) : data;
  } catch {
    return null;
  }

  if (!parsed?.nodes || !parsed?.edges) return null;

  return (
    <div className="error-topo-inline" id="error-topology-inline">
      <div className="error-topo-header">
        <span style={{ fontSize: '12px', color: 'var(--red)' }}>⚠️ Fehler-Topologie</span>
      </div>
      <div className="error-topo-graph">
        {parsed.nodes.map((node, i) => (
          <span key={i} className={`topo-node topo-node-${node.type}`}>
            {node.type === 'error' ? '❌' : node.type === 'file' ? '📄' : node.type === 'sop' ? '📋' : '🔹'}
            {' '}{node.label}
          </span>
        ))}
      </div>
      <div className="error-topo-edges">
        {parsed.edges.map((edge, i) => (
          <span key={i} className="topo-edge">
            {edge.source} ◄──{edge.type}──► {edge.target}
          </span>
        ))}
      </div>
    </div>
  );
}
