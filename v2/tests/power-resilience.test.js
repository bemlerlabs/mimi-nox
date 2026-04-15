import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Orchestrator } from '../server/agents/orchestrator.js';

describe('Power Resilience (Phase 5)', () => {
  let orch;

  beforeEach(() => {
    const mocks = {
      store: { updateAgent: vi.fn() }, 
      bus: { send: vi.fn() }, 
      kanban: {}, skills: {}, comm: {}, journal: {}
    };
    orch = new Orchestrator(mocks);
    global.fetch = vi.fn();
  });

  it('should switch to resilience mode when CPU is high', async () => {
    global.fetch.mockResolvedValue({
      json: async () => ({ airGapped: true, cpu_usage: 95 })
    });

    await orch.checkPowerResilience();
    expect(orch.powerPolicy).toBe('resilience');
  });

  it('should block non-crisis tasks in resilience mode', async () => {
    global.fetch.mockResolvedValue({
      json: async () => ({ airGapped: true, cpu_usage: 95 })
    });

    const result = await orch.submitTask('Erzähl mir einen Witz');
    expect(result.type).toBe('error');
    expect(result.content).toContain('ENERGIE-SPARMODUS');
  });

  it('should allow crisis tasks even in resilience mode', async () => {
    global.fetch.mockResolvedValue({
      json: async () => ({ airGapped: true, cpu_usage: 95 })
    });
    
    // We expect it NOT to return the error block, but to proceed to routing
    // We mock the rest of the flow to avoid full agent spawning
    orch.routeCrisisPrompt = vi.fn().mockReturnValue('medic_agent');
    orch.bus = { send: vi.fn() };

    const result = await orch.submitTask('/medic Ich brauche Hilfe');
    expect(result).not.toHaveProperty('type', 'error');
  });
});
