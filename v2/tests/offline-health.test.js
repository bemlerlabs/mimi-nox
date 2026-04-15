import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createServer } from '../server/index.js';

describe('Offline-Health-Check (T-0.1)', () => {
  let server;
  let baseUrl;

  beforeEach(async () => {
    const result = createServer({ port: 0 }); // Random port
    server = result.server;
    const { port } = server.address();
    baseUrl = `http://localhost:${port}/api`;
  });

  afterEach(async () => {
    await server.close();
  });

  it('should return a health status with airGapped and ollamaReady fields', async () => {
    const res = await fetch(`${baseUrl}/health`);
    const data = await res.json();

    expect(data).toHaveProperty('status', 'ok');
    expect(data).toHaveProperty('airGapped');
    expect(typeof data.airGapped).toBe('boolean');
    expect(data).toHaveProperty('ollamaReady');
    expect(typeof data.ollamaReady).toBe('boolean');
    expect(data).toHaveProperty('version');
  });
});
