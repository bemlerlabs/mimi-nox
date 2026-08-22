import { test, expect } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

// ESM: `__dirname` ist in einem "type":"module"-Paket nicht verfügbar.
const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * E2E gegen den ECHTEN MiMi Nox Server — kein Mock, keine Stubs, echte
 * Chromium, echte DGX (SGLang/OpenAI-kompatibel).
 *
 * Testet den kompletten End-User-First-Run-Flow:
 *
 *   1. PWA lädt → Setup-Page (Engine-Auswahl), weil kein engine.json existiert
 *   2. User wählt "OpenAI-kompatible API" (DGX Spark via Tailnet)
 *   3. Endpunkt-Input → Probe → echte Modell-Liste von der DGX (/v1/models)
 *   4. Modell-Auswahl → Übernehmen → engine.json wird persistiert
 *   5. App zeigt jetzt den Chat (configured=true)
 *   6. Chat-Nachricht → ECHTE Inferenz auf der DGX → Assistant-Antwort
 *
 * Voraussetzung: DGX erreichbar (MIMI_NOX_E2E_DGX_URL oder Default-Tailnet).
 * Kein Ollama, kein gemma4 — der E2E nutzt die schnelle Remote-Engine,
 * weil Ollama auf dem MacBook zu langsam wäre (User-Mandat 2026-08-21).
 */

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..', '..');
const E2E_CONFIG_DIR = path.join(REPO_ROOT, '.e2e-runtime', 'config');
const E2E_ENGINE_JSON = path.join(E2E_CONFIG_DIR, 'engine.json');

const DGX_URL =
  process.env.MIMI_NOX_E2E_DGX_URL || 'http://spark-2c73.tail8f685e.ts.net:8000/v1';

// DGX-Inferenz (27B, SGLang): erste Antwort kann mehrere Sekunden brauchen.
const CHAT_TIMEOUT = 90000;

test.describe('MiMi Nox First-Run E2E (echter Server + echte DGX, kein Mock)', () => {

  test.beforeAll(async () => {
    // Precondition: DGX-Engine erreichbar — sonst kein sinnvoller E2E-Lauf.
    // (Der Server-Probe würde das auch melden, aber eine saubere
    // Precondition-Fehlermeldung ist besser als ein geplatzter UI-Test.)
    const res = await fetch(`${DGX_URL.replace(/\/v1$/, '')}/v1/models`);
    if (!res.ok) {
      throw new Error(
        `DGX-Engine nicht erreichbar (${DGX_URL}): HTTP ${res.status}. ` +
        `MIMI_NOX_E2E_DGX_URL setzen oder DGX-Spark starten.`
      );
    }
    const data = await res.json();
    const ids = (data.data || []).map((m: { id: string }) => m.id);
    if (ids.length === 0) {
      throw new Error(`DGX-Engine antwortet, listet aber keine Modelle: ${JSON.stringify(data)}`);
    }
    console.log(`[e2e] DGX erreichbar, Modelle: ${ids.join(', ')}`);
  });

  test('First-Run: Setup-Page → DGX-Probe → Modell-Auswahl → Chat mit echter Inferenz', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    // ── 1. PWA lädt → Setup-Page (kein engine.json → configured=false) ──
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    const setupPage = page.locator('[data-testid="setup-page"]');
    await expect(setupPage).toBeVisible({ timeout: 15000 });
    await expect(setupPage.getByRole('heading', { name: /Engine/i })).toBeVisible();

    // ── 2. Provider wählen: OpenAI-kompatible API (DGX) ──
    await page.locator('[data-testid="setup-option-openai"]').click();
    // Endpunkt-Input erscheint (nur bei Remote-Engines)
    await expect(page.locator('[data-testid="setup-endpoint"]')).toBeVisible();

    // ── 3. Endpunkt eingeben + Probe (echter /api/model/providers/probe →
    //    Backend → DGX /v1/models) ──
    await page.locator('[data-testid="setup-endpoint"]').fill(DGX_URL);
    await page.locator('[data-testid="setup-probe"]').click();

    const status = page.locator('[data-testid="setup-status"]');
    await expect(status).toBeVisible({ timeout: 15000 });
    await expect(status).toContainText(/erreichbar/i, { timeout: 15000 });

    // Modell-Select mit den echten DGX-Modellen
    const modelSelect = page.locator('[data-testid="setup-model"]');
    await expect(modelSelect).toBeVisible({ timeout: 10000 });
    const modelOptions = await modelSelect.locator('option').allTextContents();
    expect(modelOptions.length).toBeGreaterThan(0);
    console.log(`[e2e] DGX-Probe listet Modelle: ${modelOptions.join(', ')}`);
    // Ersten (Default-)Modell bestätigen
    await modelSelect.selectOption({ index: 0 });
    const selectedModel = await modelSelect.inputValue();

    // ── 4. Übernehmen → POST /api/settings (Session-Override + engine.json) ──
    await page.locator('[data-testid="setup-finish"]').click();

    // Persistenz prüfen: engine.json in isoliertem E2E-Config-Dir
    await page.waitForTimeout(500); // Persist ist serverseitig synchron
    expect(fs.existsSync(E2E_ENGINE_JSON)).toBe(true);
    const persisted = JSON.parse(fs.readFileSync(E2E_ENGINE_JSON, 'utf-8'));
    expect(persisted.provider).toBe('openai_compatible');
    expect(persisted.model).toBe(selectedModel);
    expect(persisted.api_url).toBe(DGX_URL);
    console.log(`[e2e] engine.json persistiert:`, JSON.stringify(persisted));

    // ── 5. Nach Persist → App re-checkt Status → Chat (kein Setup mehr) ──
    await page.goto('/#/chat', { waitUntil: 'domcontentloaded' });
    const chatPanel = page.locator('[data-testid="panel-chat"]');
    await expect(chatPanel).toBeVisible({ timeout: 20000 });

    // Setup-Page darf NIE wieder sichtbar sein (configured=true)
    await expect(page.locator('[data-testid="setup-page"]')).toHaveCount(0);

    // ── 6. ECHTE Inferenz: Chat-Nachricht an die DGX ──
    const input = page.locator('textarea[placeholder="Schreibe eine Nachricht..."]');
    await expect(input).toBeVisible({ timeout: 10000 });
    await input.fill('Sag in einem Wort: Hallo');
    await input.press('Enter');

    // User-Nachricht rendert sofort
    await expect(
      chatPanel.getByText('Sag in einem Wort: Hallo')
    ).toBeVisible({ timeout: 10000 });

    // Assistant-Antwort von der echten DGX (SGLang, 27B) — Timeout großzügig
    const assistantBubble = chatPanel.locator('.liquid-glass.rounded-tl-sm');
    await expect(assistantBubble.first()).not.toHaveCount(0, { timeout: CHAT_TIMEOUT });
    const reply = (await assistantBubble.first().innerText()).trim();
    expect(reply.length).toBeGreaterThan(0);
    console.log(`[e2e] DGX-Antwort: "${reply.slice(0, 120)}"`);

    // Keine UI-Errors (API-/WS-Connection-Refused sind im E2E-Kontext irrelevant,
    // da same-origin — hier zählt echte UI-Fehlerfreiheit)
    const uiErrors = errors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('404') &&
        !e.includes('Failed to load resource') &&
        // WS-Handshake-Noise (by Design): Die PWA-UI versucht permanent eine
        // WS-Verbindung zu /ws/chat (Vorbau für Streaming) — der Server hat
        // aktuell bewusst keinen WS-Endpunkt, Chat läuft über REST /api/chat
        // (siehe ChatLayout-Kommentar). Der Browser loggt den fehlgeschlagenen
        // Handshake als Console-Error und der WSClient (websocket.ts) loggt
        // zusätzlich selbst '[WS] Error: Event' pro Reconnect-Versuch. Beides
        // ist erwartete UI-Architektur ohne WS-Backend, kein UI-Bug.
        !e.includes('WebSocket') &&
        !e.includes('[WS]') &&
        !e.includes('ERR_')
    );
    expect(uiErrors).toEqual([]);
  }, CHAT_TIMEOUT + 60000);

  test('Reset: /api/setup/reset → Setup-Page erscheint wieder', async ({ page }) => {
    // Vorher: Chat ist konfiguriert
    await page.goto('/#/chat', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('[data-testid="panel-chat"]')).toBeVisible({ timeout: 20000 });

    // Engine-Auswahl vergessen (API-Direkt + UI-Parity)
    const res = await page.request.post('/api/setup/reset');
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.configured).toBe(false);
    expect(fs.existsSync(E2E_ENGINE_JSON)).toBe(false);

    // UI-Reload → Setup-Page ist wieder sichtbar (First-Run-Flow testbar)
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('[data-testid="setup-page"]')).toBeVisible({ timeout: 15000 });
  });
});
