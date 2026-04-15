/**
 * ◑ MiMiNox v2 — Crisis Router
 * server/agents/crisis-router.js
 * 
 * Keyword-based routing for offline crisis scenarios.
 * Fast, deterministic, and works without LLM for initial dispatch.
 */

const CRISIS_KEYWORDS = {
  medic_agent: [
    'medizin', 'arzt', 'hilfe', 'verletzt', 'wunde', 'blut', 'fieber', 'schmerz',
    'apotheke', 'notfall', 'erste hilfe', 'medic', 'krank', 'bruch', 'biss',
    'vergiftung', 'atmen', 'bewusstlos', 'verbrannt', 'verbrennung', 'verletzung',
    'übelkeit', 'erbrechen', 'durchfall', 'infekt',
    // Herznotfall
    'herzstillstand', 'herzinfarkt', 'reanimation', 'hlw', 'wiederbelebung',
    'puls', 'atem', 'kollaps', 'ohnmacht', 'bewusstlos', 'nicht mehr atmet',
    'herzdrück', 'herzdruckmassage', 'defibrillator', 'aed',
    // Trauma
    'starke blutung', 'schockzustand', 'knochenbruch', 'fraktur', 'stich',
    'schnitt', 'wundversorgung', 'druckverband', 'tourniquet',
    // Umwelt
    'unterkühlung', 'hitzschlag', 'sonnenstich', 'ertrinken', 'stromschlag',
    'hyperventilation', 'panikattacke', 'krampfanfall'
  ],
  engineer_agent: [
    'reparatur', 'kaputt', 'defekt', 'solar', 'batterie', 'strom', 'generator', 
    'kabel', 'spannung', 'werkzeug', 'instandsetzung', 'elektronik', 'mechanik',
    'motor', 'pumpe', 'wasserfilter', 'licht', 'off-grid', 'wartung', 'anschluss'
  ],
  navigator_agent: [
    'karte', 'navigation', 'weg', 'route', 'standort', 'koordinaten', 'gps', 
    'orientierung', 'kompass', 'norden', 'wald', 'berg', 'ziel', 'entfernung',
    'gelände', 'wetter', 'vorhersage', 'karte', 'umgebung'
  ],
  sensor_agent: [
    'status', 'system', 'leistung', 'cpu', 'ram', 'speicher', 'auslastung', 
    'warnung', 'alarm', 'telemetrie', 'uptime', 'hardware', 'power', 'verbrauch'
  ]
};

/**
 * Routes a prompt to the most suitable crisis agent.
 * @param {string} prompt 
 * @returns {{ agentId: string|null, confidence: number, sanitizedPrompt: string }}
 */
export function routeCrisisPrompt(prompt) {
  const p = prompt.trim().toLowerCase();
  
  // 1. Detect Slash-Commands
  const slashMatch = p.match(/^\/([a-z]+)/);
  if (slashMatch) {
    const command = slashMatch[1];
    const sanitized = prompt.replace(/^\/[a-z]+\s*/i, '');
    
    if (command === 'medic' || command === 'arzt') return { agentId: 'medic_agent', confidence: 1.0, sanitizedPrompt: sanitized };
    if (command === 'repair' || command === 'engineer') return { agentId: 'engineer_agent', confidence: 1.0, sanitizedPrompt: sanitized };
    if (command === 'map' || command === 'nav') return { agentId: 'navigator_agent', confidence: 1.0, sanitizedPrompt: sanitized };
    if (command === 'power' || command === 'status' || command === 'sensor') return { agentId: 'sensor_agent', confidence: 1.0, sanitizedPrompt: sanitized };
  }

  // 2. Keyword Matching
  let bestAgent = null;
  let maxScore = 0;

  for (const [agentId, keywords] of Object.entries(CRISIS_KEYWORDS)) {
    let score = 0;
    for (const kw of keywords) {
      if (p.includes(kw)) {
        score += 1;
      }
    }
    if (score > maxScore) {
      maxScore = score;
      bestAgent = agentId;
    }
  }

  // Calculate confidence (simple: keywords found / 3, max 0.9)
  const confidence = Math.min(0.9, maxScore / 2);

  return {
    agentId: maxScore > 0 ? bestAgent : null,
    confidence,
    sanitizedPrompt: prompt
  };
}
