/**
 * ◑ MiMiNox v2 — Worker Factory
 * server/workers/factory.js
 *
 * Manages worker_threads for agent isolation.
 * Each agent runs in its own thread — crash-safe, timeout-aware.
 *
 * Features:
 *   - Spawn agents in isolated threads
 *   - Timeout handling (terminates stuck workers)
 *   - Crash recovery (error events, no cascade)
 *   - Message routing (main ↔ worker)
 */

import { Worker } from 'node:worker_threads';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKER_SCRIPT = path.join(__dirname, 'agent-worker.js');

export class WorkerFactory {
  constructor() {
    /** @type {Map<string, { worker: Worker, timeout: number, timer?: NodeJS.Timeout }>} */
    this._workers = new Map();
  }

  /**
   * Spawn a new agent in an isolated worker thread.
   * @param {Object} opts
   * @param {string} opts.id          - Agent ID
   * @param {string} opts.role        - Agent role
   * @param {number} [opts.timeout]   - Max execution time in ms (0 = no timeout)
   * @param {(msg: Object) => void} opts.onMessage - Callback for worker messages
   * @returns {Worker}
   */
  spawn({ id, role, timeout = 0, onMessage }) {
    if (this._workers.has(id)) {
      throw new Error(`Agent '${id}' ist bereits gestartet.`);
    }

    const worker = new Worker(WORKER_SCRIPT, {
      workerData: { agentId: id, role, timeout },
    });

    const entry = { worker, timeout, timer: null, _onMessage: onMessage };
    this._workers.set(id, entry);

    // Route messages to callback
    worker.on('message', (msg) => {
      // Clear timeout timer on done/error
      if (msg.type === 'done' || msg.type === 'error') {
        this._clearTimer(id);
      }
      onMessage(msg);
    });

    // Handle worker crash
    worker.on('error', (err) => {
      this._clearTimer(id);
      onMessage({ type: 'error', agentId: id, error: err.message });
      this._workers.delete(id);
    });

    // Handle worker exit
    worker.on('exit', (code) => {
      this._clearTimer(id);
      if (code !== 0) {
        onMessage({ type: 'exit', agentId: id, code, error: `Worker exited with code ${code}` });
      }
      this._workers.delete(id);
    });

    return worker;
  }

  /**
   * Send a message to a specific worker.
   * @param {string} id   - Agent ID
   * @param {Object} msg  - Message to send
   */
  sendToWorker(id, msg) {
    const entry = this._workers.get(id);
    if (!entry) {
      throw new Error(`Agent '${id}' nicht gefunden.`);
    }

    entry.worker.postMessage(msg);

    // Start timeout timer for execute commands
    if (msg.type === 'execute' && entry.timeout > 0) {
      this._clearTimer(id);
      entry.timer = setTimeout(() => {
        // Timeout reached — emit error directly from main thread
        // (postMessage to dying worker is unreliable)
        this._clearTimer(id);
        const cb = entry._onMessage;
        if (cb) cb({ type: 'error', agentId: id, error: `Timeout nach ${entry.timeout}ms` });
        entry.worker.terminate();
      }, entry.timeout);
    }
  }

  /**
   * Check if a worker is still alive.
   * @param {string} id
   * @returns {boolean}
   */
  isAlive(id) {
    return this._workers.has(id);
  }

  /** Number of active workers */
  get workerCount() {
    return this._workers.size;
  }

  /**
   * Terminate all workers (cleanup).
   */
  async terminateAll() {
    const promises = [];
    for (const [id, entry] of this._workers) {
      this._clearTimer(id);
      promises.push(entry.worker.terminate());
    }
    await Promise.allSettled(promises);
    this._workers.clear();
  }

  /** @private */
  _clearTimer(id) {
    const entry = this._workers.get(id);
    if (entry?.timer) {
      clearTimeout(entry.timer);
      entry.timer = null;
    }
  }
}
