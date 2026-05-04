/**
 * ◑ MiMiNox — Chat Message Component
 * Renders user bubbles (brass) and MiMiNox responses (night-blue cards)
 * with thinking visualization and medical disclaimers.
 */
import { useState } from 'react';
import { renderMarkdown } from './Markdown';

// Medical keywords that trigger the disclaimer (DARPA Tompkins Auflage 1)
const MEDICAL_KEYWORDS = [
  'sofortmaßnahmen', 'notruf', 'drk', 'bbk', 'erste hilfe',
  'verbrennung', 'herzstillstand', 'hlw', 'vergiftung', 'blutung',
  'verletzt', 'bewusstlos', 'reanimation', 'wunde', 'kühlen',
  'medikament', 'allergi', 'schmerz', 'bruch', 'notarzt',
];

function isMedicalContent(text) {
  const lower = (text || '').toLowerCase();
  return MEDICAL_KEYWORDS.some(kw => lower.includes(kw));
}

function isMemoryConfirmation(text) {
  const lower = (text || '').toLowerCase();
  return lower.includes('gespeichert') || lower.includes('vergesse das nie')
    || lower.includes('merke mir') || lower.includes('notiert');
}

function extractThinking(text) {
  // Check for thinking markers in content
  const thinkMatch = text?.match(/👁\s*So denke ich[.…]*\n([\s\S]*?)(?:\n---|\n\n)/);
  if (thinkMatch) {
    return {
      thinking: thinkMatch[1].trim(),
      content: text.replace(thinkMatch[0], '').trim(),
    };
  }
  return { thinking: null, content: text };
}

export function ChatMessage({ msg }) {
  const [showThinking, setShowThinking] = useState(false);

  if (!msg) return null;

  // System messages
  if (msg.from === 'system' || msg.type === 'system') {
    return (
      <div className="msg-system">
        <span>{msg.content}</span>
      </div>
    );
  }

  // User messages — brass bubble, right-aligned
  if (msg.from === 'user') {
    return (
      <div className="msg-user">
        <div className="msg-bubble">
          {msg.photoUrl && (
            <img src={msg.photoUrl} alt="Foto" className="msg-photo" />
          )}
          {msg.content}
        </div>
      </div>
    );
  }

  // MiMiNox responses — night-blue card, left-aligned
  const { thinking, content } = extractThinking(msg.content);
  const isMedical = isMedicalContent(content);
  const isMemory = isMemoryConfirmation(content);

  return (
    <div className="msg-nox">
      <div className="msg-card">
        {/* Thinking visualization (VERSTEHEN) */}
        {thinking && (
          <>
            <button
              className="thinking-toggle"
              onClick={() => setShowThinking(!showThinking)}
            >
              <span className={`thinking-chevron ${showThinking ? 'open' : ''}`}>▶</span>
              👁 So denke ich…
            </button>
            {showThinking && (
              <div className="thinking-content">{thinking}</div>
            )}
          </>
        )}

        {/* Main content — rendered markdown */}
        <div className={isMemory ? 'msg-memory' : ''}>
          {renderMarkdown(content)}
        </div>

        {/* Source badge */}
        {msg.source && (
          <span className="msg-source">Quelle: {msg.source}</span>
        )}

        {/* Medical disclaimer (DARPA Tompkins Auflage 1) */}
        {isMedical && (
          <div className="msg-disclaimer">
            <span>⚕️</span>
            <span>Kein Ersatz für ärztliche Hilfe. Im Notfall: 112</span>
          </div>
        )}
      </div>
    </div>
  );
}
