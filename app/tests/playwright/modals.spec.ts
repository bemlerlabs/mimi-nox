import { test, expect } from '@playwright/test';
import { dismissAllOverlays } from './helpers';

test.describe('Modals & Dialogs', () => {

  test('provider modal opens and closes', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await page.locator('#btn-provider-settings').click();
    await expect(page.locator('#provider-modal')).toBeVisible();
    await expect(page.locator('#provider-modal-title')).toContainText(/Provider/i);
    await page.locator('#provider-close-btn').click();
    await expect(page.locator('#provider-modal')).not.toBeVisible();
  });

  test('provider modal shows local ollama as default', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await page.locator('#btn-provider-settings').click();
    await expect(page.locator('input[name="provider"][value="local_ollama"]')).toBeChecked();
  });

  test('mobile pairing modal opens and closes', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await page.locator('#btn-mobile-pairing').click();
    await expect(page.locator('#mobile-qr-overlay')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#mobile-qr-title')).toContainText(/Mobile/i);
    // Wait for close button to be visible (it may be hidden during QR loading)
    await page.locator('#mobile-qr-close-btn').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('#mobile-qr-close-btn').click({ force: true });
    await expect(page.locator('#mobile-qr-overlay')).not.toBeVisible();
  });

  test('new chat button is clickable', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await expect(page.locator('#btn-new-chat')).toBeVisible();
    await page.locator('#btn-new-chat').click();
    await expect(page.locator('#view-chat')).toBeVisible();
  });

  test('export chat button is visible', async ({ page }) => {
    await page.goto('/');
    await dismissAllOverlays(page);
    await expect(page.locator('#btn-export-chat')).toBeVisible();
  });
});
