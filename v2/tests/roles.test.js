/**
 * ◑ MiMiNox v2 — Test: Rollen-Definitionen
 * Krisen-Agenten: Medic, Engineer, Navigator, Sensor
 * TDD: Tests FIRST.
 */
import { describe, it, expect } from 'vitest';
import { loadRole, getAllRoles, isToolAllowed } from '../server/agents/roles.js';

describe('Krisen-Rollen-Definitionen', () => {

  it('[D] GIVEN roles WHEN loadRole("medic_agent") THEN returns full config', () => {
    const role = loadRole('medic_agent');
    expect(role).toBeDefined();
    expect(role.name).toBe('Mimi-Medic');
    expect(role.role).toBe('medic');
    expect(role.systemPrompt).toContain('Medic');
    expect(Array.isArray(role.toolWhitelist)).toBe(true);
    expect(role.toolWhitelist.length).toBeGreaterThan(0);
    expect(role.skills).toBeDefined();
  });

  it('[D] GIVEN roles WHEN loadRole("engineer_agent") THEN has Engineer config', () => {
    const role = loadRole('engineer_agent');
    expect(role.name).toBe('Mimi-Engineer');
    expect(role.role).toBe('engineer');
    expect(role.systemPrompt).toContain('Engineer');
  });

  it('[D] GIVEN roles WHEN loadRole("navigator_agent") THEN has Navigator config', () => {
    const role = loadRole('navigator_agent');
    expect(role.name).toBe('Mimi-Navigator');
    expect(role.role).toBe('navigator');
    expect(role.toolWhitelist).toContain('search_knowledge');
  });

  it('[D] GIVEN roles WHEN loadRole("sensor_agent") THEN has Sensor config', () => {
    const role = loadRole('sensor_agent');
    expect(role.name).toBe('Mimi-Sensor');
    expect(role.role).toBe('sensor');
  });

  it('[D] GIVEN all roles WHEN getAllRoles THEN returns 4 crisis agents', () => {
    const roles = getAllRoles();
    expect(roles).toHaveLength(4);
    const ids = roles.map(r => r.id);
    expect(ids).toContain('medic_agent');
    expect(ids).toContain('engineer_agent');
    expect(ids).toContain('navigator_agent');
    expect(ids).toContain('sensor_agent');
  });

  it('[D] GIVEN medic_agent WHEN isToolAllowed("search_knowledge") THEN returns true', () => {
    expect(isToolAllowed('medic_agent', 'search_knowledge')).toBe(true);
    expect(isToolAllowed('medic_agent', 'run_shell')).toBe(false);
  });

  it('[D] GIVEN engineer_agent WHEN isToolAllowed("read_file") THEN returns true', () => {
    expect(isToolAllowed('engineer_agent', 'read_file')).toBe(true);
    expect(isToolAllowed('engineer_agent', 'run_shell')).toBe(false);
  });

  it('[D] GIVEN unknown role WHEN loadRole THEN throws', () => {
    expect(() => loadRole('unknown_role')).toThrow();
  });

  it('[D] GIVEN medic_agent WHEN checking skills THEN has crisis skills with initial values', () => {
    const role = loadRole('medic_agent');
    const skillNames = Object.keys(role.skills);
    expect(skillNames.length).toBeGreaterThanOrEqual(4);
    expect(skillNames).toContain('firstAid');
    expect(skillNames).toContain('diagnosis');
    expect(skillNames).toContain('communication');
    for (const val of Object.values(role.skills)) {
      expect(val).toBeGreaterThan(0);
      expect(val).toBeLessThanOrEqual(100);
    }
  });
});

// ── T-15: Dynamische Rollen aus YAML ─────────────────────────────────────────

import { writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { loadRolesFromFile, RoleConfigError } from '../server/agents/roles.js';

describe('T-15: Dynamische Rollen aus YAML', () => {

  it('[T-15] GIVEN valid YAML WHEN loadRolesFromFile THEN roles loaded', async () => {
    const yaml = `
roles:
  field_medic:
    name: Field-Medic
    role: medic
    systemPrompt: "Du bist ein Feld-Sanitäter"
    toolWhitelist: [search_knowledge]
    skills: { firstAid: 80, diagnosis: 70 }
  field_sapper:
    name: Field-Sapper
    role: engineer
    systemPrompt: "Du bist ein Pionier"
    toolWhitelist: [search_knowledge, read_file]
    skills: { demolition: 70, construction: 65 }
`;
    const yamlPath = join(tmpdir(), `roles-test-${Date.now()}.yaml`);
    writeFileSync(yamlPath, yaml.trim());

    await loadRolesFromFile(yamlPath);
    const { getAllRoles: getAll } = await import('../server/agents/roles.js');
    // 4 base crisis agents + 2 YAML agents = 6
    expect(getAll()).toHaveLength(6);
  });

  it('[T-15] GIVEN nonexistent file WHEN loadRolesFromFile THEN throws RoleConfigError', async () => {
    await expect(loadRolesFromFile('/nonexistent/roles.yaml'))
      .rejects.toThrow('RoleConfigError');
  });
});
