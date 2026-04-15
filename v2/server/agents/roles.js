/**
 * ◑ MiMiNox v2 — Rollen-Definitionen
 * server/agents/roles.js
 *
 * Outdoor-Krisen-KI mit 4 Spezial-Agenten:
 *   Medic, Engineer, Navigator, Sensor
 *
 * Powered by Gemma 4 E4B (lokal über Ollama).
 * 100% offline-fähig für Krisensituationen.
 */

// ── Krisen-Agenten ──────────────────────────────────────────────────

const ROLES = {
  medic_agent: {
    id: 'medic_agent',
    name: 'Mimi-Medic',
    role: 'medic',
    emoji: '🚑',
    systemPrompt: `Du bist der MiMi-Medic Spezialagent für Krisensituationen.
Deine Aufgabe: Medizinische Erste Hilfe, Notfalldiagnose und Beratung bei Verletzungen/Erkrankungen im Off-Grid Bereich.
Du nutzt RAG auf lokale medizinische Datenbanken.
NUTZE VISUELLE ANALYSIS: Wenn der User Fotos von Wunden, Schwellungen oder Symptomen hochlädt, analysiere diese präzise auf Farbe, Form und Schweregrad.
WICHTIG: Erinnere den User immer daran, dass du eine KI bist und kein Ersatz für professionelle Hilfe. 
Priorisiere lebensrettende Sofortmaßnahmen.
Antworte auf Deutsch.`,
    toolWhitelist: ['search_knowledge', 'get_datetime', 'analyze_image'],
    skills: {
      firstAid: 70,
      diagnosis: 60,
      trauma: 50,
      pharmacy: 45,
      communication: 70,
    },
  },

  engineer_agent: {
    id: 'engineer_agent',
    name: 'Mimi-Engineer',
    role: 'engineer',
    emoji: '🛠️',
    systemPrompt: `Du bist der MiMi-Engineer Spezialagent für Krisensituationen.
Deine Aufgabe: Reparaturanleitungen für technische Geräte (Solar, Elektronik, Funk, Generatoren, Wasserfilter).
Hilf dem User bei der Wartung und Instandsetzung von autarker Technik. 
Kommuniziere lösungsorientiert und detailliert. Nutze ASCII-Diagramme wenn nötig.
Antworte auf Deutsch.`,
    toolWhitelist: ['search_knowledge', 'read_file', 'list_directory', 'get_datetime'],
    skills: {
      solar: 65,
      electronics: 70,
      mechanics: 60,
      networking: 55,
      communication: 50,
    },
  },

  navigator_agent: {
    id: 'navigator_agent',
    name: 'Mimi-Navigator',
    role: 'navigator',
    emoji: '🗺️',
    systemPrompt: `Du bist der MiMi-Navigator Spezialagent für Krisensituationen.
Deine Aufgabe: Orientierung, Karteninterpretation und Routenplanung ohne Internet.
NUTZE VISUELLE ANALYSIS: Wenn der User Fotos von Pflanzen (z.B. Beeren), Landmarken oder Geländemerkmalen hochlädt, identifiziere diese. 
Warne explizit vor giftigen Pflanzen oder gefährlichem Gelände.
Arbeite mit GPS-Koordinaten, Landmarken und Geländebeschreibungen. 
Gib klare Anweisungen für den Marsch oder die Standortbestimmung.
Antworte auf Deutsch.`,
    toolWhitelist: ['search_knowledge', 'get_datetime', 'analyze_image'],
    skills: {
      terrain: 70,
      compass: 65,
      mapping: 60,
      weather: 55,
      communication: 60,
    },
  },

  sensor_agent: {
    id: 'sensor_agent',
    name: 'Mimi-Sensor',
    role: 'sensor',
    emoji: '⚡',
    systemPrompt: `Du bist der MiMi-Sensor Spezialagent für Krisensituationen.
Deine Aufgabe: Überwachung der lokalen Hardware-Ressourcen (Batterie, CPU, RAM, Speicher) und Auslösen von Warnungen.
Berate den User beim Energiemanagement des Systems. 
Schlage Energiesparmaßnahmen vor wenn Ressourcen knapp werden.
Sei präzise und achte auf Schwellenwerte.
Antworte auf Deutsch.`,
    toolWhitelist: ['get_datetime'],
    skills: {
      monitoring: 75,
      alerting: 70,
      optimization: 60,
      communication: 80,
    },
  },
};

// ── Public API ──────────────────────────────────────────────────────

/**
 * Load a role configuration by agent ID.
 * @param {string} agentId - e.g. "medic_agent", "engineer_agent"
 * @returns {Object} Role config with name, role, systemPrompt, toolWhitelist, skills
 * @throws {Error} If role not found
 */
export function loadRole(agentId) {
  const role = ROLES[agentId];
  if (!role) {
    throw new Error(`Rolle '${agentId}' nicht gefunden. Verfügbar: ${Object.keys(ROLES).join(', ')}`);
  }
  return { ...role };
}

/**
 * Get all available role configurations.
 * @returns {Object[]}
 */
export function getAllRoles() {
  return Object.values(ROLES).map(r => ({ ...r }));
}

/**
 * Check if a specific tool is allowed for a given agent role.
 * @param {string} agentId - Agent ID
 * @param {string} toolName - Tool name
 * @returns {boolean}
 */
export function isToolAllowed(agentId, toolName) {
  const role = ROLES[agentId];
  if (!role) return false;
  return role.toolWhitelist.includes(toolName);
}

// ── T-15: Dynamische Rollen aus YAML ────────────────────────────────

/**
 * T-15: Fehler der geworfen wird wenn eine YAML-Rollen-Datei ungültig ist.
 */
export class RoleConfigError extends Error {
  constructor(message, path) {
    super(`RoleConfigError: ${message} (${path})`);
    this.name = 'RoleConfigError';
    this.configPath = path;
  }
}

/**
 * T-15: Lädt Rollen aus einer YAML-Datei und überschreibt die ROLES-Map.
 *
 * @param {string} filePath - Absoluter Pfad zur YAML-Datei
 * @returns {Promise<void>}
 * @throws {RoleConfigError} wenn Datei nicht gefunden oder ungültiges YAML
 */
export async function loadRolesFromFile(filePath) {
  const { readFileSync } = await import('node:fs');
  let raw;

  try {
    raw = readFileSync(filePath, 'utf-8');
  } catch (err) {
    throw new RoleConfigError(`Datei nicht gefunden: ${err.message}`, filePath);
  }

  let parsed;
  try {
    try {
      const { load } = await import('js-yaml');
      parsed = load(raw);
    } catch {
      parsed = _parseSimpleYaml(raw);
    }
  } catch (err) {
    throw new RoleConfigError(`Ungültiges YAML: ${err.message}`, filePath);
  }

  if (!parsed?.roles || typeof parsed.roles !== 'object') {
    throw new RoleConfigError('Kein "roles"-Schlüssel im YAML gefunden', filePath);
  }

  for (const [id, cfg] of Object.entries(parsed.roles)) {
    ROLES[id] = {
      id,
      name:         cfg.name         || id,
      role:         cfg.role         || id,
      emoji:        cfg.emoji        || '🤖',
      systemPrompt: cfg.systemPrompt || '',
      toolWhitelist: Array.isArray(cfg.toolWhitelist) ? cfg.toolWhitelist : [],
      skills:       cfg.skills       || {},
    };
  }
}

/**
 * Minimaler YAML-Parser Fallback.
 */
function _parseSimpleYaml(raw) {
  throw new Error('js-yaml nicht verfügbar — bitte "npm install js-yaml" ausführen');
}
