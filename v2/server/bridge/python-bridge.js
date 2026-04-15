/**
 * ◑ MiMiNox v2 — Python Bridge
 * server/bridge/python-bridge.js
 *
 * Executes Python code via child_process.
 * Enables reuse of existing Python tools (memory, vision, browser, RAG)
 * until they are fully ported to Node.js.
 *
 * Sicherheit:
 *   - Timeout-basiert (kein Hängen)
 *   - stderr → BridgeError
 *   - Kein direkter Zugriff auf Node.js State
 *   - T-05: MIMINOX_ROOT env-Variable statt Hardcode
 *   - T-05: Triple-Quote JSON-Embedding statt einfache Apostrophe (Injection-Schutz)
 */

import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const execFileAsync = promisify(execFile);

// ── Custom Errors ───────────────────────────────────────────────────

export class BridgeError extends Error {
  constructor(message, stderr) {
    super(message);
    this.name = 'BridgeError';
    this.stderr = stderr;
  }
}

export class BridgeTimeoutError extends Error {
  constructor(timeout) {
    super(`Python-Bridge Timeout nach ${timeout}ms`);
    this.name = 'BridgeTimeoutError';
    this.timeout = timeout;
  }
}

// ── Bridge ──────────────────────────────────────────────────────────

export class PythonBridge {
  /**
   * @param {Object} opts
   * @param {string} [opts.pythonPath] - Path to Python executable
   * @param {number} [opts.timeout]    - Max execution time in ms
   */
  constructor(opts = {}) {
    const root = process.env.MIMINOX_ROOT || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
    const venvPath = path.join(root, '.venv', 'bin', 'python3');
    
    this.pythonPath = opts.pythonPath || venvPath; // Prefer venv if exists
    this.timeout = opts.timeout || 30000;

    // Fallback if venv doesn't exist (though usually it should)
    import('node:fs').then(fs => {
      if (!fs.existsSync(this.pythonPath)) {
        this.pythonPath = 'python3';
      }
    });
  }

  /**
   * Evaluate a Python expression/statement and return stdout.
   * @param {string} code - Python code to execute
   * @returns {Promise<string>} stdout output, trimmed
   */
  async eval(code) {
    const isStatement = code.includes('print') || code.includes(';')
      || code.includes('\n') || /^(import |from |for |if |def |class |while |try |with )/.test(code.trim());
    const wrappedCode = isStatement ? code : `print(${code})`;

    try {
      const { stdout, stderr } = await execFileAsync(
        this.pythonPath,
        ['-c', wrappedCode],
        { timeout: this.timeout, maxBuffer: 1024 * 1024 }
      );

      if (stderr && stderr.trim()) {
        // Python warnings are okay, but errors should propagate
        if (stderr.includes('Error') || stderr.includes('Traceback')) {
          throw new BridgeError(`Python-Fehler: ${stderr.trim()}`, stderr);
        }
      }

      return stdout.trim();
    } catch (err) {
      if (err instanceof BridgeError) throw err;

      if (err.killed || err.signal === 'SIGTERM') {
        throw new BridgeTimeoutError(this.timeout);
      }

      if (err.stderr && (err.stderr.includes('Error') || err.stderr.includes('Traceback'))) {
        throw new BridgeError(`Python-Fehler: ${err.stderr.trim()}`, err.stderr);
      }

      throw new BridgeError(`Bridge-Fehler: ${err.message}`, err.stderr || '');
    }
  }

  /**
   * Baut den Python-Code für callModule().
   * Extrahiert für Testbarkeit und Konfigurierbarkeit.
   *
   * T-05: Root-Pfad aus MIMINOX_ROOT env-Variable (kein Hardcode).
   * T-05: JSON via triple-quoted string (Injection-Schutz gegen Apostrophe).
   *
   * @param {string} module - Python module (e.g. "core.memory")
   * @param {string} func   - Function name
   * @param {Object} args   - Arguments as plain object
   * @returns {string} Python code ready to exec via eval()
   */
  _buildModuleCode(module, func, args = {}) {
    // T-05: MIMINOX_ROOT env → kein Hardcode mehr
    const root = process.env.MIMINOX_ROOT
      || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');

    // QA-Fix T-05: Base64-Encoding statt Triple-Quotes
    // Triple-Quotes wären bei args-Werten mit ''' unsicher (Python SyntaxError).
    // Base64 enthält nur [A-Za-z0-9+/=] → keine Injection möglich.
    const argsB64 = Buffer.from(JSON.stringify(args)).toString('base64');

    return [
      'import json, sys, base64',
      `sys.path.insert(0, '${root}')`,
      `from ${module} import ${func}`,
      `result = ${func}(**json.loads(base64.b64decode('${argsB64}').decode()))`,
      'print(json.dumps(result, default=str))',
    ].join('\n');
  }

  /**
   * Call a function in a Python module from the MiMiNox core.
   * @param {string} module   - Module path (e.g. "core.memory")
   * @param {string} func     - Function name (e.g. "search")
   * @param {Object} args     - Arguments as JSON
   * @returns {Promise<Object>} - Parsed JSON result
   */
  async callModule(module, func, args = {}) {
    const code = this._buildModuleCode(module, func, args);
    const stdout = await this.eval(code);
    try {
      return JSON.parse(stdout);
    } catch {
      return stdout;
    }
  }
}
