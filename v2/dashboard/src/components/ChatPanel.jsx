/**
 * ◑ MiMiNox v2 — Krisen-Chat Panel
 * Nachrichten zwischen User und Krisen-Agenten
 */
import { useRef, useEffect } from 'react';

function formatTime(ts) {
  if (!ts) return '';
  try {
    return new Date(ts).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

function getAvatar(from) {
  if (from === 'system') return '◑';
  if (from === 'user') return '→';
  if (from?.includes('medic')) return '🚑';
  if (from?.includes('engineer')) return '🛠️';
  if (from?.includes('navigator')) return '🗺️';
  if (from?.includes('sensor')) return '⚡';
  return '🤖';
}

export function ChatPanel({ messages = [] }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  return (
    <div className="chat-panel" id="chat-panel">
      <div className="chat-title">Krisen-Chat</div>
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div className="chat-msg" key={msg.id || `${msg.timestamp}-${msg.from}-${i}`}>
            <div className="chat-avatar">
              {getAvatar(msg.from)}
            </div>
            <div className="chat-body">
              <div className="chat-sender">
                {msg.from === 'user' ? 'Du' : (msg.from || 'system')}
              </div>
              <div className="chat-text">{msg.content}</div>
            </div>
            <div className="chat-time">{formatTime(msg.timestamp)}</div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
