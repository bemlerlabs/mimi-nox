/**
 * ◑ MiMiNox v2 — Auto-Kanban Board
 * Task 4.4: Tickets in Spalten
 */

const COLUMNS = [
  { key: 'backlog', label: '📋 Backlog', color: 'var(--text-muted)' },
  { key: 'in_progress', label: '⚡ In Progress', color: 'var(--cyan)' },
  { key: 'testing', label: '🧪 Testing', color: 'var(--orange)' },
  { key: 'done', label: '✅ Done', color: 'var(--green)' },
];

export function KanbanBoard({ kanban = {} }) {
  return (
    <div className="kanban-panel glass" id="kanban-board">
      <div className="kanban-board">
        {COLUMNS.map(col => {
          const tickets = kanban[col.key] || [];
          return (
            <div className="kanban-col" key={col.key}>
              <div className="kanban-col-header" style={{ color: col.color }}>
                {col.label}
                <span className="kanban-col-count">{tickets.length}</span>
              </div>
              {tickets.map(ticket => (
                <div className="kanban-ticket" key={ticket.id}>
                  <div className="kanban-ticket-title">{ticket.title || ticket.task || `Ticket #${ticket.id}`}</div>
                  <div className="kanban-ticket-assignee">→ {ticket.assignee || '—'}</div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
