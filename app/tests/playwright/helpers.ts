import { Page } from '@playwright/test';

/**
 * Helpers für die aktuelle React+Vite UI (Hash-Router: /, /onboarding, /chat).
 *
 * Die Legacy-UI (tab-basierte PWA mit #welcome-screen / #mobile-bottomnav)
 * existiert nicht mehr — die alten dismiss*-Overlays sind damit obsolet.
 *
 * Onboarding-Gate: localStorage 'mimi_nox_onboarded'='1' (vor dem App-Boot
 * setzen, sonst rendert die App direkt die Landingpage — Hash-Router, kein
 * imperatives Overlay mehr).
 */

export async function ensureOnboarded(page: Page) {
  await page.addInitScript(() => {
    // Deutsch deterministisch setzen — i18next-browser-languagedetector
    // persistiert die Locale im Key 'i18nextLng' (order: localStorage,
    // navigator). Ohne das wären Labels navigator-abhängig (Test-Lauf mit
    // en-US-Navigator rendert englische Labels).
    localStorage.setItem('i18nextLng', 'de');
    localStorage.setItem('mimi_nox_onboarded', '1');
  });
}

/** Navigiert zu einem Hash-Route (/chat → /#/chat) und wartet auf den Inhalt. */
export async function gotoHash(page: Page, route: string, selector: string) {
  // route ohne Leading-Slash übergeben: '/chat' → 'http://127.0.0.1:9199/#/chat'
  const hash = `#/${route.replace(/^\//, '')}`;
  await page.goto(hash, { waitUntil: 'load' });
  await page.waitForSelector(selector, { timeout: 15000 });
}
