import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { createServer } from '../server/index.js';

describe('v2 CORS defaults', () => {
  let server;
  let port;

  beforeAll(async () => {
    ({ server } = createServer({ port: 0 }));
    await new Promise(resolve => server.once('listening', resolve));
    port = server.address().port;
  });

  afterAll(async () => {
    if (server) await new Promise(resolve => server.close(resolve));
  });

  it('[D] GIVEN foreign web origin WHEN preflight write request THEN CORS is not granted', async () => {
    const res = await fetch(`http://127.0.0.1:${port}/api/tasks`, {
      method: 'OPTIONS',
      headers: {
        Origin: 'https://evil.example.test',
        'Access-Control-Request-Method': 'POST',
      },
    });

    expect(res.headers.get('access-control-allow-origin')).toBeNull();
  });

  it('[D] GIVEN local dashboard origin WHEN preflight write request THEN CORS is granted', async () => {
    const res = await fetch(`http://127.0.0.1:${port}/api/tasks`, {
      method: 'OPTIONS',
      headers: {
        Origin: 'http://127.0.0.1:5173',
        'Access-Control-Request-Method': 'POST',
      },
    });

    expect(res.headers.get('access-control-allow-origin')).toBe('http://127.0.0.1:5173');
  });
});
