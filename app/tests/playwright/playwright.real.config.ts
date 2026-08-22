import { defineConfig } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// ESM: `__dirname`/`require` sind in einem "type":"module"-Paket nicht verfügbar.
const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * E2E gegen den ECHTEN MiMi Nox Server (FastAPI) — kein Mock, kein Stub.
 *
 * - webServer: app/tests/e2e_server.py startet den produktionsgleichen
 *   FastAPI-Server (uvicorn) auf 127.0.0.1:8765 mit isoliertem, leerem
 *   Config-Dir (frisch: engine.json fehlt → First-Run-Setup-Flow).
 * - Frontend: ECHTER Build aus app/dist (Muss vorher `npm run build`).
 * - Test-Engine: ECHTE DGX Spark (OpenAI-kompatibel, SGLang) — die Probe
 *   und der Chat laufen gegen die reale In-Netz-Engine, kein Ollama.
 *
 * Voraussetzungen (werden im Test selbst mit klaren Fehlern geprüft):
 *   1. app/dist/ existiert          → `npm run build`
 *   2. DGX erreichbar               → MIMI_NOX_E2E_DGX_URL (Default: Spark-Tailnet)
 *   3. Python-Venv mit FastAPI/uvicorn/httpx
 *
 * Kein Mock: Der Test-Flow ist der echte End-User-Flow:
 *   /  (unconfigured) → Setup-Page → Endpunkt-Input → Probe → Modell-Picker
 *   → Übernehmen → Chat → Nachricht an ECHTE DGX → Assistant-Antwort.
 */
// venv-Python (System-python3 hat keine FastAPI/uvicorn). Override via MIMI_NOX_PYTHON.
// Config-Dir: <repo>/app/tests/playwright → Repo-Root ist 3 Ebenen hoch.
const python =
  process.env.MIMI_NOX_PYTHON ||
  path.resolve(__dirname, '../../../.venv/bin/python');

export default defineConfig({
  testDir: './setup-e2e',
  timeout: 60000, // DGX-Inferenz: großzügig (27B-Modell, erste Tokens können dauern)
  expect: { timeout: 20000 },
  retries: 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  outputDir: './test-results-real',
  use: {
    headless: true,
    baseURL: 'http://127.0.0.1:8765',
    viewport: { width: 1280, height: 800 },
    ignoreHTTPSErrors: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: `${python} tests/e2e_server.py`,
    cwd: '../..',
    url: 'http://127.0.0.1:8765/api/health',
    timeout: 120000,
    reuseExistingServer: false,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
