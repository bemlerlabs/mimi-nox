import { test, expect } from '@playwright/test';
import { ensureOnboarded, gotoHash } from './helpers';

// Mobile Viewport: Die Legacy #mobile-bottomnav-Tabbar existiert nicht mehr.
// Aktuelle Mobile-Logik: Menü-Button im Chat-Header öffnet die Sidebar
// (fixed, Slide-In); Panels bleiben responsiv.

test.describe('Mobile Viewport (aktuelle UI: Sidebar-Drawer statt Bottom-Nav)', () => {

  test.use({ viewport: { width: 375, height: 667 } });

  test('landing has no horizontal overflow on mobile', async ({ page }) => {
    await ensureOnboarded(page);
    await page.goto('/', { waitUntil: 'load' });
    await page.waitForSelector('h1', { timeout: 10000 });
    await page.waitForTimeout(500);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 2,
    );
    expect(overflow).toBe(false);
  });

  test('chat header shows the mobile menu button', async ({ page }) => {
    await ensureOnboarded(page);
    await gotoHash(page, '/chat', '[data-testid="panel-chat"]');
    const menuBtn = page.locator('header button:has(svg.lucide-menu)');
    await expect(menuBtn).toBeVisible();
  });

  test('menu button opens the sidebar drawer', async ({ page }) => {
    await ensureOnboarded(page);
    await gotoHash(page, '/chat', '[data-testid="panel-chat"]');
    await page.locator('header button:has(svg.lucide-menu)').click();
    await expect(page.locator('[data-testid="sessions-view"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-testid="new-session"]')).toBeVisible();
  });

  test('chat workspace has no horizontal overflow on mobile', async ({ page }) => {
    await ensureOnboarded(page);
    await gotoHash(page, '/chat', '[data-testid="panel-chat"]');
    await page.waitForTimeout(500);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 2,
    );
    expect(overflow).toBe(false);
  });
});
