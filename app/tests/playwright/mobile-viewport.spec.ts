import { test, expect } from '@playwright/test';
import { dismissAllOverlays } from './helpers';

test.describe('Mobile Viewport', () => {

  test.use({ viewport: { width: 375, height: 667 } });

  test('mobile bottom navigation is visible', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await expect(page.locator('#mobile-bottomnav')).toBeVisible();
  });

  test('mobile nav has 6 tab buttons', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    const tabs = page.locator('#mobile-bottomnav .mbn-tab');
    await expect(tabs).toHaveCount(6);
  });

  test('chat tab is active in mobile nav by default', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await expect(page.locator('#mobile-bottomnav .mbn-tab[data-tab="chat"]')).toHaveClass(/active/);
  });

  test('switching tabs via mobile bottom nav works', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await page.locator('#mobile-bottomnav .mbn-tab[data-tab="skills"]').click();
    await expect(page.locator('#view-skills')).toBeVisible();
  });
});
