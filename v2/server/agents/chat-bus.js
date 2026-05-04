/**
 * ◑ MiMiNox v2 — Chat-Bus
 * server/agents/chat-bus.js
 *
 * Zentraler Nachrichten-Bus für Agent-zu-Agent Kommunikation.
 * Persistiert alle Nachrichten im StateStore.
 *
 * Features:
 *   - Direct messages (from → to)
 *   - Broadcast (from → all)
 *   - Event-basierte Subscriber (für Socket.io / Dashboard)
 *   - getMessagesFor(agent) — filtert Direkt + Broadcast
 */

export class ChatBus {
  /**
   * @param {import('../state/store.js').StateStore} store
   */
  constructor(store) {
    this._store = store;
    this._subscribers = [];
  }

  /**
   * Send a message. Streaming messages (type='streaming') are only sent to
   * subscribers (Socket.io) and NOT persisted to DB. Final messages are persisted.
   * @param {{ id?: string, from: string, to: string, content: string, type?: string }} msg
   */
  send({ id, from, to, content, type = 'message' }) {
    if (type === 'streaming') {
      // Stream updates → only notify subscribers (Socket.io / frontend), no DB write
      this._notify({ id, from, to, content, type, timestamp: new Date().toISOString() });
      return;
    }
    // Final or regular message → persist to DB + notify
    this._store.addChatMessage({ from, to, content, type });
    this._notify({ id, from, to, content, type, timestamp: new Date().toISOString() });
  }

  /**
   * Broadcast a message to all agents.
   * @param {{ from: string, content: string, type?: string }} msg
   */
  broadcast({ from, content, type = 'broadcast' }) {
    this.send({ from, to: 'all', content, type });
  }

  /**
   * Get full chat history, chronologically.
   * @param {number} [limit=100]
   * @returns {Object[]}
   */
  getHistory(limit = 100) {
    return this._store.getChatHistory(limit);
  }

  /**
   * Get messages relevant to a specific agent (direct + broadcast).
   * @param {string} agentId
   * @param {number} [limit=50]
   * @returns {Object[]}
   */
  getMessagesFor(agentId, limit = 50) {
    const all = this._store.getChatHistory(500);
    return all
      .filter(m => m.to === agentId || m.to === 'all' || m.from === agentId)
      .slice(0, limit);
  }

  /**
   * Subscribe to new messages.
   * @param {(msg: Object) => void} callback
   * @returns {() => void} unsubscribe
   */
  onMessage(callback) {
    this._subscribers.push(callback);
    return () => {
      this._subscribers = this._subscribers.filter(s => s !== callback);
    };
  }

  /** @private */
  _notify(msg) {
    for (const sub of this._subscribers) {
      try { sub(msg); } catch { /* subscriber crash safe */ }
    }
  }
}
