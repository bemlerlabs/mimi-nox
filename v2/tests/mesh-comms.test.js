import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { io as Client } from 'socket.io-client';
import { createServer } from 'node:http';
import { Server } from 'socket.io';
import express from 'express';

describe('Mesh Communication (Phase 4)', () => {
  let io, server, client1, client2;
  const port = 3001;

  beforeAll(async () => {
    const app = express();
    server = createServer(app);
    io = new Server(server);

    io.on('connection', (socket) => {
      socket.on('mesh:join', (data) => {
        socket.userName = data.user || 'Survivor';
        io.emit('mesh:presence', { user: socket.userName, status: 'online' });
      });
      socket.on('mesh:message', (msg) => {
        io.emit('mesh:message', {
          from: socket.userName || 'Anonymous',
          content: msg.content,
          timestamp: new Date().toISOString()
        });
      });
    });

    await new Promise(resolve => server.listen(port, resolve));
    client1 = new Client(`http://localhost:${port}`);
    client2 = new Client(`http://localhost:${port}`);
    
    await Promise.all([
      new Promise(r => client1.on('connect', r)),
      new Promise(r => client2.on('connect', r))
    ]);
  });

  afterAll(() => {
    if (client1) client1.disconnect();
    if (client2) client2.disconnect();
    if (io) io.close();
    if (server) server.close();
  });

  it('should broadcast presence when a user joins', () => {
    return new Promise((resolve) => {
      client2.on('mesh:presence', (data) => {
        if (data.user === 'Alice') {
          expect(data.status).toBe('online');
          resolve();
        }
      });
      client1.emit('mesh:join', { user: 'Alice' });
    });
  });

  it('should broadcast messages to all connected clients', () => {
    const testMsg = 'S.O.S. - Wasser benötigt!';
    return new Promise((resolve) => {
      client2.on('mesh:message', (msg) => {
        if (msg.content === testMsg) {
          expect(msg.from).toBe('Alice');
          expect(msg.content).toBe(testMsg);
          resolve();
        }
      });
      client1.emit('mesh:message', { content: testMsg });
    });
  });
});
