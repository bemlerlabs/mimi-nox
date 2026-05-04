/**
 * ◑ MiMiNox Field-Tools — Test: Taschenlampe (Torch)
 * TDD: Tests FIRST, dann Implementation.
 *
 * GIVEN / WHEN / THEN
 */
import { describe, it, expect } from 'vitest';
import { createTorchState, toggleTorch, TORCH_OFF, TORCH_ON } from '../../server/field-tools/torch.js';

// ── TORCH STATE MACHINE ────────────────────────────────────────────

describe('Feature 7: Taschenlampe — TorchState Machine', () => {

  // GIVEN eine frische Torch-State
  // WHEN createTorchState aufgerufen wird
  // THEN ist der Status OFF
  it('[D] GIVEN new state WHEN created THEN status is OFF', () => {
    const state = createTorchState();
    expect(state.status).toBe(TORCH_OFF);
    expect(state.wakeLockActive).toBe(false);
  });

  // GIVEN Torch ist OFF
  // WHEN toggleTorch aufgerufen wird
  // THEN wechselt Status zu ON
  it('[D] GIVEN torch is OFF WHEN toggle THEN status becomes ON', () => {
    const state = createTorchState();
    const next = toggleTorch(state);
    expect(next.status).toBe(TORCH_ON);
  });

  // GIVEN Torch ist ON
  // WHEN toggleTorch aufgerufen wird
  // THEN wechselt Status zurück zu OFF
  it('[D] GIVEN torch is ON WHEN toggle again THEN status becomes OFF', () => {
    const state = createTorchState();
    const on = toggleTorch(state);
    const off = toggleTorch(on);
    expect(off.status).toBe(TORCH_OFF);
  });

  // GIVEN Torch wechselt zu ON
  // WHEN Status geprüft wird
  // THEN wakeLockRequired ist true
  it('[D] GIVEN torch ON WHEN status checked THEN wakeLockRequired is true', () => {
    const state = createTorchState();
    const on = toggleTorch(state);
    expect(on.wakeLockRequired).toBe(true);
  });

  // GIVEN Torch wechselt zu OFF
  // WHEN Status geprüft wird
  // THEN wakeLockRequired ist false
  it('[D] GIVEN torch OFF WHEN toggled off THEN wakeLockRequired is false', () => {
    const state = createTorchState();
    const on = toggleTorch(state);
    const off = toggleTorch(on);
    expect(off.wakeLockRequired).toBe(false);
  });

  // GIVEN Torch ist ON
  // WHEN getCssClass aufgerufen wird
  // THEN gibt 'torch-active' zurück
  it('[D] GIVEN torch ON WHEN getCssClass THEN returns torch-active', () => {
    const state = createTorchState();
    const on = toggleTorch(state);
    expect(on.cssClass).toBe('torch-active');
  });

  // GIVEN Torch ist OFF
  // WHEN getCssClass aufgerufen wird
  // THEN gibt '' zurück
  it('[D] GIVEN torch OFF WHEN getCssClass THEN returns empty', () => {
    const state = createTorchState();
    expect(state.cssClass).toBe('');
  });
});
