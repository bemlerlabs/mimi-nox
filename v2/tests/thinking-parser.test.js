/**
 * ◑ MiMiNox v2 — Test: ThinkingStreamParser
 * Task 1.3: Port von Python ThinkingStreamParser
 * TDD: Tests FIRST, then implementation.
 */
import { describe, it, expect } from 'vitest';
import { ThinkingStreamParser } from '../server/llm/thinking-parser.js';

describe('Task 1.3: ThinkingStreamParser', () => {

  // GIVEN ein ThinkingStreamParser
  // WHEN Chunks mit <|think|> Tags gefüttert werden
  // THEN werden Thinking und Answer korrekt getrennt
  it('[D] GIVEN stream with thinking WHEN parsed THEN separates thought from answer', () => {
    const parser = new ThinkingStreamParser();
    const chunks = ['Hallo ', '<|', 'think', '|>', 'Ich denke...', '<|/', 'think|>', ' Welt'];
    for (const chunk of chunks) {
      parser.feed(chunk);
    }
    expect(parser.thinking).toBe('Ich denke...');
    expect(parser.answer).toBe('Hallo  Welt');
  });

  // GIVEN ein ThinkingStreamParser
  // WHEN Chunks OHNE Thinking-Tags gefüttert werden
  // THEN ist thinking leer und answer enthält alles
  it('[D] GIVEN stream without thinking WHEN parsed THEN returns full as answer', () => {
    const parser = new ThinkingStreamParser();
    parser.feed('Hallo');
    parser.feed(' Welt');
    expect(parser.thinking).toBe('');
    expect(parser.answer).toBe('Hallo Welt');
  });

  // GIVEN ein ThinkingStreamParser
  // WHEN ein Stream mit 2 Think-Blöcken verarbeitet wird
  // THEN enthält allThoughts beide Gedanken
  it('[D] GIVEN multiple thinking blocks WHEN parsed THEN all collected', () => {
    const parser = new ThinkingStreamParser();
    parser.feed('Start <|think|>Gedanke 1<|/think|> Mitte <|think|>Gedanke 2<|/think|> Ende');
    expect(parser.allThoughts).toHaveLength(2);
    expect(parser.allThoughts[0]).toBe('Gedanke 1');
    expect(parser.allThoughts[1]).toBe('Gedanke 2');
    expect(parser.answer).toBe('Start  Mitte  Ende');
  });

  // GIVEN ein ThinkingStreamParser mit onThinking Callback
  // WHEN <|think|>...<|/think|> gestreamt wird
  // THEN wird der Callback aufgerufen
  it('[D] GIVEN thinking callback WHEN thinking tags present THEN callback called', () => {
    const thinkingChunks = [];
    const parser = new ThinkingStreamParser({
      onThinking: (text) => thinkingChunks.push(text),
    });
    parser.feed('<|think|>Ich überlege...<|/think|>Antwort');
    expect(thinkingChunks.length).toBeGreaterThan(0);
    expect(thinkingChunks.join('')).toBe('Ich überlege...');
  });

  // GIVEN ein ThinkingStreamParser
  // WHEN das Tag in 1-Byte-Chunks geliefert wird
  // THEN wird es korrekt erkannt
  it('[D] GIVEN partial thinking tag WHEN streaming chunk by chunk THEN buffers correctly', () => {
    const parser = new ThinkingStreamParser();
    const tag = '<|think|>Gedanke<|/think|>';
    for (const char of tag) {
      parser.feed(char);
    }
    parser.feed('Antwort');
    expect(parser.thinking).toBe('Gedanke');
    expect(parser.answer).toBe('Antwort');
  });

  // GIVEN ein leerer Think-Block
  // WHEN geparst wird
  // THEN kein Crash
  it('[D] GIVEN empty thinking block WHEN parsed THEN no crash', () => {
    const parser = new ThinkingStreamParser();
    parser.feed('<|think|><|/think|>OK');
    expect(parser.thinking).toBe('');
    expect(parser.answer).toBe('OK');
  });
});
