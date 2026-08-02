import { Page } from '@playwright/test';

export async function dismissLanguagePicker(page: Page) {
  const overlay = page.locator('#lang-overlay');
  if (await overlay.isVisible({ timeout: 2000 }).catch(() => false)) {
    await page.locator('.lang-btn[data-lang="de"]').click();
    await overlay.waitFor({ state: 'hidden', timeout: 3000 });
  }
}

export async function dismissOnboarding(page: Page) {
  const ob = page.locator('#onboarding-overlay');
  if (await ob.isVisible({ timeout: 2000 }).catch(() => false)) {
    // Select a category first to enable the start button
    await page.locator('.ob-cat[data-cat="allround"]').click();
    await page.locator('#ob-start-btn').click();
    await ob.waitFor({ state: 'hidden', timeout: 3000 });
  }
}

export async function dismissAllOverlays(page: Page) {
  await dismissLanguagePicker(page);
  await dismissOnboarding(page);
}
