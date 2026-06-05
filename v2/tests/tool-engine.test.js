/**
 * ◑ MiMiNox v2 — Test: Tool Engine
 * Task 1.7: Tool-Engine (Node.js Port)
 * TDD: Tests FIRST, then implementation.
 */
import { describe, it, expect } from 'vitest';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { ToolEngine, ShellConfirmationRequired, FileNotAllowedError } from '../server/tools/engine.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

describe('Task 1.7: Tool Engine', () => {
  let engine;

  // ── get_datetime ──────────────────────────────────────────────────

  // GIVEN die Tool-Engine
  // WHEN executeTool("get_datetime") aufgerufen wird
  // THEN enthält das Ergebnis das aktuelle Jahr
  it('[D] GIVEN engine WHEN get_datetime THEN contains current year', async () => {
    engine = new ToolEngine();
    const result = await engine.execute('get_datetime', {});
    expect(result).toContain('2026');
  });

  // ── run_shell — Confirmation Gate ─────────────────────────────────

  // GIVEN die Tool-Engine
  // WHEN run_shell aufgerufen wird
  // THEN wird ShellConfirmationRequired geworfen
  it('[D] GIVEN engine WHEN run_shell THEN throws ShellConfirmationRequired', async () => {
    engine = new ToolEngine();
    await expect(
      engine.execute('run_shell', { command: 'ls -la' })
    ).rejects.toThrow(ShellConfirmationRequired);
  });

  // ── read_file — Whitelist ─────────────────────────────────────────

  // GIVEN die Tool-Engine mit Whitelist
  // WHEN read_file mit /etc/passwd aufgerufen wird
  // THEN wird FileNotAllowedError geworfen
  it('[D] GIVEN engine WHEN read_file /etc/passwd THEN throws FileNotAllowedError', async () => {
    engine = new ToolEngine({ whitelist: ['/home'] });
    await expect(
      engine.execute('read_file', { path: '/etc/passwd' })
    ).rejects.toThrow(FileNotAllowedError);
  });

  // ── read_file — erlaubter Pfad ────────────────────────────────────

  it('[D] GIVEN engine WHEN read_file on allowed path THEN returns content', async () => {
    engine = new ToolEngine({ whitelist: [ROOT] });
    const result = await engine.execute('read_file', { path: join(ROOT, 'package.json') });
    expect(result).toContain('miminox-v2');
  });

  // ── list_directory ────────────────────────────────────────────────

  it('[D] GIVEN engine WHEN list_directory on allowed path THEN returns entries', async () => {
    engine = new ToolEngine({ whitelist: [ROOT] });
    const result = await engine.execute('list_directory', { path: ROOT });
    expect(result).toContain('package.json');
  });

  // ── Tool-Schema Kompatibilität ────────────────────────────────────

  // GIVEN getToolSchemas aufgerufen
  // THEN sind alle Schemas Ollama-kompatibel
  it('[D] GIVEN engine WHEN getSchemas THEN all have function structure', () => {
    engine = new ToolEngine();
    const schemas = engine.getSchemas();
    expect(Array.isArray(schemas)).toBe(true);
    expect(schemas.length).toBeGreaterThan(0);
    for (const s of schemas) {
      expect(s.type).toBe('function');
      expect(s.function.name).toBeDefined();
      expect(s.function.description).toBeDefined();
      expect(s.function.parameters).toBeDefined();
    }
  });

  // GIVEN getSchemas
  // THEN jeder Schema-Name existiert als ausführbares Tool
  it('[D] GIVEN schemas WHEN checking names THEN all are executable', () => {
    engine = new ToolEngine();
    const schemas = engine.getSchemas();
    const names = schemas.map(s => s.function.name);
    for (const name of names) {
      expect(engine.hasTool(name)).toBe(true);
    }
  });
});
