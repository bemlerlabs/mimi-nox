/**
 * ◑ MiMiNox v2 — Metrics Panel — Rechte Spalte unten
 * Zeigt TF/KC/Agents/Tickets
 */

export function MetricsPanel({ agents = [], kanban = {} }) {
  const totalTickets = Object.values(kanban).reduce((sum, col) => sum + (col?.length || 0), 0);
  const activeAgents = agents.filter(a => a.status === 'running').length;
  const doneTickets = (kanban.done || []).length;
  const avgLevel = agents.length
    ? Math.round(agents.reduce((s, a) => s + (a.skills?.level || 1), 0) / agents.length)
    : 0;

  return (
    <div className="metrics-panel glass" id="metrics-panel">
      <div className="metrics-grid">
        <div className="glass-card metric-card">
          <div className="metric-value">{agents.length}</div>
          <div className="metric-label">Agenten</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-value" style={{ color: 'var(--green)' }}>{activeAgents}</div>
          <div className="metric-label">Aktiv</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-value" style={{ color: 'var(--orange)' }}>{totalTickets}</div>
          <div className="metric-label">Tickets</div>
        </div>
        <div className="glass-card metric-card">
          <div className="metric-value" style={{ color: 'var(--purple)' }}>LV.{avgLevel}</div>
          <div className="metric-label">Ø Level</div>
        </div>
      </div>
    </div>
  );
}
