/**
 * ◑ MiMiNox v2 — Express + Socket.io Server
 * server/index.js
 *
 * Core server with REST API and WebSocket support.
 * Port of Python server/main.py create_app() pattern.
 *
 * Endpoints:
 *   GET  /api/health       → { status, version }
 *   GET  /api/agents       → Agent[] from StateStore
 *   POST /api/tasks        → 202 { taskId }
 *   GET  /api/chat/history → ChatMessage[]
 *   GET  /api/kanban       → { backlog, in_progress, testing, done }
 */

import express from 'express';
import { createServer as createHttpServer } from 'node:http';
import { Server as SocketIOServer } from 'socket.io';
import cors from 'cors';
import crypto from 'node:crypto';
import { StateStore } from './state/store.js';
import { ChatBus } from './agents/chat-bus.js';
import { KanbanEngine } from './agents/kanban.js';
import { SkillSystem } from './agents/skill-system.js';
import { CommTools } from './agents/comm-tools.js';
import { CorrectionJournal } from './agents/correction-journal.js';
import { Orchestrator } from './agents/orchestrator.js';
import { EventLog } from './transparency/event-log.js';
import { KnowledgeGraph } from './transparency/knowledge-graph.js';

const VERSION = '2.0.0';

/**
 * Creates and returns the Express app, HTTP server, and Socket.io instance.
 * @param {Object} opts
 * @param {number}     [opts.port=3001]  - Port to listen on (0 = random)
 * @param {string}     [opts.dbPath]     - SQLite database path
 * @param {StateStore} [opts.store]      - Inject a StateStore (for testing)
 * @returns {{ app, server, io, store }}
 */
export function createServer(opts = {}) {
  const port = opts.port ?? 3001;
  const store = opts.store || new StateStore(opts.dbPath || ':memory:');
  const bus = new ChatBus(store);
  const kanban = new KanbanEngine(store);
  const skills = new SkillSystem(store);
  const comm = new CommTools({ store, bus, kanban, skills });
  const journal = new CorrectionJournal(store);
  const eventLog = new EventLog(store);
  const graph = new KnowledgeGraph();
  const orch = new Orchestrator({ store, bus, kanban, skills, comm, journal });

  // Initialize the crisis team (agents + skill profiles) on server start
  try { orch.init(); } catch { /* already initialized (e.g. persistent DB) */ }

  const app = express();
  const server = createHttpServer(app);
  const io = new SocketIOServer(server, {
    cors: { origin: '*' },
  });

  // ── Middleware ─────────────────────────────────────────────────────
  app.use(cors());
  app.use(express.json());

  // ── Pub/Sub → Socket.io Bridge ────────────────────────────────────
  store.subscribe((event) => {
    io.emit(event.type, event);
  });
  eventLog.onEvent((event) => {
    io.emit('event', event);
  });
  graph.onPulse((pulse) => {
    io.emit('topology_pulse', pulse);
  });

  // ── Routes: Health ────────────────────────────────────────────────

  app.get('/api/health', (_req, res) => {
    res.json({
      status: 'ok',
      version: VERSION,
      timestamp: new Date().toISOString(),
    });
  });

  // ── Routes: Agents ────────────────────────────────────────────────

  app.get('/api/agents', (_req, res) => {
    const raw = store.getAllAgents();
    const enriched = raw.map(agent => ({
      ...agent,
      skills: skills.getProfile(agent.id) || null,
    }));
    res.json(enriched);
  });

  // ── Routes: Tasks ─────────────────────────────────────────────────

  app.post('/api/tasks', async (req, res) => {
    const { prompt } = req.body || {};
    if (!prompt) {
      return res.status(400).json({ error: 'prompt is required' });
    }

    const taskId = await orch.submitTask(prompt);
    res.status(202).json({ taskId, status: 'accepted', prompt });
  });

  // ── Routes: Chat ──────────────────────────────────────────────────

  app.get('/api/chat/history', (_req, res) => {
    const limit = parseInt(_req.query.limit) || 100;
    res.json(store.getChatHistory(limit));
  });

  // ── Routes: Kanban ────────────────────────────────────────────────

  app.get('/api/kanban', (_req, res) => {
    res.json(kanban.getGrouped());
  });

  // ── Routes: Skills ────────────────────────────────────────────────

  app.get('/api/agents/:id/skills', (req, res) => {
    const profile = skills.getProfile(req.params.id);
    if (!profile) return res.status(404).json({ error: 'Agent nicht gefunden' });
    res.json(profile);
  });

  // ── Routes: Graph ─────────────────────────────────────────────────

  app.get('/api/graph', (_req, res) => {
    res.json(graph.toJSON());
  });

  app.get('/api/graph/query', (req, res) => {
    const { node } = req.query;
    if (!node) return res.status(400).json({ error: 'node query param required' });
    const path = graph.queryPath(node);
    res.json(path);
  });

  // ── Routes: Events ────────────────────────────────────────────────

  app.get('/api/events', (req, res) => {
    const { agentId, type } = req.query;
    const limit = parseInt(req.query.limit) || 100;
    res.json(eventLog.getEvents({ agentId, type, limit }));
  });

  // ── Socket.io ─────────────────────────────────────────────────────

  io.on('connection', (socket) => {
    socket.emit('connected', { version: VERSION });
  });

  // ── Start ─────────────────────────────────────────────────────────

  server.listen(port, () => {
    if (port !== 0) {
      console.log(`🚀 Miminox v2 listening on :${port}`);
    }
  });

  return { app, server, io, store, orch, bus, kanban, skills, comm, journal, eventLog, graph };
}

// Start standalone if run directly
const isMain = process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, '/'));
if (isMain) {
  createServer({ port: 3001 });
}
