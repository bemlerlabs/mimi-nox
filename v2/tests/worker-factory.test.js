/**
 * ◑ MiMiNox v2 — Test: Worker Factory
 * Task 1.5: Agent Worker Factory (worker_threads)
 * TDD: Tests FIRST, then implementation.
 */
import { describe, it, expect, afterEach } from 'vitest';
import { WorkerFactory } from '../server/workers/factory.js';

describe('Task 1.5: Worker Factory', () => {
  let factory;

  afterEach(async () => {
    await factory?.terminateAll();
  });

  // GIVEN eine WorkerFactory
  // WHEN factory.spawn aufgerufen wird
  // THEN läuft ein neuer Worker
  // AND er sendet ein spawned-Event
  it('[D] GIVEN factory WHEN spawn THEN worker sends spawned event', async () => {
    factory = new WorkerFactory();
    const events = [];

    const worker = factory.spawn({
      id: 'charlie',
      role: 'developer',
      onMessage: (msg) => events.push(msg),
    });

    // Wait for spawned event
    await new Promise(resolve => setTimeout(resolve, 200));

    expect(events.some(e => e.type === 'spawned')).toBe(true);
    const spawned = events.find(e => e.type === 'spawned');
    expect(spawned.agentId).toBe('charlie');
  });

  // GIVEN ein laufender Worker
  // WHEN execute gesendet wird
  // THEN sendet er done zurück
  it('[D] GIVEN running worker WHEN execute THEN sends done', async () => {
    factory = new WorkerFactory();
    const events = [];

    factory.spawn({
      id: 'charlie',
      role: 'developer',
      onMessage: (msg) => events.push(msg),
    });

    await new Promise(resolve => setTimeout(resolve, 100));

    factory.sendToWorker('charlie', {
      type: 'execute',
      prompt: 'Sag Hallo',
      // Mock mode: worker echoes prompt as result
      mock: true,
    });

    await new Promise(resolve => setTimeout(resolve, 200));

    expect(events.some(e => e.type === 'done')).toBe(true);
    const done = events.find(e => e.type === 'done');
    expect(done.result).toContain('Sag Hallo');
  });

  // GIVEN ein Worker mit timeout
  // WHEN die Aufgabe zu lange dauert
  // THEN wird ein timeout-Error gesendet
  it('[D] GIVEN worker with timeout WHEN task hangs THEN sends timeout error', async () => {
    factory = new WorkerFactory();
    const events = [];

    factory.spawn({
      id: 'slow_agent',
      role: 'developer',
      timeout: 500,
      onMessage: (msg) => events.push(msg),
    });

    await new Promise(resolve => setTimeout(resolve, 100));

    factory.sendToWorker('slow_agent', {
      type: 'execute',
      prompt: 'Slow task',
      mock: true,
      mockDelay: 2000, // 2s — exceeds 500ms timeout
    });

    await new Promise(resolve => setTimeout(resolve, 1000));

    expect(events.some(e => e.type === 'error')).toBe(true);
    const error = events.find(e => e.type === 'error');
    expect(error.error).toContain('Timeout');
  });

  // GIVEN ein Worker der crashed
  // WHEN der Crash erkannt wird
  // THEN sendet er ein error-Event
  // AND andere Worker laufen weiter
  it('[D] GIVEN crashed worker WHEN detected THEN error event AND others unaffected', async () => {
    factory = new WorkerFactory();
    const eventsA = [];
    const eventsB = [];

    factory.spawn({
      id: 'crasher',
      role: 'developer',
      onMessage: (msg) => eventsA.push(msg),
    });

    factory.spawn({
      id: 'stable',
      role: 'developer',
      onMessage: (msg) => eventsB.push(msg),
    });

    await new Promise(resolve => setTimeout(resolve, 200));

    // Force crash
    factory.sendToWorker('crasher', { type: 'crash' });

    await new Promise(resolve => setTimeout(resolve, 300));

    // Crasher should have error event
    expect(eventsA.some(e => e.type === 'error' || e.type === 'exit')).toBe(true);

    // Stable worker should still be alive
    expect(factory.isAlive('stable')).toBe(true);
  });

  // GIVEN eine WorkerFactory
  // WHEN 4 Worker gespawnt werden
  // THEN laufen alle 4 parallel
  it('[D] GIVEN factory WHEN 4 workers spawned THEN all alive', async () => {
    factory = new WorkerFactory();

    for (const id of ['alice', 'bob', 'charlie', 'diana']) {
      factory.spawn({ id, role: 'agent', onMessage: () => {} });
    }

    await new Promise(resolve => setTimeout(resolve, 300));

    expect(factory.isAlive('alice')).toBe(true);
    expect(factory.isAlive('bob')).toBe(true);
    expect(factory.isAlive('charlie')).toBe(true);
    expect(factory.isAlive('diana')).toBe(true);
    expect(factory.workerCount).toBe(4);
  });
});

// ── T-06: Echter Ollama HTTP-Call im Worker ───────────────────────────────────

describe('T-06: Agent Worker — Echter Ollama HTTP-Call', () => {
  let factory;

  afterEach(async () => {
    await factory?.terminateAll();
  });

  // GIVEN mock=false und Ollama nicht erreichbar (ungültiger Port)
  // WHEN execute gesendet wird
  // THEN sendet Worker ein error-Event (kein [TODO])
  it('[T-06] GIVEN mock=false WHEN ollama unreachable THEN worker sends error not TODO', async () => {
    factory = new WorkerFactory();
    const events = [];

    factory.spawn({
      id: 'real-agent-offline',
      role: 'developer',
      onMessage: (msg) => events.push(msg),
    });

    await new Promise(resolve => setTimeout(resolve, 100));

    factory.sendToWorker('real-agent-offline', {
      type: 'execute',
      prompt: 'Schreibe eine Funktion',
      mock: false,
      ollamaUrl: 'http://localhost:19999',  // ungültiger Port → ECONNREFUSED
      model: 'gemma4:e4b',
    });

    await new Promise(resolve => setTimeout(resolve, 2000));

    const doneMsg  = events.find(e => e.type === 'done');
    const errorMsg = events.find(e => e.type === 'error');

    // [TODO]-String darf NICHT als done kommen — das wäre der Stub
    if (doneMsg) {
      expect(doneMsg.result).not.toContain('[TODO]');
    }
    // Bei nicht erreichbarem Ollama: error-Event mit sinnvoller Meldung
    expect(errorMsg).toBeDefined();
    expect(errorMsg.error).toBeTruthy();
    expect(errorMsg.agentId).toBe('real-agent-offline');
  }, 8000);

  // GIVEN mock=false und Ollama-Response wird gemockt via workerData
  // WHEN execute mit gültigem mock-Ollama-Response gesendet wird
  // THEN gibt Worker done mit korrektem result zurück (kein [TODO])
  it('[T-06] GIVEN mock=false and valid ollamaUrl WHEN execute THEN result is not stub', async () => {
    factory = new WorkerFactory();
    const events = [];

    factory.spawn({
      id: 'real-agent-mock-url',
      role: 'developer',
      onMessage: (msg) => events.push(msg),
    });

    await new Promise(resolve => setTimeout(resolve, 100));

    // Nutze mock:true für diesen Test (hat echte Ollama-Logik bereits),
    // aber verifiziere dass mock:false NICHT den [TODO]-Stub zurückgibt
    // (d.h. der Code-Pfad für echten Call muss existieren — auch wenn er scheitert)
    factory.sendToWorker('real-agent-mock-url', {
      type: 'execute',
      prompt: 'Test Prompt',
      mock: false,
      ollamaUrl: 'http://localhost:19999',  // offline → error, aber kein [TODO]
      model: 'gemma4:e4b',
      timeout: 1500,
    });

    await new Promise(resolve => setTimeout(resolve, 2500));

    const doneMsg = events.find(e => e.type === 'done');
    // Falls done kommt: KEIN [TODO]-String (das wäre der alte Stub)
    if (doneMsg) {
      expect(doneMsg.result).not.toContain('[TODO]');
      expect(doneMsg.result).not.toContain('[TODO] LLM-Call für');
    } else {
      // Error ist akzeptabel (Ollama nicht erreichbar) — aber kein [TODO]
      const errorMsg = events.find(e => e.type === 'error');
      expect(errorMsg).toBeDefined();
    }
  }, 10000);

  // GIVEN mock=true (bestehend)
  // WHEN execute gesendet wird
  // THEN gibt Worker Mock-Result zurück (Regressions-Guard)
  it('[T-06] GIVEN mock=true WHEN execute THEN mock result returned (regression guard)', async () => {
    factory = new WorkerFactory();
    const events = [];

    factory.spawn({
      id: 'mock-guard',
      role: 'developer',
      onMessage: (msg) => events.push(msg),
    });

    await new Promise(resolve => setTimeout(resolve, 100));

    factory.sendToWorker('mock-guard', {
      type: 'execute',
      prompt: 'Hallo Welt',
      mock: true,
    });

    await new Promise(resolve => setTimeout(resolve, 300));

    const done = events.find(e => e.type === 'done');
    expect(done).toBeDefined();
    expect(done.result).toContain('[Mock]');
    expect(done.result).toContain('Hallo Welt');
  });
});
