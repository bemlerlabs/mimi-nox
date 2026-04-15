/**
 * ◑ MiMiNox v2 — Test: RPG-Skill-System
 * Task 2.7: Skills, XP, Level-Up, Persistenz
 * TDD: Tests FIRST.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { SkillSystem } from '../server/agents/skill-system.js';
import { StateStore } from '../server/state/store.js';
import { loadRole } from '../server/agents/roles.js';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

function tmpDbPath() {
  return path.join(os.tmpdir(), `miminox-skills-${Date.now()}-${Math.random().toString(36).slice(2)}.db`);
}

describe('Task 2.7: RPG-Skill-System', () => {
  let store, skills;

  beforeEach(() => {
    store = new StateStore(':memory:');
    skills = new SkillSystem(store);
  });

  afterEach(() => store?.close());

  // ── Skill-Profil initialisieren ───────────────────────────────────

  // GIVEN ein neuer Krisen-Agent "medic_agent"
  // WHEN sein Skill-Profil erstellt wird
  // THEN hat er Skills und Level 1
  it('[D] GIVEN new agent WHEN initProfile THEN has skills at level 1', () => {
    const role = loadRole('medic_agent');
    skills.initProfile('medic_agent', role.skills);

    const profile = skills.getProfile('medic_agent');
    expect(profile).toBeDefined();
    expect(profile.level).toBe(1);
    expect(profile.xp).toBe(0);
    expect(Object.keys(profile.skills).length).toBeGreaterThanOrEqual(4);
    expect(profile.skills.communication).toBeGreaterThan(0);
  });

  // ── XP durch Task-Completion ──────────────────────────────────────

  // GIVEN Charlie mit Code Quality: 50
  // WHEN er ein Ticket ohne QA-Rejection abschließt
  // THEN steigt Code Quality um +3
  it('[D] GIVEN profile WHEN taskCompleted without rejection THEN codeQuality +3', () => {
    // SkillSystem nutzt generische Skill-Namen — initProfile mit exakten Startwerten
    skills.initProfile('agent_x', { codeQuality: 50, bugDetection: 30, architecture: 25,
      research: 40, speed: 45, toolMastery: 35, communication: 70, testing: 40 });

    skills.onTaskCompleted('agent_x', { rejected: false });

    const profile = skills.getProfile('agent_x');
    expect(profile.skills.codeQuality).toBe(53); // 50 + 3
    expect(profile.xp).toBeGreaterThan(0);
  });

  // ── XP durch QA-Feedback-Loop ─────────────────────────────────────

  // GIVEN Charlie mit Bug Detection: 30
  // WHEN QA ablehnt UND er den Fix einreicht
  // THEN steigt Bug Detection um +8
  it('[D] GIVEN profile WHEN qaRejectionFixed THEN bugDetection +8', () => {
    skills.initProfile('agent_x2', { codeQuality: 50, bugDetection: 30, architecture: 25,
      research: 40, speed: 45, toolMastery: 35, communication: 70, testing: 40 });

    skills.onQARejectionFixed('agent_x2');

    const profile = skills.getProfile('agent_x2');
    expect(profile.skills.bugDetection).toBe(38); // 30 + 8
  });

  // ── XP durch Tool-Usage ───────────────────────────────────────────

  // GIVEN Charlie mit Research: 40
  // WHEN er web_search nutzt
  // THEN steigt Research um +5
  it('[D] GIVEN profile WHEN toolUsed("web_search") THEN research +5', () => {
    skills.initProfile('agent_x3', { codeQuality: 50, bugDetection: 30, architecture: 25,
      research: 40, speed: 45, toolMastery: 35, communication: 70, testing: 40 });

    skills.onToolUsed('agent_x3', 'web_search');

    const profile = skills.getProfile('agent_x3');
    expect(profile.skills.research).toBe(45); // 40 + 5
  });

  // GIVEN Charlie
  // WHEN er ein Tool zum ERSTEN Mal nutzt
  // THEN steigt Tool Mastery um +4
  it('[D] GIVEN profile WHEN first time tool THEN toolMastery +4', () => {
    skills.initProfile('agent_x4', { codeQuality: 50, bugDetection: 30, architecture: 25,
      research: 40, speed: 45, toolMastery: 35, communication: 70, testing: 40 });

    skills.onToolUsed('agent_x4', 'browser_go');

    const profile = skills.getProfile('agent_x4');
    expect(profile.skills.toolMastery).toBe(39); // 35 + 4
    expect(profile.skills.research).toBe(45); // 40 + 5
  });

  // ── Level-Up ──────────────────────────────────────────────────────

  // GIVEN Charlie mit Level 3 und 950/1000 XP
  // WHEN er 100 XP erhält
  // THEN Level-Up auf 4
  it('[D] GIVEN high xp WHEN gains more THEN level up', () => {
    skills.initProfile('agent_x5', { codeQuality: 50, bugDetection: 30, architecture: 25,
      research: 40, speed: 45, toolMastery: 35, communication: 70, testing: 40 });

    skills._setXP('agent_x5', 2950);
    skills._setLevel('agent_x5', 3);

    const events = [];
    store.subscribe(e => { if (e.type === 'agent_level_up') events.push(e); });

    skills.addXP('agent_x5', 100);

    expect(skills.getProfile('agent_x5').level).toBe(4);
    expect(events).toHaveLength(1);
    expect(events[0].agentId).toBe('agent_x5');
    expect(events[0].newLevel).toBe(4);
  });

  // ── Skill-Cap bei 100 ────────────────────────────────────────────

  it('[D] GIVEN skill at 99 WHEN gains +5 THEN capped at 100', () => {
    skills.initProfile('test_agent', {
      codeQuality: 99, bugDetection: 50, architecture: 50, research: 50,
      speed: 50, toolMastery: 50, communication: 50, testing: 50,
    });

    skills.addSkillXP('test_agent', 'codeQuality', 5);
    expect(skills.getProfile('test_agent').skills.codeQuality).toBe(100);
  });

  // ── Persistenz ────────────────────────────────────────────────────

  it('[D] GIVEN profile WHEN store closed and reopened THEN profile persists', () => {
    const dbPath = tmpDbPath();
    const store1 = new StateStore(dbPath);
    const skills1 = new SkillSystem(store1);

    skills1.initProfile('persist_agent', { codeQuality: 50, bugDetection: 30, architecture: 25,
      research: 40, speed: 45, toolMastery: 35, communication: 70, testing: 40 });
    skills1.onTaskCompleted('persist_agent', { rejected: false });
    store1.close();

    // Reopen
    const store2 = new StateStore(dbPath);
    const skills2 = new SkillSystem(store2);
    const profile = skills2.getProfile('persist_agent');

    expect(profile).toBeDefined();
    expect(profile.skills.codeQuality).toBe(53); // 50 + 3
    expect(profile.xp).toBeGreaterThan(0);

    store2.close();
    try { fs.unlinkSync(dbPath); } catch {}
  });

  // ── Recent Learnings ──────────────────────────────────────────────

  it('[D] GIVEN skill changes WHEN getProfile THEN recentLearnings populated', () => {
    skills.initProfile('learn_agent', { codeQuality: 50, bugDetection: 30, architecture: 25,
      research: 40, speed: 45, toolMastery: 35, communication: 70, testing: 40 });

    skills.onTaskCompleted('learn_agent', { rejected: false });
    skills.onQARejectionFixed('learn_agent');

    const profile = skills.getProfile('learn_agent');
    expect(profile.recentLearnings.length).toBeGreaterThanOrEqual(2);
  });
});

// ── T-18: getWeakestSkill — Deterministisches Tie-Breaking ───────────────────

describe('T-18: getWeakestSkill — Determinism', () => {
  let store, skills;
  beforeEach(() => { store = new StateStore(':memory:'); skills = new SkillSystem(store); });
  afterEach(() => store?.close());

  // GIVEN testing=0 WHEN getWeakestSkill THEN returns testing
  it('[T-18] GIVEN testing=0 WHEN getWeakestSkill THEN returns testing skill', () => {
    skills.initProfile('test_agent', {
      codeQuality: 50, bugDetection: 50, architecture: 50,
      research: 50, speed: 50, toolMastery: 50, communication: 50, testing: 0,
    });
    const weakest = skills.getWeakestSkill('test_agent');
    expect(weakest.skill).toBe('testing');
    expect(weakest.value).toBe(0);
  });

  // GIVEN alle Skills gleich WHEN getWeakestSkill THEN deterministisch
  it('[T-18] GIVEN all skills equal WHEN getWeakestSkill THEN deterministic', () => {
    skills.initProfile('equal_agent', {
      codeQuality: 50, bugDetection: 50, architecture: 50,
      research: 50, speed: 50, toolMastery: 50, communication: 50, testing: 50,
    });
    const w1 = skills.getWeakestSkill('equal_agent');
    const w2 = skills.getWeakestSkill('equal_agent');
    expect(w1.skill).toBe(w2.skill); // deterministisch — kein zufälliges Ergebnis
  });
});

// ── T-20: Skill-Evolution — Empirische Validierung ───────────────────────────

describe('T-20: Skill-Evolution — Wachstumskurve', () => {
  let store, skills;
  beforeEach(() => { store = new StateStore(':memory:'); skills = new SkillSystem(store); });
  afterEach(() => store?.close());

  // GIVEN 50 Tasks ohne Rejection WHEN getProfile THEN codeQuality messbar gestiegen
  it('[T-20] GIVEN 50 tasks no rejection WHEN profile checked THEN codeQuality grew and capped', () => {
    skills.initProfile('veteran', {
      codeQuality: 50, bugDetection: 30, architecture: 25,
      research: 40, speed: 45, toolMastery: 35, communication: 30, testing: 40,
    });
    const initial = skills.getProfile('veteran').skills.codeQuality;
    for (let i = 0; i < 50; i++) {
      skills.onTaskCompleted('veteran', { rejected: false });
    }
    const final = skills.getProfile('veteran').skills.codeQuality;
    expect(final).toBeGreaterThan(initial);
    expect(final).toBeLessThanOrEqual(100); // Cap
  });
});
