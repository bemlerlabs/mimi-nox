/**
 * ◑ MiMiNox v2 — ThinkingStreamParser
 * server/llm/thinking-parser.js
 *
 * Zustandsautomat für Gemma 4 <|think|> Tag-Parsing.
 * Port von Python core/chat.py ThinkingStreamParser (L69-158).
 *
 * Design: Identische Logik wie Python-Original. Puffert partielle Tags,
 * trennt Thinking-Content vom Answer-Text, ruft Callbacks auf.
 */

// Parser states (same as Python)
const OUTSIDE = 'OUTSIDE';
const MAYBE_OPEN = 'MAYBE_OPEN';
const INSIDE = 'INSIDE';
const MAYBE_CLOSE = 'MAYBE_CLOSE';

const OPEN_TAG = '<|think|>';
const CLOSE_TAG = '<|/think|>';

export class ThinkingStreamParser {
  /**
   * @param {Object} opts
   * @param {(text: string) => void} [opts.onThinking] - Callback for thinking chunks
   * @param {(text: string) => void} [opts.onAnswer]   - Callback for answer chunks
   */
  constructor(opts = {}) {
    this._onThinking = opts.onThinking || null;
    this._onAnswer = opts.onAnswer || null;

    this._state = OUTSIDE;
    this._buffer = '';          // Partial tag buffer
    this._answerParts = [];     // Collected answer text
    this._thinkingParts = [];   // Current thinking block
    this._allThoughts = [];     // All completed thinking blocks
  }

  /** Feed a chunk of text from the LLM stream. */
  feed(chunk) {
    for (const char of chunk) {
      this._processChar(char);
    }
  }

  /** @returns {string} All thinking content concatenated */
  get thinking() {
    // Current in-progress thinking + all completed
    const current = this._thinkingParts.join('');
    if (this._allThoughts.length === 0) return current;
    if (current) return [...this._allThoughts, current].join('\n');
    return this._allThoughts[this._allThoughts.length - 1] || '';
  }

  /** @returns {string} Answer text (everything outside think tags) */
  get answer() {
    return this._answerParts.join('');
  }

  /** @returns {string[]} All completed thinking blocks */
  get allThoughts() {
    return [...this._allThoughts];
  }

  // ── State machine ─────────────────────────────────────────────────────

  _processChar(char) {
    switch (this._state) {
      case OUTSIDE:
        this._handleOutside(char);
        break;
      case MAYBE_OPEN:
        this._handleMaybeOpen(char);
        break;
      case INSIDE:
        this._handleInside(char);
        break;
      case MAYBE_CLOSE:
        this._handleMaybeClose(char);
        break;
    }
  }

  _handleOutside(char) {
    if (char === '<') {
      this._buffer = '<';
      this._state = MAYBE_OPEN;
    } else {
      this._emitAnswer(char);
    }
  }

  _handleMaybeOpen(char) {
    this._buffer += char;

    if (OPEN_TAG.startsWith(this._buffer)) {
      if (this._buffer === OPEN_TAG) {
        // Full open tag matched
        this._buffer = '';
        this._state = INSIDE;
        this._thinkingParts = [];
      }
      // else: still accumulating, stay in MAYBE_OPEN
    } else {
      // Not a valid tag — flush buffer as answer text
      this._emitAnswer(this._buffer);
      this._buffer = '';
      this._state = OUTSIDE;
    }
  }

  _handleInside(char) {
    if (char === '<') {
      this._buffer = '<';
      this._state = MAYBE_CLOSE;
    } else {
      this._emitThinking(char);
    }
  }

  _handleMaybeClose(char) {
    this._buffer += char;

    if (CLOSE_TAG.startsWith(this._buffer)) {
      if (this._buffer === CLOSE_TAG) {
        // Full close tag matched — finalize thinking block
        const thought = this._thinkingParts.join('');
        this._allThoughts.push(thought);
        this._thinkingParts = [];
        this._buffer = '';
        this._state = OUTSIDE;
      }
      // else: still accumulating
    } else {
      // Not a valid close tag — emit buffer as thinking text
      this._emitThinking(this._buffer);
      this._buffer = '';
      this._state = INSIDE;
    }
  }

  // ── Emitters ──────────────────────────────────────────────────────────

  _emitAnswer(text) {
    this._answerParts.push(text);
    if (this._onAnswer) this._onAnswer(text);
  }

  _emitThinking(text) {
    this._thinkingParts.push(text);
    if (this._onThinking) this._onThinking(text);
  }
}
