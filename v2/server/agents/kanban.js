/**
 * ◑ MiMiNox v2 — Kanban-Engine
 * server/agents/kanban.js
 *
 * Ticket-Management mit Workflow-Validierung.
 * Port von Python Kanban-Logik mit strikten Zustandsübergängen.
 *
 * Workflow:
 *   backlog → in_progress → testing → done
 *                  ↑            ↓
 *                  └── (reject) ←┘
 *
 * Ungültige Übergänge (z.B. backlog → done) werden rejected.
 */

// Valid state transitions
const VALID_TRANSITIONS = {
  backlog:     ['in_progress'],
  in_progress: ['testing'],
  testing:     ['done', 'in_progress'],  // QA can reject → back to dev
  done:        [],                        // Final state
};

export class KanbanEngine {
  /**
   * @param {import('../state/store.js').StateStore} store
   */
  constructor(store) {
    this._store = store;
  }

  /**
   * Create a new ticket.
   * @param {{ title: string, assignee?: string, createdBy?: string, description?: string }} data
   * @returns {number} ticket ID
   */
  createTicket({ title, assignee = null, createdBy = null, description = '' }) {
    return this._store.createTicket({ title, assignee, createdBy, description });
  }

  /**
   * Move a ticket to a new status with workflow validation.
   * @param {number} id
   * @param {string} newStatus
   * @throws {Error} If the transition is invalid
   */
  moveTicket(id, newStatus) {
    const ticket = this.getTicket(id);
    if (!ticket) {
      throw new Error(`Ticket #${id} nicht gefunden.`);
    }

    const currentStatus = ticket.status;
    const allowed = VALID_TRANSITIONS[currentStatus] || [];

    if (!allowed.includes(newStatus)) {
      throw new Error(
        `Ungültiger Übergang: '${currentStatus}' → '${newStatus}'. ` +
        `Erlaubt: ${allowed.join(', ') || 'keine (Endstatus)'}`
      );
    }

    this._store.updateTicketStatus(id, newStatus);
  }

  /**
   * Get a single ticket by ID.
   * @param {number} id
   * @returns {Object|undefined}
   */
  getTicket(id) {
    const tickets = this._store.getTickets();
    return tickets.find(t => t.id === id);
  }

  /**
   * Get all tickets.
   * @returns {Object[]}
   */
  getAll() {
    return this._store.getTickets();
  }

  /**
   * Get tickets grouped by status for the Kanban board.
   * @returns {{ backlog: Object[], in_progress: Object[], testing: Object[], done: Object[] }}
   */
  getGrouped() {
    const tickets = this.getAll();
    return {
      backlog: tickets.filter(t => t.status === 'backlog'),
      in_progress: tickets.filter(t => t.status === 'in_progress'),
      testing: tickets.filter(t => t.status === 'testing'),
      done: tickets.filter(t => t.status === 'done'),
    };
  }
}
