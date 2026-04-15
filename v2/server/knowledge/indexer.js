/**
 * ◑ MiMiNox v2 — Knowledge Indexer (Legacy-Shim)
 * server/knowledge/indexer.js
 *
 * Dieser Indexer nutzt jetzt den Zero-Dependency TF-IDF-Ansatz
 * statt ChromaDB + PythonBridge.
 *
 * Beim Server-Start wird automatisch die vorberechnete chunks.json geladen.
 * Kein Setup, kein Python, kein ChromaDB nötig.
 *
 * Um die Knowledge Base zu aktualisieren:
 *   npm run kb:build
 */

import { getKnowledgeStats } from './search.js';

export async function indexKnowledge() {
  const stats = getKnowledgeStats();

  if (!stats.loaded) {
    console.warn('[KB] ⚠ Keine chunks.json gefunden!');
    console.warn('[KB]   → Führe `npm run kb:build` aus um die Wissensbasis zu erstellen.');
    return { domains: [], lastIndexed: null, stats: { totalChunks: 0 } };
  }

  console.log(`[KB] ✓ ${stats.totalChunks} Wissens-Chunks geladen`);
  console.log(`[KB]   🚨 SOFORT: ${stats.byPriority?.SOFORT || 0}  📋 ANLEITUNG: ${stats.byPriority?.ANLEITUNG || 0}  📖 HINTERGRUND: ${stats.byPriority?.HINTERGRUND || 0}`);

  const domains = Object.keys(stats.byDomain || {});

  return {
    domains,
    lastIndexed: new Date().toISOString(),
    stats: {
      totalChunks: stats.totalChunks,
      byDomain: stats.byDomain,
      byPriority: stats.byPriority,
    }
  };
}

// Für direkten Aufruf: zeige Status
const isMain = process.argv[1]?.endsWith('indexer.js');
if (isMain) {
  indexKnowledge()
    .then(info => console.log('[KB] Status:', JSON.stringify(info, null, 2)))
    .catch(err => console.error('[KB] Fehler:', err));
}
