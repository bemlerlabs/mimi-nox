/**
 * ◑ MiMiNox v2 — Zero-Dependency Knowledge Search
 * server/knowledge/search.js
 *
 * DESIGN-PRINZIP:
 *   Kein ChromaDB, kein Python, kein Vector-DB Setup.
 *   Rein Node.js TF-IDF-Suche über vorberechnete Chunks (chunks.json).
 *   → Funktioniert sofort nach `git clone`, offline, ohne Setup.
 *
 * TRIAGE-LAYER:
 *   Jeder Chunk hat eine Priorität: SOFORT / ANLEITUNG / HINTERGRUND
 *   Bei lebensbedrohlichen Anfragen werden SOFORT-Chunks zuerst geliefert.
 */

import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CHUNKS_FILE = join(__dirname, '../../../knowledge/chunks.json');

// ── TF-IDF Basis-Implementierung ────────────────────────────────────

/** Tokenisiert deutschen und englischen Text */
function tokenize(text) {
  return text
    .toLowerCase()
    .replace(/[^\wäöüß]/g, ' ')
    .split(/\s+/)
    .filter(t => t.length > 2);
}

/** Stopwörter Deutsch + Englisch */
const STOPWORDS = new Set([
  'der', 'die', 'das', 'ein', 'eine', 'einen', 'dem', 'den', 'des',
  'und', 'oder', 'aber', 'ist', 'sind', 'war', 'wird', 'werden', 'hat',
  'haben', 'beim', 'bei', 'von', 'mit', 'für', 'auf', 'aus', 'nach', 'zur',
  'zum', 'als', 'wie', 'auch', 'nicht', 'wenn', 'dann', 'noch', 'nur',
  'sehr', 'mehr', 'alle', 'kann', 'kann', 'muss', 'soll', 'wird',
  'the', 'and', 'for', 'with', 'this', 'that', 'are', 'not', 'you',
]);

/** TF: Term Frequency im Chunk */
function tf(term, tokens) {
  const count = tokens.filter(t => t === term).length;
  return count / tokens.length;
}

/** BM25-ähnliches Scoring */
function score(query, chunk) {
  const queryTokens = tokenize(query).filter(t => !STOPWORDS.has(t));
  if (queryTokens.length === 0) return 0;
  
  const chunkTokens = chunk._tokens;
  let score = 0;
  
  for (const qt of queryTokens) {
    // TITEL-Match (5× Gewicht) — Chunk ist wirklich über das Thema
    const titleMatches = (chunk._titleTokens || []).filter(t => t === qt || t.startsWith(qt) || qt.startsWith(t)).length;
    if (titleMatches > 0) score += titleMatches * 5;

    // Fließtext: Exact match
    const freq = chunkTokens.filter(t => t === qt).length;
    if (freq > 0) score += freq * 2;

    // Fließtext: Partial match (prefix)
    const partials = chunkTokens.filter(t => t.startsWith(qt) || qt.startsWith(t));
    score += partials.length * 0.3; // reduziert um False Positives zu dämpfen
  }
  
  // TRIAGE BOOST: Sofort-Chunks bekommen Bonus bei Notfall-Anfragen
  const urgentKeywords = ['notfall', 'hilfe', 'verletzt', 'bewusstlos', 'blut', 'herzstill', 
                           'vergif', 'nicht atm', 'kollaps', 'rettung', 'dringend', 'sofort',
                           'emergency', 'help', 'danger'];
  const isUrgentQuery = urgentKeywords.some(kw => query.toLowerCase().includes(kw));
  
  if (isUrgentQuery && chunk.priority === 'SOFORT') {
    score *= 3;
  } else if (chunk.priority === 'SOFORT') {
    score *= 1.5;
  }
  
  // Domain-Match Boost wenn explizit nach Agent gefragt
  const domainHints = {
    medical: ['medic', 'arzt', 'wunde', 'verletzt', 'krank', 'schmerz', 'blut', 'medizin', 'puls'],
    engineering: ['solar', 'strom', 'reparatur', 'technik', 'generator', 'funk', 'akku', 'filter'],
    survival: ['überleben', 'vorrat', 'wasser', 'evakuierung', 'shelter', 'notvorrat', 'feuer'],
    navigation: ['karte', 'kompass', 'weg', 'orientierung', 'norden', 'richtung', 'gelände'],
    cbrn: ['strahlung', 'chemie', 'nuklear', 'jod', 'abc', 'kontaminat'],
  };
  
  for (const [domain, hints] of Object.entries(domainHints)) {
    if (chunk.domain === domain && hints.some(h => query.toLowerCase().includes(h))) {
      score *= 1.8;
      break;
    }
  }
  
  return score;
}

// ── Chunk-Laden mit Lazy Initialization ─────────────────────────────

let _chunks = null;

function getChunks() {
  if (_chunks) return _chunks;
  
  if (!existsSync(CHUNKS_FILE)) {
    console.warn('[KB] chunks.json nicht gefunden — führe `npm run kb:build` aus');
    return [];
  }
  
  try {
    const raw = readFileSync(CHUNKS_FILE, 'utf-8');
    _chunks = JSON.parse(raw);
    
    // Pre-tokenisieren für Performance (Text + Titel separat)
    for (const chunk of _chunks) {
      chunk._tokens = tokenize(chunk.text);
      chunk._titleTokens = tokenize(chunk.title || chunk.source || '');
    }
    
    console.log(`[KB] ${_chunks.length} Knowledge-Chunks geladen`);
    return _chunks;
  } catch (err) {
    console.error('[KB] Fehler beim Laden der chunks.json:', err.message);
    return [];
  }
}

// ── Public API ──────────────────────────────────────────────────────

/**
 * Sucht nach relevanten Chunks für eine Anfrage.
 * 
 * @param {string} query - Die Suchanfrage
 * @param {Object} options
 * @param {number} [options.limit=5] - Max. Anzahl Ergebnisse
 * @param {string} [options.domain] - Optional: Domain filtern (medical/engineering/...)
 * @param {boolean} [options.urgentOnly] - Nur SOFORT-Chunks
 * @returns {Array<{text, domain, source, priority, title, score}>}
 */
export function searchKnowledge(query, { limit = 5, domain = null, urgentOnly = false } = {}) {
  const chunks = getChunks();
  if (chunks.length === 0) return [];
  
  let candidates = chunks;
  
  // Domain-Filter
  if (domain) {
    candidates = chunks.filter(c => c.domain === domain);
  }
  
  // Triage-Filter
  if (urgentOnly) {
    candidates = candidates.filter(c => c.priority === 'SOFORT');
  }
  
  // Scorings berechnen
  const scored = candidates
    .map(chunk => ({ ...chunk, _score: score(query, chunk) }))
    .filter(c => c._score > 0)
    .sort((a, b) => b._score - a._score)
    .slice(0, limit);
  
  // Tokens entfernen (nicht in Response)
  return scored.map(({ _tokens, _score, ...rest }) => ({
    ...rest,
    score: Math.round(_score * 10) / 10,
  }));
}

/**
 * Gibt die Top-Sofortmaßnahmen für eine Notfall-Situation zurück.
 * Immer max. 3 Chunks → kurz, schnell, lebensrettend.
 * 
 * @param {string} situation - Beschreibung der Situation
 * @returns {Array}
 */
export function getEmergencyResponse(situation) {
  return searchKnowledge(situation, { limit: 3, urgentOnly: true });
}

/**
 * Gibt alle Chunks einer Domain zurück (für Kontext-Aufbau).
 * @param {string} domain 
 * @returns {Array}
 */
export function getDomainChunks(domain) {
  return getChunks().filter(c => c.domain === domain);
}

/** Statistiken der Wissensbasis */
export function getKnowledgeStats() {
  const chunks = getChunks();
  const byDomain = {};
  const byPriority = {};
  
  for (const c of chunks) {
    byDomain[c.domain] = (byDomain[c.domain] || 0) + 1;
    byPriority[c.priority] = (byPriority[c.priority] || 0) + 1;
  }
  
  return {
    totalChunks: chunks.length,
    byDomain,
    byPriority,
    loaded: chunks.length > 0,
  };
}
