/**
 * ◑ MiMiNox v2 — Agent Worker Script
 * server/workers/agent-worker.js
 *
 * Runs inside a worker_thread. Receives messages from main thread,
 * executes LLM calls or mock tasks, sends results back.
 *
 * Message Protocol (Main → Worker):
 *   { type: "execute", prompt, mock?, mockDelay?, ollamaUrl?, model? }
 *   { type: "crash" }  (for testing crash recovery)
 *
 * Message Protocol (Worker → Main):
 *   { type: "spawned", agentId }
 *   { type: "chunk", content }
 *   { type: "done", result }
 *   { type: "error", error }
 */

import { parentPort, workerData } from 'node:worker_threads';

const { agentId, role, timeout } = workerData;

// T-05/T-06: Konfiguration via Env-Variable (kein Hardcode)
const DEFAULT_OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434';
const DEFAULT_MODEL      = process.env.MIMI_NOX_MODEL || 'gemma4:e4b';

// Notify main thread that we're alive
parentPort.postMessage({ type: 'spawned', agentId, role });

// Handle messages from main thread
parentPort.on('message', async (msg) => {
  switch (msg.type) {
    case 'execute':
      await handleExecute(msg);
      break;

    case 'crash':
      // Intentional crash for testing
      process.exit(1);
      break;

    default:
      parentPort.postMessage({
        type: 'error',
        agentId,
        error: `Unbekannter Message-Typ: ${msg.type}`,
      });
  }
});

async function handleExecute(msg) {
  try {
    if (msg.mock) {
      // Mock mode: simulate LLM with delay
      const delay = msg.mockDelay || 50;
      await sleep(delay);
      parentPort.postMessage({
        type: 'done',
        agentId,
        result: `[Mock] Aufgabe erledigt: ${msg.prompt}`,
      });
    } else {
      // T-06: Echter Ollama HTTP-Call (kein [TODO] mehr)
      await callOllama(msg);
    }
  } catch (err) {
    parentPort.postMessage({
      type: 'error',
      agentId,
      error: err.message,
    });
  }
}

/**
 * T-06: Ruft Ollama /api/generate auf und streamt Chunks zurück.
 * Nutzt ollamaUrl/model aus der execute-Message, Fallback auf Env-Variable.
 *
 * @param {Object} msg - execute message
 * @param {string} msg.prompt
 * @param {string} [msg.ollamaUrl]  - z.B. http://localhost:11434
 * @param {string} [msg.model]      - z.B. gemma4:e4b
 * @param {string} [msg.systemPrompt]
 */
async function callOllama(msg) {
  const ollamaUrl   = msg.ollamaUrl || DEFAULT_OLLAMA_URL;
  const model       = msg.model     || DEFAULT_MODEL;
  const endpoint    = `${ollamaUrl}/api/generate`;

  const body = JSON.stringify({
    model,
    prompt:    msg.systemPrompt ? `${msg.systemPrompt}\n\n${msg.prompt}` : msg.prompt,
    stream:    true,
    options: { temperature: 0.7 },
  });

  let response;
  try {
    response = await fetch(endpoint, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      signal:  AbortSignal.timeout(msg.timeout || timeout || 60000),
    });
  } catch (err) {
    // ECONNREFUSED, Timeout, oder anderer Netzwerkfehler
    const label = err.name === 'TimeoutError'
      ? `Ollama Timeout nach ${msg.timeout || timeout}ms`
      : `Ollama nicht erreichbar (${ollamaUrl}): ${err.message}`;
    throw new Error(label);
  }

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(`Ollama HTTP ${response.status}: ${text.slice(0, 200)}`);
  }

  // Streaming: jede Zeile ist ein JSON-Objekt mit { response, done }
  const reader  = response.body.getReader();
  const decoder = new TextDecoder();
  let   fullText = '';
  let   buffer   = '';

  while (true) {
    const { value, done: streamDone } = await reader.read();
    if (streamDone) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // letzte unvollständige Zeile behalten

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const parsed = JSON.parse(line);
        if (parsed.response) {
          fullText += parsed.response;
          // Chunk an Main-Thread senden
          parentPort.postMessage({ type: 'chunk', agentId, content: parsed.response });
        }
        if (parsed.done) break;
      } catch {
        // Malformed JSON-Zeile überspringen
      }
    }
  }

  parentPort.postMessage({
    type:   'done',
    agentId,
    result: fullText.trim() || '[Leere Antwort von Ollama]',
  });
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
