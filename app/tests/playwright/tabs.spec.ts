import { test, expect } from '@playwright/test';
import { dismissAllOverlays } from './helpers';

test.describe('Tab Navigation', () => {

  async function verifyTab(page: any, tabId: string, viewId: string) {
    await page.locator(tabId).click();
    await expect(page.locator(tabId)).toHaveClass(/active/);
    await expect(page.locator(viewId)).toBeVisible();
  }

  test('chat tab is active by default', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await expect(page.locator('#tab-chat')).toHaveClass(/active/);
    await expect(page.locator('#view-chat')).toBeVisible();
  });

  test('switching to skills tab works', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await verifyTab(page, '#tab-skills', '#view-skills');
  });

  test('switching to history tab works', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await verifyTab(page, '#tab-history', '#view-history');
  });

  test('switching to tasks tab works', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await verifyTab(page, '#tab-tasks', '#view-tasks');
  });

  test('switching to memory tab works', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await verifyTab(page, '#tab-memory', '#view-memory');
  });

  test('switching to profile tab works', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await verifyTab(page, '#tab-profile', '#view-profile');
  });

  test('chat remains active after cycling through all tabs', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    const tabs = ['#tab-skills', '#tab-history', '#tab-tasks', '#tab-memory', '#tab-profile'];
    for (const tab of tabs) {
      await page.locator(tab).click();
    }
    await page.locator('#tab-chat').click();
    await expect(page.locator('#tab-chat')).toHaveClass(/active/);
    await expect(page.locator('#view-chat')).toBeVisible();
  });
});
