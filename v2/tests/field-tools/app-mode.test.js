/**
 * ◑ MiMiNox — Test: App-Modus-Wechsler
 * tests/field-tools/app-mode.test.js
 *
 * TDD: Given / When / Then
 * Feature: User wechselt zwischen Krisen- und Alltags-Modus
 */
import { describe, it, expect } from 'vitest';
import {
  MODES,
  createModeStore,
  setMode,
  getMode,
  getModeConfig,
  getModeLabel,
  getModeEmoji,
  showsFieldTools,
  getOnboardingPrompts,
} from '../../server/field-tools/app-mode.js';

describe('App-Modus-Wechsler', () => {

  // ── MODES Konstante ────────────────────────────────────────────────

  it('[D] GIVEN MODES THEN contains crisis and daily', () => {
    expect(MODES).toContain('crisis');
    expect(MODES).toContain('daily');
  });

  // ── createModeStore ────────────────────────────────────────────────

  it('[D] GIVEN new store WHEN created THEN default mode is crisis', () => {
    const store = createModeStore();
    expect(store.mode).toBe('crisis');
  });

  it('[D] GIVEN createModeStore with daily THEN mode is daily', () => {
    const store = createModeStore('daily');
    expect(store.mode).toBe('daily');
  });

  it('[D] GIVEN createModeStore with invalid THEN throws', () => {
    expect(() => createModeStore('xyz')).toThrow();
  });

  // ── setMode ────────────────────────────────────────────────────────

  it('[D] GIVEN crisis store WHEN setMode daily THEN returns new store with daily', () => {
    const store = createModeStore('crisis');
    const next = setMode(store, 'daily');
    expect(next.mode).toBe('daily');
    expect(store.mode).toBe('crisis'); // immutable
  });

  it('[D] GIVEN daily store WHEN setMode crisis THEN returns crisis', () => {
    const store = createModeStore('daily');
    const next = setMode(store, 'crisis');
    expect(next.mode).toBe('crisis');
  });

  it('[D] GIVEN store WHEN setMode with invalid code THEN throws', () => {
    const store = createModeStore();
    expect(() => setMode(store, 'work')).toThrow();
    expect(() => setMode(store, '')).toThrow();
    expect(() => setMode(store, null)).toThrow();
  });

  it('[D] GIVEN store WHEN setMode THEN original store is unchanged (immutable)', () => {
    const store = createModeStore('crisis');
    setMode(store, 'daily');
    expect(store.mode).toBe('crisis');
  });

  // ── getMode ────────────────────────────────────────────────────────

  it('[D] GIVEN crisis store WHEN getMode THEN returns crisis', () => {
    expect(getMode(createModeStore('crisis'))).toBe('crisis');
  });

  it('[D] GIVEN daily store WHEN getMode THEN returns daily', () => {
    expect(getMode(createModeStore('daily'))).toBe('daily');
  });

  // ── getModeConfig ──────────────────────────────────────────────────

  it('[D] GIVEN mode crisis WHEN getModeConfig THEN has all required fields', () => {
    const cfg = getModeConfig('crisis');
    expect(cfg.label).toBeDefined();
    expect(cfg.emoji).toBeDefined();
    expect(cfg.theme).toBe('mode-crisis');
    expect(cfg.showFieldTools).toBe(true);
    expect(cfg.systemPromptKey).toBe('crisis');
    expect(cfg.accentColor).toBeDefined();
  });

  it('[D] GIVEN mode daily WHEN getModeConfig THEN showFieldTools is false', () => {
    const cfg = getModeConfig('daily');
    expect(cfg.showFieldTools).toBe(false);
    expect(cfg.theme).toBe('mode-daily');
    expect(cfg.systemPromptKey).toBe('daily');
  });

  it('[D] GIVEN invalid mode WHEN getModeConfig THEN throws', () => {
    expect(() => getModeConfig('invalid')).toThrow();
  });

  // ── Convenience-Helfer ─────────────────────────────────────────────

  it('[D] GIVEN mode crisis WHEN getModeLabel THEN returns non-empty string', () => {
    expect(getModeLabel('crisis').length).toBeGreaterThan(0);
  });

  it('[D] GIVEN mode daily WHEN getModeEmoji THEN returns emoji', () => {
    const emoji = getModeEmoji('daily');
    expect(emoji.length).toBeGreaterThan(0);
  });

  it('[D] GIVEN mode crisis WHEN showsFieldTools THEN true', () => {
    expect(showsFieldTools('crisis')).toBe(true);
  });

  it('[D] GIVEN mode daily WHEN showsFieldTools THEN false', () => {
    expect(showsFieldTools('daily')).toBe(false);
  });

  // ── Onboarding-Prompts ─────────────────────────────────────────────

  it('[D] GIVEN mode crisis WHEN getOnboardingPrompts THEN returns array of strings', () => {
    const prompts = getOnboardingPrompts('crisis');
    expect(Array.isArray(prompts)).toBe(true);
    expect(prompts.length).toBeGreaterThan(0);
    expect(typeof prompts[0]).toBe('string');
  });

  it('[D] GIVEN mode daily WHEN getOnboardingPrompts THEN prompts differ from crisis', () => {
    const crisis = getOnboardingPrompts('crisis');
    const daily = getOnboardingPrompts('daily');
    expect(crisis[0]).not.toBe(daily[0]);
  });

  it('[D] GIVEN mode daily WHEN getOnboardingPrompts THEN no Notruf/SOS in prompts', () => {
    const prompts = getOnboardingPrompts('daily');
    const text = prompts.join(' ').toLowerCase();
    expect(text).not.toContain('notruf');
    expect(text).not.toContain('sos');
  });
});
