/**
 * ◑ MiMiNox v2 — Test: Ollama Client (erweitert)
 * Task 1.2: Gemma 4 Connector — Streaming + Tool-Call Parsing
 * TDD: Tests for features that DON'T require a running Ollama instance.
 */
import { describe, it, expect } from 'vitest';
import { OllamaClient, OllamaNotReachableError } from '../server/llm/ollama-client.js';

describe('Task 1.2: Ollama Client', () => {

  // ── Connection Error ──────────────────────────────────────────────

  it('[D] GIVEN ollama not running WHEN chat called THEN throws OllamaNotReachableError', async () => {
    const client = new OllamaClient({ baseUrl: 'http://localhost:99999' });
    await expect(
      client.chat({ model: 'gemma4:e4b', messages: [{ role: 'user', content: 'Hi' }] })
    ).rejects.toThrow(OllamaNotReachableError);
  });

  // ── Tool Schemas ──────────────────────────────────────────────────

  it('[D] GIVEN client WHEN getToolSchemas called THEN returns valid schemas', () => {
    const client = new OllamaClient();
    const schemas = client.getToolSchemas();
    expect(Array.isArray(schemas)).toBe(true);
    for (const schema of schemas) {
      expect(schema.type).toBe('function');
      expect(schema.function.name).toBeDefined();
      expect(schema.function.parameters).toBeDefined();
    }
  });

  // ── Tool-Call Parsing (unit test with mock response) ──────────────

  it('[D] GIVEN tool-call response WHEN parseToolCalls called THEN extracts tools', () => {
    const client = new OllamaClient();

    // Simulate an Ollama response with tool calls
    const mockResponse = {
      message: {
        content: '',
        tool_calls: [
          {
            function: {
              name: 'web_search',
              arguments: { query: 'Node.js best practices 2026' },
            },
          },
        ],
      },
    };

    const result = client.parseResponse(mockResponse);
    expect(result.toolCalls).toHaveLength(1);
    expect(result.toolCalls[0].function.name).toBe('web_search');
    expect(result.toolCalls[0].function.arguments.query).toBe('Node.js best practices 2026');
  });

  // ── Empty Response Parsing ────────────────────────────────────────

  it('[D] GIVEN text-only response WHEN parseResponse THEN content set, no tools', () => {
    const client = new OllamaClient();

    const mockResponse = {
      message: {
        content: 'Die Antwort ist 42.',
        tool_calls: [],
      },
    };

    const result = client.parseResponse(mockResponse);
    expect(result.content).toBe('Die Antwort ist 42.');
    expect(result.toolCalls).toHaveLength(0);
  });
});
