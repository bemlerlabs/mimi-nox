import { test, expect } from '@playwright/test';
import { dismissAllOverlays } from './helpers';

test.describe('App Boot & Welcome', () => {

  test('page loads without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/');
    await dismissAllOverlays(page);
    await page.waitForLoadState('networkidle');
    expect(errors.filter(e => !e.includes('favicon') && !e.includes('404') && !e.includes('501'))).toEqual([]);
  });

  test('welcome screen is visible', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await expect(page.locator('#welcome-screen')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.welcome-heading')).toContainText(/helfen|help/i);
  });

  test('page title is set', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await expect(page).toHaveTitle(/MiMi Nox/);
  });

  test('chat input is present and editable', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    const input = page.locator('#chat-input');
    await expect(input).toBeVisible();
    await input.fill('Hello MiMi');
    await expect(input).toHaveValue('Hello MiMi');
  });

  test('send button is visible', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await expect(page.locator('#send-btn')).toBeVisible();
  });

  test('skill chips are rendered', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    const chips = page.locator('.skill-chip');
    const count = await chips.count();
    expect(count).toBeGreaterThanOrEqual(5);
  });
});
