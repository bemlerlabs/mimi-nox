/**
 * ◑ MiMiNox v2 — Test: Express + Socket.io Server
 * Task 1.1: Core-Server Setup (+ StateStore Wiring)
 * TDD: Tests FIRST, then implementation.
 */
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { createServer } from '../server/index.js';

describe('Task 1.1: Core-Server Setup', () => {
  let app, server, store, baseUrl;

  beforeAll(async () => {
    const result = createServer({ port: 0 }); // random port
    app = result.app;
    server = result.server;
    store = result.store;
    await new Promise(resolve => server.on('listening', resolve));
    const addr = server.address();
    baseUrl = `http://localhost:${addr.port}`;
  });

  afterAll(() => {
    store?.close();
    server?.close();
  });

  // ── Health ────────────────────────────────────────────────────────

  it('[D] GET /api/health antwortet mit status ok', async () => {
    const res = await fetch(`${baseUrl}/api/health`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.status).toBe('ok');
    expect(body.version).toBe('2.0.0');
  });

  // ── Agents (wired to StateStore) ──────────────────────────────────

  it('[D] GET /api/agents gibt leere Liste zurück', async () => {
    const res = await fetch(`${baseUrl}/api/agents`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  it('[D] GET /api/agents returns agents from StateStore', async () => {
    store.createAgent({ id: 'test_alice', role: 'ceo', status: 'running' });
    const res = await fetch(`${baseUrl}/api/agents`);
    const body = await res.json();
    expect(body.some(a => a.id === 'test_alice')).toBe(true);
    expect(body.find(a => a.id === 'test_alice').role).toBe('ceo');
  });

  // ── Tasks ─────────────────────────────────────────────────────────

  it('[D] POST /api/tasks gibt 202 mit taskId zurück', async () => {
    const res = await fetch(`${baseUrl}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: 'Baue eine App' }),
    });
    expect(res.status).toBe(202);
    const body = await res.json();
    expect(body.taskId).toBeDefined();
    expect(typeof body.taskId).toBe('string');
  });

  // ── Chat History (wired to StateStore) ────────────────────────────

  it('[D] GET /api/chat/history returns messages from StateStore', async () => {
    store.addChatMessage({ from: 'alice', to: 'bob', content: 'Sprint starten', type: 'directive' });
    const res = await fetch(`${baseUrl}/api/chat/history`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.some(m => m.content === 'Sprint starten')).toBe(true);
  });

  // ── Kanban (wired to StateStore) ──────────────────────────────────

  it('[D] GET /api/kanban returns grouped tickets', async () => {
    store.createTicket({ title: 'API bauen', assignee: 'charlie', createdBy: 'bob' });
    const ticketId = store.createTicket({ title: 'Tests schreiben', assignee: 'charlie', createdBy: 'bob' });
    store.updateTicketStatus(ticketId, 'in_progress');

    const res = await fetch(`${baseUrl}/api/kanban`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.backlog.length).toBeGreaterThanOrEqual(1);
    expect(body.in_progress.length).toBeGreaterThanOrEqual(1);
    expect(body).toHaveProperty('testing');
    expect(body).toHaveProperty('done');
  });
});
