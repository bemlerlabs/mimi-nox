/**
 * ◑ MiMiNox Field-Tools — Torch State Machine
 * server/field-tools/torch.js
 *
 * Pure state machine — kein DOM, kein Browser-API.
 * Die UI-Komponente (TorchPanel.jsx) nutzt diese Funktionen.
 * Testbar mit Vitest ohne Browser.
 */

export const TORCH_OFF = 'off';
export const TORCH_ON  = 'on';

/**
 * Erstellt einen frischen Torch-State (OFF).
 * @returns {TorchState}
 */
export function createTorchState() {
  return {
    status:          TORCH_OFF,
    wakeLockActive:  false,
    wakeLockRequired: false,
    cssClass:        '',
  };
}

/**
 * Wechselt den Torch-Status (Toggle).
 * Immutable — gibt neuen State zurück.
 * @param {TorchState} state
 * @returns {TorchState}
 */
export function toggleTorch(state) {
  if (state.status === TORCH_OFF) {
    return {
      status:           TORCH_ON,
      wakeLockActive:   false,    // wird in UI über WakeLock API gesetzt
      wakeLockRequired: true,
      cssClass:         'torch-active',
    };
  }
  return {
    status:           TORCH_OFF,
    wakeLockActive:   false,
    wakeLockRequired: false,
    cssClass:         '',
  };
}
