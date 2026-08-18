import { test, expect } from '@playwright/test';
import { ensureOnboarded, gotoHash } from './helpers';

// "Tabs" der aktuellen UI = Workspace-Layout-Presets (Focus/Dev/Swarm/Minimal),
// die die Panel-Komposition steuern (Chat/Agent/Explorer/Terminal/Files).
// Die Legacy-Sidebar-Tabs (#tab-skills o.ä.) existieren nicht mehr.

const PRESET_BUTTONS: Record<string, string> = {
  focus: '[data-testid="preset-focus"]',
  dev: '[data-testid="preset-dev"]',
  swarm: '[data-testid="preset-swarm"]',
  minimal: '[data-testid="preset-minimal"]',
};

test.describe('Workspace Layout Presets (aktuelle UI: Panels statt Tabs)', () => {

  test.beforeEach(async ({ page }) => {
    await ensureOnboarded(page);
    await gotoHash(page, '/chat', '[data-testid="panel-chat"]');
  });

  test('dev preset is default with terminal and files panels', async ({ page }) => {
    await expect(page.locator('[data-testid="layout-dev"]')).toBeVisible();
    await expect(page.locator('[data-testid="panel-terminal"]')).toBeVisible();
    await expect(page.locator('[data-testid="panel-files"]')).toBeVisible();
    await expect(page.locator('[data-testid="panel-explorer"]')).toBeVisible();
    await expect(page.locator('[data-testid="context-rail"]')).toBeVisible();
  });

  test('focus preset hides terminal/files and shows agent-free chat', async ({ page }) => {
    await page.locator(PRESET_BUTTONS.focus).click();
    await expect(page.locator('[data-testid="layout-focus"]')).toBeVisible();
    await expect(page.locator('[data-testid="panel-terminal"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="panel-files"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="panel-chat"]')).toBeVisible();
  });

  test('swarm preset shows the agent panel', async ({ page }) => {
    await page.locator(PRESET_BUTTONS.swarm).click();
    await expect(page.locator('[data-testid="layout-swarm"]')).toBeVisible();
    await expect(page.locator('[data-testid="panel-agent"]')).toBeVisible();
  });

  test('minimal preset hides explorer and context rail', async ({ page }) => {
    await page.locator(PRESET_BUTTONS.minimal).click();
    await expect(page.locator('[data-testid="layout-minimal"]')).toBeVisible();
    await expect(page.locator('[data-testid="panel-explorer"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="context-rail"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="panel-chat"]')).toBeVisible();
  });

  test('cycling through all presets returns to a working layout', async ({ page }) => {
    for (const sel of Object.values(PRESET_BUTTONS)) {
      await page.locator(sel).click();
      await expect(page.locator('[data-testid="panel-chat"]')).toBeVisible();
    }
    await page.locator(PRESET_BUTTONS.dev).click();
    await expect(page.locator('[data-testid="layout-dev"]')).toBeVisible();
  });
});
