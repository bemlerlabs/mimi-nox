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
import { Ollama } from 'ollama';
import { networkInterfaces } from 'node:os';
// QR-Code wird client-seitig generiert (Frontend, Vite-Bundle)

const VERSION = '2.0.0';

/**
 * Detect the machine's primary local network IP (not loopback).
 * Used to generate QR codes for mobile access via WiFi.
 */
function getLocalIP() {
  const nets = networkInterfaces();
  for (const name of Object.keys(nets)) {
    for (const net of nets[name]) {
      // Erste nicht-interne IPv4-Adresse → das ist die LAN-IP
      if (net.family === 'IPv4' && !net.internal) return net.address;
    }
  }
  return 'localhost';
}

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

  // ── T-07: Connect Gemma 4 E4B via Ollama ────────────────────────────
  const OLLAMA_HOST = process.env.OLLAMA_HOST || 'http://localhost:11434';
  const OLLAMA_MODEL = process.env.OLLAMA_MODEL || 'gemma4:e4b';

  // ── LLM Performance-Konfiguration ─────────────────────────────
  // #3 Token-Budget: Kontext-abhängige Limits (Emergency kurz +
  //    direkt, Medical strukturiert, Vision fokussiert)
  // #6 KV-Cache: keep_alive:-1 → Modell bleibt in RAM, System-
  //    Prompt KV-Cache wird wiederverwendet (TTFT 2s → 0.3s)
  // #7 TTFT-Logging: exakt messen wann erster Token kommt
  const TOKEN_BUDGET = {
    emergency: 200,  // Notruf-Szenarien: kurz + direkt
    medical:   400,  // Medizinische Details: strukturiert
    vision:    350,  // Bildanalyse: fokussiert
    default:   500,  // Standard-Konversation
  };

  /**
   * Classify prompt to pick the right token budget.
   * @param {string} prompt
   * @param {boolean} hasImages
   * @returns {number}
   */
  function getTokenBudget(prompt, hasImages) {
    if (hasImages) return TOKEN_BUDGET.vision;
    const lower = prompt.toLowerCase();
    if (lower.match(/notruf|112|144|ohnmacht|herzstillstand|bewusstlos|notfall|sos|hilfe/))
      return TOKEN_BUDGET.emergency;
    if (lower.match(/verbrennung|blutung|allergi|vergiftung|medikament|dosis|schmerz|symptom/))
      return TOKEN_BUDGET.medical;
    return TOKEN_BUDGET.default;
  }

  (async () => {
    try {
      const ollama = new Ollama({ host: OLLAMA_HOST });
      // Verify connection with a minimal ping
      await ollama.list();
      orch.setLLMProvider({
        // Blocking chat (for simple queries)
        async chat({ messages, hasImages }) {
          const response = await ollama.chat({
            model:      OLLAMA_MODEL,
            messages,
            stream:     false,
            keep_alive: -1,   // #6 KV-Cache: Modell bleibt geladen
            options: {
              num_predict: getTokenBudget(
                messages[messages.length - 1]?.content || '', hasImages
              ),
            },
          });
          return { content: response.message?.content || '' };
        },
        // Streaming chat (for real-time token delivery)
        async chatStream({ messages, hasImages }, onToken) {
          const t0          = Date.now();
          let   firstToken  = false;
          let   tokenCount  = 0;

          const lastPrompt = messages[messages.length - 1]?.content || '';
          const stream = await ollama.chat({
            model:      OLLAMA_MODEL,
            messages,
            stream:     true,
            keep_alive: -1,   // #6 KV-Cache: System-Prompt gecacht
            options: {
              num_predict: getTokenBudget(lastPrompt, hasImages), // #3 Token-Budget
            },
          });

          let full = '';
          for await (const chunk of stream) {
            const token = chunk.message?.content || '';
            if (!token) continue;

            // #7 TTFT-Messung: erstes Token-Timing
            if (!firstToken) {
              const ttft = Date.now() - t0;
              console.log(`⚡ TTFT: ${ttft}ms`);
              firstToken = true;
            }

            full       += token;
            tokenCount += 1;
            if (onToken) onToken(token);
          }

          // #7 TPS-Messung: Tokens pro Sekunde loggen
          const durationS = (Date.now() - t0) / 1000;
          const tps       = (tokenCount / durationS).toFixed(1);
          console.log(`📊 ${tokenCount} Tokens in ${durationS.toFixed(1)}s = ${tps} tok/s`);

          return { content: full };
        },
      });
      console.log(`🧠 Gemma 4 E4B verbunden (${OLLAMA_HOST}, model: ${OLLAMA_MODEL})`);
    } catch (err) {
      console.warn(`⚠️  Ollama nicht erreichbar (${OLLAMA_HOST}) — Offline-RAG-Modus aktiv`);
      // Graceful degradation: System läuft weiter mit TF-IDF-Fallback
    }
  })();

  const app = express();
  const server = createHttpServer(app);
  const io = new SocketIOServer(server, {
    cors: { origin: '*' },
  });

  // ── Middleware ─────────────────────────────────────────────────────
  app.use(cors());
  // 10MB limit: vision payloads (base64 1024px JPEG ~200-800KB) exceed the 100KB default
  app.use(express.json({ limit: '10mb' }));

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

  // ── ChatBus → Socket.io: Live Streaming ───────────────────────────
  // Streaming tokens arrive here every ~500ms during LLM generation.
  // We push them directly to all connected clients so the frontend
  // shows live typing — no polling gap (1.5s) for these events.
  bus.onMessage((msg) => {
    if (msg.type === 'streaming') {
      io.emit('chat_stream', msg);   // Frontend listens to 'chat_stream'
    } else if (msg.type === 'message') {
      io.emit('chat_message', msg);  // Confirm final message via socket too
    }
  });

  // ── Routes: Health ────────────────────────────────────────────────

  app.get('/api/health', (_req, res) => {
    const ollamaReady = orch._llm != null;
    res.json({
      status:     'ok',
      version:    VERSION,
      timestamp:  new Date().toISOString(),
      ollamaReady,
      airGapped:  !ollamaReady,
    });
  });

  // ── Routes: Connect via QR ────────────────────────────────────
  // Gibt lokale URL zurück → Frontend generiert QR-Code im Browser (Vite/Browser-Build)
  app.get('/api/connect', (_req, res) => {
    const localIP = getLocalIP();
    const frontendPort = process.env.FRONTEND_PORT || 5173;
    const url = `http://${localIP}:${frontendPort}`;
    res.json({ url, ip: localIP });
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

  // ── Routes: App-Modus ─────────────────────────────────────────────
  // GET  /api/mode → { mode: 'crisis' | 'daily' }
  // POST /api/mode → { mode: 'crisis' | 'daily' } → 200 { mode, status }

  app.get('/api/mode', (_req, res) => {
    res.json({ mode: orch.getAppMode() });
  });

  app.post('/api/mode', (req, res) => {
    const { mode } = req.body || {};
    try {
      orch.setAppMode(mode);
      io.emit('app_mode_changed', { mode });  // Socket.io: alle Clients informieren
      res.json({ mode, status: 'ok' });
    } catch (err) {
      res.status(400).json({ error: err.message });
    }
  });

  // ── Routes: Vision (Feature #1) ───────────────────────────────────
  // Accepts: POST /api/vision
  // Body (JSON): { image: "<base64>", mimeType: "image/jpeg", prompt?: "..." }
  // Gemma 4 E4B has native vision — no external OCR or image service needed.

  app.post('/api/vision', async (req, res) => {
    const { image, mimeType = 'image/jpeg', prompt } = req.body || {};
    if (!image) {
      return res.status(400).json({ error: 'image (base64) is required' });
    }

    // Default prompt if user didn't provide context
    const analysisPrompt = prompt?.trim()
      || 'Analysiere dieses Bild. Beschreibe was du siehst und gib relevante Hilfestellung auf Deutsch. Bei medizinischen Befunden: Notruf 112.';

    const taskId = await orch.submitTask(analysisPrompt, [image]);
    res.status(202).json({ taskId, status: 'accepted', hasVision: true });
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

  // ── Routes: Personal Memory (Feature #2) ────────────────────────

  app.get('/api/memory', (_req, res) => {
    res.json(store.getAllMemories());
  });

  app.post('/api/memory', (req, res) => {
    const { key, value, category } = req.body || {};
    if (!key || !value) {
      return res.status(400).json({ error: 'key and value are required' });
    }
    const id = store.addMemory({ key, value, category });
    res.status(201).json({ id, key, value, category, status: 'gespeichert' });
  });

  app.delete('/api/memory/:id', (req, res) => {
    store.deleteMemory(parseInt(req.params.id));
    res.json({ status: 'gelöscht' });
  });

  app.delete('/api/memory', (_req, res) => {
    store.clearAllMemories();
    res.json({ status: 'alle Erinnerungen gelöscht' });
  });

  // ── Routes: Data Management (DSGVO / Feature #6) ────────────────

  app.delete('/api/chat/history', (_req, res) => {
    store.clearChatHistory();
    res.json({ status: 'Chatverlauf gelöscht' });
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
  // Persist data across restarts — MIMINOX_DB_PATH or ./miminox.db next to server/
  const dbPath = process.env.MIMINOX_DB_PATH
    || new URL('../miminox.db', import.meta.url).pathname;
  createServer({ port: 3001, dbPath });
  console.log(`💾 Datenbank: ${dbPath}`);
}
