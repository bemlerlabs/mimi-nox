/**
 * ◑ MiMiNox v2 — Kommunikations-Tools
 * server/agents/comm-tools.js
 *
 * Inter-Agent Communication Tools.
 * Diese werden vom LLM als Tool-Calls aufgerufen.
 *
 * Tools:
 *   assign_task  — Agent delegates work → ticket + chat
 *   submit_work  — Agent submits work → ticket → testing + reviewer notification
 *   reject_work  — Reviewer rejects → ticket → in_progress
 *   approve_work — Reviewer approves → ticket → done + skill XP
 */

export class CommTools {
  /**
   * @param {Object} deps - Injected dependencies
   * @param {import('../state/store.js').StateStore} deps.store
   * @param {import('./chat-bus.js').ChatBus} deps.bus
   * @param {import('./kanban.js').KanbanEngine} deps.kanban
   * @param {import('./skill-system.js').SkillSystem} deps.skills
   */
  constructor({ store, bus, kanban, skills, reviewerId = 'sensor_agent' }) {
    this._store = store;
    this._bus = bus;
    this._kanban = kanban;
    this._skills = skills;
    this._reviewerId = reviewerId;
  }

  /**
   * Assign a task to an agent. Creates a ticket and sends a chat message.
   * @param {{ from: string, to: string, task: string, description?: string }} opts
   * @returns {{ ticketId: number }}
   */
  assignTask({ from, to, task, description = '' }) {
    const ticketId = this._kanban.createTicket({
      title: task,
      assignee: to,
      createdBy: from,
      description,
    });

    this._bus.send({
      from,
      to,
      content: `📋 Neue Aufgabe: "${task}"${description ? `\n${description}` : ''}`,
      type: 'directive',
    });

    return { ticketId };
  }

  /**
   * Submit completed work for QA review.
   * @param {{ from: string, ticketId: number, result: string, code?: string }} opts
   */
  submitWork({ from, ticketId, result, code = '' }) {
    this._kanban.moveTicket(ticketId, 'testing');

    const ticket = this._kanban.getTicket(ticketId);
    const qaAgent = this._reviewerId;

    this._bus.send({
      from,
      to: qaAgent,
      content: `✅ Arbeit eingereicht für Ticket #${ticketId} "${ticket.title}":\n${result}${code ? `\n\`\`\`\n${code}\n\`\`\`` : ''}`,
      type: 'submission',
    });
  }

  /**
   * Reject work and send it back to the developer.
   * @param {{ from: string, ticketId: number, reason: string, feedback?: string }} opts
   */
  rejectWork({ from, ticketId, reason, feedback = '' }) {
    const ticket = this._kanban.getTicket(ticketId);
    const developer = ticket.assignee;

    this._kanban.moveTicket(ticketId, 'in_progress');

    // T-04: Ticket als "war rejected" markieren — für korrekte XP-Vergabe bei approveWork
    this._store.markTicketRejected(ticketId);

    this._bus.send({
      from,
      to: developer,
      content: `❌ Ticket #${ticketId} rejected: ${reason}${feedback ? `\nFeedback: ${feedback}` : ''}`,
      type: 'rejection',
    });

    // T-04: KEIN onQARejectionFixed hier — der Developer hat noch nichts gefixt!
    // XP kommt erst bei approveWork wenn was_rejected=1 (Fix wurde erfolgreich abgeliefert).
  }

  /**
   * Approve work and mark ticket as done.
   * @param {{ from: string, ticketId: number }} opts
   */
  approveWork({ from, ticketId }) {
    const ticket = this._kanban.getTicket(ticketId);
    const developer = ticket.assignee;

    this._kanban.moveTicket(ticketId, 'done');

    this._bus.send({
      from,
      to: developer,
      content: `✅ Ticket #${ticketId} "${ticket.title}" approved. Gute Arbeit!`,
      type: 'approval',
    });

    // T-04: codeQuality XP bei jedem Approve
    this._skills.onTaskCompleted(developer, { rejected: false });

    // T-04: bugDetection XP NUR wenn Ticket vorher rejected war — Fix wurde geleistet
    if (ticket.was_rejected) {
      this._skills.onQARejectionFixed(developer);
    }
  }
}
