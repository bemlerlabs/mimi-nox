import { describe, it, expect, beforeEach } from 'vitest';
import { ToolEngine } from '../server/tools/engine.js';
import { PythonBridge } from '../server/bridge/python-bridge.js';

describe('Knowledge Search Tool (Phase 3)', () => {
  let engine;
  let bridge;

  beforeEach(() => {
    bridge = new PythonBridge();
    engine = new ToolEngine({ bridge });
  });

  it('should find medical information about burns', async () => {
    const result = await engine.execute('search_knowledge', { 
      query: 'Erste Hilfe bei Verbrennungen für Krisensituationen' 
    });
    
    expect(result).toContain('Gefundene Informationen');
  });

  it('should find engineering information about solar panels', async () => {
    const result = await engine.execute('search_knowledge', { 
      query: 'Troubleshooting: Solaranlage (Off-Grid) reparieren' 
    });
    
    expect(result).toContain('Gefundene Informationen');
  });

  it('should return a graceful message when no info is found', async () => {
    const result = await engine.execute('search_knowledge', { 
      query: 'Bitcoins und Kryptowährungen investieren' 
    });
    
    expect(result).toContain('Keine ausreichend relevanten Informationen');
  });
});
