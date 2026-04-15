/**
 * ◑ MiMiNox v2 — Tool Engine
 * server/tools/engine.js
 *
 * Port von Python core/tools.py.
 * Sichere Tool-Ausführung mit Whitelist, Confirmation Gate, und Schema-Registry.
 *
 * Sicherheit:
 *   - Path-Whitelist für read_file/list_directory
 *   - Shell-Confirmation-Gate (nie direkt ausführen)
 *   - Ollama-kompatible Tool-Schemas
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import { PythonBridge } from '../bridge/python-bridge.js';

// ── Custom Errors ───────────────────────────────────────────────────

export class ShellConfirmationRequired extends Error {
  constructor(command) {
    super(`Shell-Bestätigung erforderlich für: ${command}`);
    this.name = 'ShellConfirmationRequired';
    this.command = command;
  }
}

export class FileNotAllowedError extends Error {
  constructor(filePath) {
    super(`Zugriff verweigert: '${filePath}' ist nicht in der Whitelist.`);
    this.name = 'FileNotAllowedError';
    this.path = filePath;
  }
}

// ── Schemas (Ollama-kompatibel) ─────────────────────────────────────

const SCHEMAS = [
  {
    type: 'function',
    function: {
      name: 'web_search',
      description: 'Sucht im Internet via DuckDuckGo.',
      parameters: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'Die Suchanfrage' },
          max_results: { type: 'integer', description: 'Max Ergebnisse', default: 5 },
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
      description: 'Führt Shell-Befehl aus (erfordert Bestätigung).',
      parameters: {
        type: 'object',
        properties: {
          command: { type: 'string', description: 'Der Shell-Befehl' },
        },
        required: ['command'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'search_knowledge',
      description: 'Sucht in der lokalen Krisen-Wissensbasis (Medizin, Technik, Survival).',
      parameters: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'Die Suchanfrage' },
          domain: { type: 'string', enum: ['medical', 'engineering', 'survival'], description: 'Optionaler Wissensbereich' },
          top_k: { type: 'integer', description: 'Max Ergebnisse', default: 3 },
        },
        required: ['query'],
      },
    },
  },
];

// ── Engine ──────────────────────────────────────────────────────────

export class ToolEngine {
  /**
   * @param {Object} opts
   * @param {string[]} [opts.whitelist] - Allowed root paths for file access
   */
  constructor(opts = {}) {
    this._whitelist = opts.whitelist || [process.env.HOME || '/home'];
    this._bridge = opts.bridge || new PythonBridge();
    this._tools = new Map();
    this._registerBuiltins();
  }

  _registerBuiltins() {
    this._tools.set('get_datetime', this._getDatetime.bind(this));
    this._tools.set('run_shell', this._runShell.bind(this));
    this._tools.set('read_file', this._readFile.bind(this));
    this._tools.set('list_directory', this._listDirectory.bind(this));
    this._tools.set('web_search', this._webSearch.bind(this));
    this._tools.set('file_search', this._fileSearch.bind(this));
    this._tools.set('analyze_image', this._analyzeImage.bind(this));
    this._tools.set('search_knowledge', this._searchKnowledge.bind(this));
  }

  /**
   * Execute a tool by name.
   * @param {string} name
   * @param {Object} args
   * @returns {Promise<string>}
   */
  async execute(name, args) {
    const fn = this._tools.get(name);
    if (!fn) throw new Error(`Tool '${name}' nicht gefunden.`);
    return fn(args);
  }

  /** Check if a tool exists. */
  hasTool(name) {
    return this._tools.has(name);
  }

  /** Get all Ollama-compatible tool schemas. */
  getSchemas() {
    return [...SCHEMAS];
  }

  // ── Built-in Tools ────────────────────────────────────────────────

  async _getDatetime() {
    const now = new Date();
    const formatter = new Intl.DateTimeFormat('de-DE', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: 'Europe/Berlin',
    });
    return formatter.format(now);
  }

  async _runShell({ command }) {
    // NEVER execute directly — always require confirmation
    throw new ShellConfirmationRequired(command);
  }

  async _readFile({ path: filePath }) {
    const resolved = path.resolve(filePath);
    this._checkWhitelist(resolved);
    const content = await fs.readFile(resolved, 'utf-8');
    const MAX = 50000;
    if (content.length > MAX) {
      return content.slice(0, MAX) + `\n\n... [Datei gekürzt, ${content.length} Zeichen gesamt]`;
    }
    return content;
  }

  async _listDirectory({ path: dirPath }) {
    const resolved = path.resolve(dirPath);
    this._checkWhitelist(resolved);
    const entries = await fs.readdir(resolved, { withFileTypes: true });
    return entries
      .map(e => `${e.isDirectory() ? '📁' : '📄'} ${e.name}`)
      .join('\n');
  }

  async _webSearch({ query, max_results = 5 }) {
    // Placeholder — will use DuckDuckGo API or Python bridge
    return `[Web-Suche für "${query}" — Ergebnisse werden via Python-Bridge geladen]`;
  }

  async _fileSearch({ query, directory }) {
    return `[Dateisuche für "${query}" in ${directory || '.'} — wird implementiert]`;
  }

  async _analyzeImage({ path: imgPath, question }) {
    return `[Vision-Analyse für "${imgPath}" — wird via Gemma4 Vision implementiert]`;
  }

  async _searchKnowledge({ query, domain, top_k = 3 }) {
    try {
      const results = await this._bridge.callModule('core.memory_utils', 'search', {
        query,
        top_k,
        collection: 'mimi_nox_knowledge'
      });

      if (!Array.isArray(results) || results.length === 0) {
        return "Keine relevanten Informationen in der lokalen Wissensbasis gefunden.";
      }

      const relevant = results.filter(res => res.score >= 0.42);
      if (relevant.length === 0) {
        return "Keine ausreichend relevanten Informationen in der lokalen Wissensbasis gefunden.";
      }

      let output = `Gefundene Informationen (Offline-Wissensbasis):\n`;
      for (const res of relevant) {
        output += `• ${res.text} (Quelle: ${res.metadata.source || 'unbekannt'})\n`;
      }
      return output;
    } catch (err) {
      return `Fehler bei der Wissensabfrage: ${err.message}`;
    }
  }

  // ── Security ──────────────────────────────────────────────────────

  _checkWhitelist(resolvedPath) {
    const allowed = this._whitelist.some(w =>
      resolvedPath.startsWith(path.resolve(w))
    );
    if (!allowed) {
      throw new FileNotAllowedError(resolvedPath);
    }
  }
}
