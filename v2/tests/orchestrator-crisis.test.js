import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Orchestrator } from '../server/agents/orchestrator.js';

// Mock dependencies
const mockStore = {
  createAgent: vi.fn(),
  updateAgent: vi.fn(),
  getAllAgents: vi.fn().mockReturnValue([])
};
const mockBus = {
  send: vi.fn(),
  broadcast: vi.fn(),
  getHistory: vi.fn().mockReturnValue([])
};
const mockKanban = {
  getAll: vi.fn().mockReturnValue([]),
  getGrouped: vi.fn().mockReturnValue({})
};
const mockSkills = {
  initProfile: vi.fn(),
  getProfile: vi.fn()
};
const mockComm = {
  assignTask: vi.fn()
};
const mockJournal = {
  getContextPrompt: vi.fn(),
  getRecent: vi.fn().mockReturnValue([])
};

describe('Crisis Orchestrator (Phase 2)', () => {
  let orch;

  beforeEach(() => {
    vi.clearAllMocks();
    orch = new Orchestrator({ 
      store: mockStore, 
      bus: mockBus, 
      kanban: mockKanban, 
      skills: mockSkills, 
      comm: mockComm, 
      journal: mockJournal 
    });
  });

  it('should initialize the crisis team correctly', () => {
    orch.initFirma(); // initFirma = crisis team init
    
    expect(mockStore.createAgent).toHaveBeenCalledTimes(4);
    // Should create medic, engineer, navigator, sensor
    const agentIds = mockStore.createAgent.mock.calls.map(call => call[0].id);
    expect(agentIds).toContain('medic_agent');
    expect(agentIds).toContain('engineer_agent');
    expect(agentIds).toContain('navigator_agent');
    expect(agentIds).toContain('sensor_agent');
    
    expect(mockBus.broadcast).toHaveBeenCalledWith(expect.objectContaining({
      content: expect.stringContaining('Krisen-Modus')
    }));
  });

  it('should route a medical prompt to the medic agent', async () => {
    orch.initCrisisTeam();
    await orch.submitTask('Ich habe mir den Arm verbrannt');
    
    expect(mockBus.send).toHaveBeenCalledWith(expect.objectContaining({
      to: 'medic_agent',
      content: 'Ich habe mir den Arm verbrannt'
    }));
    expect(mockStore.updateAgent).toHaveBeenCalledWith('medic_agent', { status: 'working' });
  });

  it('should route an engineering prompt to the engineer agent', async () => {
    orch.initCrisisTeam();
    await orch.submitTask('Wie repariere ich mein Solarpanel?');
    
    expect(mockBus.send).toHaveBeenCalledWith(expect.objectContaining({
      to: 'engineer_agent',
      content: 'Wie repariere ich mein Solarpanel?'
    }));
  });

  it('should respect slash commands for direct routing', async () => {
    orch.initCrisisTeam();
    await orch.submitTask('/map Wo ist Norden?');
    
    expect(mockBus.send).toHaveBeenCalledWith(expect.objectContaining({
      to: 'navigator_agent',
      content: 'Wo ist Norden?'
    }));
  });

  it('should fallback to sensor_agent if no keywords match (default)', async () => {
    orch.initFirma(); // Crisis team initialized
    await orch.submitTask('Erzähl mir einen Witz');
    
    // No medical/engineering/navigation keywords → falls back to sensor_agent (default)
    expect(mockBus.send).toHaveBeenCalledWith(expect.objectContaining({
      to: 'sensor_agent'
    }));
  });
});
