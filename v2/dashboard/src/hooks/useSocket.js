/**
 * ◑ MiMiNox v2 — Socket.io Hook
 * Echtzeit-Updates vom Backend.
 */
import { useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';

const SOCKET_URL = 'http://localhost:3001';

export function useSocket(onEvent) {
  const socketRef = useRef(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    try {
      const socket = io(SOCKET_URL, {
        transports: ['websocket'],
        reconnectionDelay: 2000,
        timeout: 3000,
      });

      socketRef.current = socket;

      socket.on('connect', () => {
        onEventRef.current?.({ type: 'connected' });
      });

      // Store events
      socket.on('agent_updated', (data) =>
        onEventRef.current?.({ type: 'agent_updated', ...data }));
      socket.on('chat_message', (data) =>
        onEventRef.current?.({ type: 'chat_message', ...data }));
      socket.on('ticket_moved', (data) =>
        onEventRef.current?.({ type: 'ticket_moved', ...data }));
      socket.on('agent_level_up', (data) =>
        onEventRef.current?.({ type: 'agent_level_up', ...data }));

      // Transparency events
      socket.on('topology_pulse', (data) =>
        onEventRef.current?.({ type: 'topology_pulse', ...data }));
      socket.on('event', (data) =>
        onEventRef.current?.({ type: 'event', ...data }));

      socket.on('disconnect', () => {
        onEventRef.current?.({ type: 'disconnected' });
      });

      return () => { socket.disconnect(); };
    } catch {
      // Backend not running — ignore
    }
  }, []);

  const emit = useCallback((event, data) => {
    socketRef.current?.emit(event, data);
  }, []);

  return { emit };
}
