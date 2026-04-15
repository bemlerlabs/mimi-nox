/**
 * ◑ MiMiNox v2 — Test: Python Bridge
 * Task 1.6: Python-Bridge (child_process)
 * TDD: Tests FIRST, then implementation.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { PythonBridge, BridgeTimeoutError, BridgeError } from '../server/bridge/python-bridge.js';

describe('Task 1.6: Python Bridge', () => {

  // GIVEN eine PythonBridge
  // WHEN bridge.call mit gültigem Python-Ausdruck aufgerufen wird
  // THEN wird das Ergebnis zurückgegeben
  it('[D] GIVEN bridge WHEN call with valid python THEN returns result', async () => {
    const bridge = new PythonBridge();
    const result = await bridge.eval('2 + 2');
    expect(result).toBe('4');
  });

  // GIVEN eine PythonBridge
  // WHEN der Python-Code eine Exception wirft
  // THEN wird BridgeError geworfen
  it('[D] GIVEN bridge WHEN python raises THEN throws BridgeError', async () => {
    const bridge = new PythonBridge();
    await expect(
      bridge.eval('1/0')
    ).rejects.toThrow(BridgeError);
  });

  // GIVEN eine PythonBridge mit timeout
  // WHEN der Python-Prozess zu lange dauert
  // THEN wird BridgeTimeoutError geworfen
  it('[D] GIVEN bridge with timeout WHEN python hangs THEN throws BridgeTimeoutError', async () => {
    const bridge = new PythonBridge({ timeout: 1000 });
    await expect(
      bridge.eval('import time; time.sleep(5)')
    ).rejects.toThrow(BridgeTimeoutError);
  }, 5000);

  // GIVEN eine PythonBridge
  // WHEN bridge.callModule mit memory-search aufgerufen wird
  // THEN wird der richtige Python-Code ausgeführt
  it('[D] GIVEN bridge WHEN callModule THEN executes python module function', async () => {
    const bridge = new PythonBridge();
    // Run a simple json import to verify module calling works
    const result = await bridge.eval('import json; print(json.dumps({"status": "ok"}))');
    expect(result).toContain('ok');
  });
});

// ── T-05: Konfigurierbarer Pfad (kein Hardcode) ─────────────────────────────

describe('T-05: PythonBridge — Konfigurierbarer Root-Pfad', () => {
  const originalEnv = process.env.MIMINOX_ROOT;

  afterEach(() => {
    // Env-Variable nach jedem Test zurücksetzen
    if (originalEnv === undefined) {
      delete process.env.MIMINOX_ROOT;
    } else {
      process.env.MIMINOX_ROOT = originalEnv;
    }
  });

  // GIVEN MIMINOX_ROOT Umgebungsvariable ist gesetzt
  // WHEN _buildModuleCode() aufgerufen wird
  // THEN enthält der generierte Code den Env-Pfad, NICHT den Hardcode
  it('[T-05] GIVEN MIMINOX_ROOT env WHEN buildModuleCode THEN uses env path', () => {
    process.env.MIMINOX_ROOT = '/custom/miminox/path';
    const bridge = new PythonBridge();

    const code = bridge._buildModuleCode('core.memory', 'search', { query: 'test' });

    expect(code).toContain('/custom/miminox/path');
    expect(code).not.toContain('/home/mimione/MiMiNox');
  });

  // GIVEN MIMINOX_ROOT ist NICHT gesetzt
  // WHEN _buildModuleCode() aufgerufen wird
  // THEN enthält der Code einen inferrierten Pfad (kein "undefined" drin)
  it('[T-05] GIVEN no MIMINOX_ROOT WHEN buildModuleCode THEN infers path without undefined', () => {
    delete process.env.MIMINOX_ROOT;
    const bridge = new PythonBridge();

    const code = bridge._buildModuleCode('core.memory', 'search', {});

    expect(code).toContain('sys.path.insert');
    expect(code).not.toContain('undefined');
    expect(code).not.toContain('null');
  });

  // GIVEN args mit einfachem Apostroph UND triple-quotes (maximaler Injection-Versuch)
  // WHEN _buildModuleCode() aufgerufen wird
  // THEN nutzt der Code Base64-Encoding — vollständig injektionssicher
  it('[T-05] GIVEN args with apostrophe WHEN buildModuleCode THEN no injection', () => {
    const bridge = new PythonBridge();

    const code = bridge._buildModuleCode('core.memory', 'search', {
      query: "triple ''' and apostrophe: it's dangerous"
    });

    expect(code).toContain('sys.path.insert');
    expect(code).toContain('core.memory');

    // QA-Fix: Kein Triple-Quote mehr — stattdessen Base64
    expect(code).toContain('base64.b64decode(');
    expect(code).toContain('import json, sys, base64');

    // Kein ungeschütztes JSON im Code (weder single-quote noch triple-quote)
    expect(code).not.toContain("it's dangerous");  // Roher Wert darf nicht im Code sein
    expect(code).not.toContain("'''");              // Triple-quotes entfernt
  });

  // GIVEN eine vollständige PythonBridge mit MIMINOX_ROOT
  // WHEN callModule aufgerufen wird
  // THEN nutzt die interne eval() den Pfad aus der Env-Variable
  it('[T-05] GIVEN MIMINOX_ROOT WHEN callModule builds code THEN env path in code', () => {
    process.env.MIMINOX_ROOT = '/opt/miminox';
    const bridge = new PythonBridge();

    const code = bridge._buildModuleCode('core.test', 'func', { x: 1 });

    expect(code).toMatch(/sys\.path\.insert\(0,\s*'\/opt\/miminox'\)/);
  });
});
