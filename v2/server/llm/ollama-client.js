/**
 * ◑ MiMiNox v2 — Ollama Client
 * server/llm/ollama-client.js
 *
 * HTTP client for Ollama API (local LLM inference).
 * Port of core/chat.py Ollama integration.
 *
 * Features:
 *   - Streaming chat with tool-call detection
 *   - Connection error handling (OllamaNotReachableError)
 *   - Model not found detection
 *   - Tool schema registration
 */

const DEFAULT_BASE_URL = 'http://localhost:11434';
const DEFAULT_MODEL = 'gemma4:e4b';

// ── Custom Errors ───────────────────────────────────────────────────────

export class OllamaNotReachableError extends Error {
  constructor(url) {
    super(`Ollama ist nicht erreichbar unter ${url}. Läuft der Server?`);
    this.name = 'OllamaNotReachableError';
  }
}

export class ModelNotFoundError extends Error {
  constructor(model) {
    super(`Modell '${model}' nicht gefunden. Bitte mit 'ollama pull ${model}' installieren.`);
    this.name = 'ModelNotFoundError';
  }
}

// ── Tool Schemas (Ollama-kompatibel) ────────────────────────────────────

const TOOL_SCHEMAS = [
  {
    type: 'function',
    function: {
      name: 'web_search',
      description: 'Sucht im Internet via DuckDuckGo.',
      parameters: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'Die Suchanfrage' },
          max_results: { type: 'integer', description: 'Anzahl Ergebnisse (Standard: 5)', default: 5 },
        },
        required: ['query'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'read_file',
      description: 'Liest den Inhalt einer Datei.',
      parameters: {
        type: 'object',
        properties: {
          path: { type: 'string', description: 'Pfad zur Datei' },
        },
        required: ['path'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'list_directory',
      description: 'Listet den Inhalt eines Verzeichnisses.',
      parameters: {
        type: 'object',
        properties: {
          path: { type: 'string', description: 'Pfad zum Verzeichnis' },
        },
        required: ['path'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'get_datetime',
      description: 'Gibt aktuelles Datum und Uhrzeit zurück.',
      parameters: { type: 'object', properties: {} },
    },
  },
  {
    type: 'function',
    function: {
      name: 'run_shell',
      description: 'Führt einen Shell-Befehl aus (erfordert Bestätigung).',
      parameters: {
        type: 'object',
        properties: {
          command: { type: 'string', description: 'Der Shell-Befehl' },
        },
        required: ['command'],
      },
    },
  },
];

// ── Client ──────────────────────────────────────────────────────────────

export class OllamaClient {
  /**
   * @param {Object} opts
   * @param {string} [opts.baseUrl] - Ollama API base URL
   * @param {string} [opts.model]   - Default model name
   */
  constructor(opts = {}) {
    this.baseUrl = opts.baseUrl || DEFAULT_BASE_URL;
    this.model = opts.model || DEFAULT_MODEL;
  }

  /**
   * Chat with the LLM. Returns the full response (non-streaming).
   * For streaming, use chatStream().
   *
   * @param {Object} params
   * @param {string} [params.model]
   * @param {Array}  params.messages
   * @param {Array}  [params.tools]
   * @returns {Promise<Object>} - { content, toolCalls, model, totalDuration, evalCount }
   */
  async chat({ model, messages, tools } = {}) {
    const url = `${this.baseUrl}/api/chat`;
    const body = {
      model: model || this.model,
      messages,
      stream: false,
    };
    if (tools && tools.length > 0) {
      body.tools = tools;
    }

    let res;
    try {
      res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
    } catch (err) {
      throw new OllamaNotReachableError(this.baseUrl);
    }

    if (!res.ok) {
      const text = await res.text();
      if (text.includes('not found') || res.status === 404) {
        throw new ModelNotFoundError(model || this.model);
      }
      throw new Error(`Ollama error ${res.status}: ${text}`);
    }

    const data = await res.json();
    return {
      content: data.message?.content || '',
      toolCalls: data.message?.tool_calls || [],
      model: data.model,
      totalDuration: data.total_duration,
      evalCount: data.eval_count,
    };
  }

  /**
   * Chat with the LLM and stream the response.
   *
   * @param {Object} params
   * @param {string} [params.model]
   * @param {Array}  params.messages
   * @param {Array}  [params.tools]
   * @returns {AsyncGenerator<Object>} - Yields { content, toolCalls, done }
   */
  async *chatStream({ model, messages, tools } = {}) {
    const url = `${this.baseUrl}/api/chat`;
    const body = {
      model: model || this.model,
      messages,
      stream: true,
    };
    if (tools && tools.length > 0) {
      body.tools = tools;
    }

    let res;
    try {
      res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
    } catch (err) {
      throw new OllamaNotReachableError(this.baseUrl);
    }

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Ollama streaming error ${res.status}: ${text}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.trim()) continue;
          let data;
          try {
            data = JSON.parse(line);
          } catch (e) {
            continue;
          }

          if (data.error) throw new Error(data.error);

          yield {
            content: data.message?.content || '',
            toolCalls: data.message?.tool_calls || [],
            done: data.done || false,
            model: data.model,
          };
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Returns Ollama-compatible tool schemas.
   * @returns {Array}
   */
  getToolSchemas() {
    return [...TOOL_SCHEMAS];
  }

  /**
   * Parse a raw Ollama response into structured { content, toolCalls }.
   * Useful for unit testing without a live Ollama instance.
   * @param {Object} raw - Raw Ollama API response
   * @returns {{ content: string, toolCalls: Array }}
   */
  parseResponse(raw) {
    return {
      content: raw.message?.content || '',
      toolCalls: raw.message?.tool_calls || [],
    };
  }
  /**
   * Checks if Ollama is reachable and if the default model is loaded.
   * @returns {Promise<boolean>}
   */
  async checkHealth() {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 2000); // 2s timeout

      const res = await fetch(`${this.baseUrl}/api/tags`, { signal: controller.signal });
      clearTimeout(timer);

      if (!res.ok) return false;

      const data = await res.json();
      const models = data.models || [];
      return models.some(m => m.name.startsWith(this.model));
    } catch (err) {
      return false;
    }
  }
}
