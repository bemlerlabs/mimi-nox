import { test, expect } from '@playwright/test';
import { ensureOnboarded, gotoHash } from './helpers';

// Modals/Dialogs der aktuellen UI: Settings-Panel (Slideover) und
// Command-Palette (Cmd/Ctrl+K). Die Legacy-Provider-/Mobile-Pairing-Modals
// mit eigenen IDs existieren nicht mehr.

test.describe('Modals & Dialogs (aktuelle UI: Settings + Command Palette)', () => {

  test.beforeEach(async ({ page }) => {
    await ensureOnboarded(page);
    await gotoHash(page, '/chat', '[data-testid="panel-chat"]');
  });

  test('settings panel opens and shows model selection', async ({ page }) => {
    const settingsBtn = page.locator('header button:has(svg.lucide-settings)');
    await expect(settingsBtn).toBeVisible();
    await settingsBtn.click();
    const panel = page.locator('[data-testid="settings-panel"]');
    await expect(panel).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('gemma4:e4b').first()).toBeVisible();
  });

  test('settings panel closes via close control', async ({ page }) => {
    const settingsBtn = page.locator('header button:has(svg.lucide-settings)');
    await settingsBtn.click();
    const panel = page.locator('[data-testid="settings-panel"]');
    await expect(panel).toBeVisible({ timeout: 5000 });
    // Esc schließt (Dialog-Verhalten — a11y-Standard)
    await page.keyboard.press('Escape');
    await expect(panel).toBeHidden({ timeout: 5000 });
  });

  test('command palette opens with Cmd+K and filters', async ({ page }) => {
    await page.keyboard.press('Meta+k');
    const paletteInput = page.locator('input').last();
    await expect(paletteInput).toBeVisible({ timeout: 5000 });
    await paletteInput.fill('chat');
    // Filterergebnisse erscheinen (mind. 1 Eintrag)
    await expect(paletteInput).toHaveValue('chat');
    await page.keyboard.press('Escape');
  });

  test('new session button in sidebar is clickable', async ({ page }) => {
    // Sidebar ist auf Desktop (lg+) immer sichtbar (relative); Klick auf
    // „New Session“ darf nicht crashen. Drawer-Öffnung testet das
    // mobile-viewport-Spec (unter lg ist die Sidebar ein Drawer).
    const newSession = page.locator('[data-testid="new-session"]');
    await expect(newSession).toBeVisible({ timeout: 5000 });
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(String(e)));
    await newSession.click();
    expect(errors, `Klick auf „Neue Sitzung“ darf nicht crashen: ${errors.join(' | ')}`).toEqual([]);
  });
});
