/**
 * ◑ MiMiNox v2 — Thought Decomposer
 * server/transparency/thought-decomposer.js
 *
 * Zerlegt rohen Gedanken-Text in einen hierarchischen Baum.
 * Erkennt Fragen als Root-Knoten und Aussagen als Kinder.
 *
 * T-19: decomposeWithLLM() — LLM-gestützte Verfeinerung mit typenreichem
 * Dependency-Graph. Fallback auf heuristischen decompose() bei LLM-Fehler.
 */

export class ThoughtDecomposer {
  /**
   * Decompose raw thinking text into a tree structure (heuristisch).
   * @param {string} text
   * @returns {{ root: string, children: Array<{ text: string, type: string }> }}
   */
  decompose(text) {
    if (!text || !text.trim()) {
      return { root: '', children: [] };
    }

    const sentences = this._splitSentences(text.trim());

    if (sentences.length <= 1) {
      return { root: sentences[0] || text.trim(), children: [] };
    }

    const questionIdx = sentences.findIndex(s => s.includes('?'));
    let root, rest;

    if (questionIdx >= 0) {
      root = sentences[questionIdx];
      rest = [...sentences.slice(0, questionIdx), ...sentences.slice(questionIdx + 1)];
    } else {
      root = sentences[0];
      rest = sentences.slice(1);
    }

    return {
      root,
      children: rest.map(s => ({ text: s, type: this._classifySentence(s) })),
    };
  }

  /**
   * T-19: LLM-gestützte Dekomposition mit typenreichem Dependency-Graph.
   *
   * Erwartet vom LLM folgendes JSON:
   *   { root: string, children: [{ text, type, dependsOn: number[] }] }
   *
   * Fallback auf heuristischen decompose() wenn:
   *   - llmClient null ist
   *   - LLM-Call fehlschlägt
   *   - Antwort kein valides JSON / falsche Struktur
   *
   * @param {string} text
   * @param {{ chat: Function }|null} llmClient
   * @returns {Promise<{ root: string, children: Array }>}
   */
  async decomposeWithLLM(text, llmClient) {
    if (!llmClient) {
      return this.decompose(text);
    }

    try {
      const response = await llmClient.chat([
        {
          role: 'system',
          content: [
            'Du bist ein Reasoning-Analyst.',
            'Zerleg den folgenden Gedankentext in einen JSON-Baum:',
            '{ "root": "<Hauptfrage>", "children": [{ "text": "...", "type": "reasoning|consideration|conclusion|concern|step", "dependsOn": [<Indizes>] }] }',
            'Antworte NUR mit dem JSON-Objekt, kein weiterer Text.',
          ].join('\n'),
        },
        { role: 'user', content: text },
      ]);

      const raw  = response?.message?.content || '';
      const tree = JSON.parse(raw.trim());

      if (!tree.root || !Array.isArray(tree.children)) {
        throw new Error('Invalid tree structure from LLM');
      }

      return tree;
    } catch {
      // T-19: Graceful Fallback — heuristischer Decomposer
      return this.decompose(text);
    }
  }

  _splitSentences(text) {
    return text
      .split(/(?<=[.!?])\s+/)
      .map(s => s.trim())
      .filter(s => s.length > 0);
  }

  _classifySentence(sentence) {
    if (sentence.includes('?')) return 'question';
    if (/^(also|daher|deshalb|fazit|ergebnis|schluss)/i.test(sentence)) return 'conclusion';
    if (/^(aber|jedoch|allerdings|problem)/i.test(sentence)) return 'concern';
    if (/^(erst|dann|danach|zuerst|schritt)/i.test(sentence)) return 'step';
    return 'reasoning';
  }
}
