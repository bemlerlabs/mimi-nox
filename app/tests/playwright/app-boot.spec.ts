import { test, expect } from '@playwright/test';
import { ensureOnboarded, gotoHash } from './helpers';

test.describe('App Boot — Landing / Onboarding / Chat (aktuelle React+Vite-UI)', () => {

  test('landing loads without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await ensureOnboarded(page);
    await page.goto('/', { waitUntil: 'load' });
    await page.waitForSelector('h1', { timeout: 10000 });
    await page.waitForLoadState('networkidle');
    // Kein lokales Backend im Test → WS-/Fetch-Errors gegen localhost:8765 sind
    // erwartbar (offline-first-App ohne Backend). UI-Errors wären der Rest.
    const uiErrors = errors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('404') &&
        !e.includes('501') &&
        !e.includes('8765') &&
        !e.includes('localhost') &&
        !e.includes('WebSocket') &&
        !e.includes('[WS]') &&
        !e.includes('ERR_FAILED') &&
        !e.includes('ERR_CONNECTION_REFUSED'),
    );
    expect(uiErrors).toEqual([]);
  });

  test('landing hero and section navigation render', async ({ page }) => {
    await ensureOnboarded(page);
    await page.goto('/', { waitUntil: 'load' });
    await expect(page.locator('h1').first()).toBeVisible({ timeout: 10000 });
    // Hero-Section + Section-Headlines (Features/Architecture/Skills/CTA)
    await expect(page.locator('h2').first()).toBeVisible();
    const h2Count = await page.locator('h2').count();
    expect(h2Count).toBeGreaterThanOrEqual(4);
  });

  test('onboarding route renders the wizard', async ({ page }) => {
    await ensureOnboarded(page);
    await gotoHash(page, '/onboarding', 'h2');
    await expect(page.locator('h2').first()).toContainText(/Ollama/i, { timeout: 10000 });
    // Step-Buttons (Ollama prüfen) sichtbar
    await expect(page.getByRole('button', { name: /Ollama/i }).first()).toBeVisible();
  });

  test('chat route renders the workspace', async ({ page }) => {
    await ensureOnboarded(page);
    await gotoHash(page, '/chat', '[data-testid="panel-chat"]');
    await expect(page.locator('[data-testid="layout-dev"]')).toBeVisible();
    await expect(page.locator('[data-testid="panel-chat"]')).toBeVisible();
    await expect(page.locator('[data-testid="context-rail"]')).toBeVisible();
  });

  test('chat input is present and editable', async ({ page }) => {
    await ensureOnboarded(page);
    await gotoHash(page, '/chat', 'textarea');
    const input = page.locator('textarea[placeholder="Schreibe eine Nachricht..."]');
    await expect(input).toBeVisible();
    await input.fill('Hello MiMi');
    await expect(input).toHaveValue('Hello MiMi');
  });

  test('page title is set', async ({ page }) => {
    await ensureOnboarded(page);
    await page.goto('/', { waitUntil: 'load' });
    await expect(page).toHaveTitle(/MiMi Nox/);
  });
});
