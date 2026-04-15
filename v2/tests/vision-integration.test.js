import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Orchestrator } from '../server/agents/orchestrator.js';
import { OllamaClient } from '../llm/ollama-client.js';

describe('Vision Integration (Phase 6)', () => {
  let orch;
  let mockLLM;

  beforeEach(() => {
    mockLLM = {
      chat: vi.fn().mockResolvedValue({ 
        content: 'Das sind Blaubeeren (Vaccinium myrtillus). Sie sind essbar.',
        toolCalls: [] 
      })
    };
    
    const mocks = {
      store: { updateAgent: vi.fn(), addChatMessage: vi.fn() },
      bus: { send: vi.fn(), getHistory: () => [] },
      kanban: {},
      skills: { getProfile: () => ({ skills: {} }) },
      comm: { assignTask: vi.fn() },
      journal: { getContextPrompt: () => '', getRecent: () => [] }
    };
    
    orch = new Orchestrator(mocks);
    orch._llm = mockLLM;
  });

  it('should pass images from submitTask to the LLM agent', async () => {
    const testImage = 'base64_berry_image_data';
    const prompt = 'Kann ich diese Beeren essen?';
    
    await orch.submitTask(prompt, [testImage]);
    
    // Check if CEO was asked with images
    expect(mockLLM.chat).toHaveBeenCalledWith(expect.objectContaining({
      messages: expect.arrayContaining([
        expect.objectContaining({
          role: 'user',
          images: [testImage]
        })
      ])
    }));
  });

  it('should route crisis prompts with images to the correct specialist', async () => {
    const testImage = 'base64_wound_image_data';
    const prompt = '/medic Wie schlimm ist diese Wunde?';
    
    // We don't need to mock the full routing, just check if images are in the bus send
    const busSpy = orch._bus.send;
    
    await orch.submitTask(prompt, [testImage]);
    
    expect(busSpy).toHaveBeenCalledWith(expect.objectContaining({
      to: 'medic_agent',
      images: [testImage]
    }));
  });
});
