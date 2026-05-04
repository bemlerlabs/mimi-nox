/**
 * ◑ MiMiNox Field-Tools — Voice Memo Store
 * server/field-tools/voice-memo.js
 *
 * Immutable State Machine für Sprach-Notizen.
 * Die UI nutzt MediaRecorder API (HTTPS nötig).
 * Hier: reine Datenverwaltung (CRUD + Sortierung).
 *
 * Kein DOM, kein Browser-API — testbar mit Vitest.
 */

export const RECORDER_STATE = {
  IDLE:      'idle',
  RECORDING: 'recording',
  STOPPED:   'stopped',
};

/**
 * Erstellt einen leeren Voice-Memo-Store.
 * @returns {VoiceMemoStore}
 */
export function createVoiceMemoStore() {
  return {
    memos:         [],
    recorderState: RECORDER_STATE.IDLE,
  };
}

/**
 * Fügt eine Memo hinzu oder aktualisiert sie (Upsert nach ID).
 * Immutable — gibt neuen Store zurück.
 *
 * @param {VoiceMemoStore} store
 * @param {VoiceMemo} memo
 * @returns {VoiceMemoStore}
 */
export function addMemo(store, memo) {
  const existing = store.memos.findIndex(m => m.id === memo.id);
  let memos;
  if (existing >= 0) {
    // Upsert: bestehende ersetzen
    memos = store.memos.map(m => m.id === memo.id ? { ...memo } : m);
  } else {
    memos = [...store.memos, { ...memo }];
  }
  return { ...store, memos };
}

/**
 * Löscht eine Memo nach ID (immutable).
 * @param {VoiceMemoStore} store
 * @param {string} id
 * @returns {VoiceMemoStore}
 */
export function deleteMemo(store, id) {
  return {
    ...store,
    memos: store.memos.filter(m => m.id !== id),
  };
}

/**
 * Gibt eine Memo nach ID zurück.
 * @param {VoiceMemoStore} store
 * @param {string} id
 * @returns {VoiceMemo|undefined}
 */
export function getMemo(store, id) {
  return store.memos.find(m => m.id === id);
}

/**
 * Gibt alle Memos zurück, sortiert nach createdAt (neueste zuerst).
 * @param {VoiceMemoStore} store
 * @returns {VoiceMemo[]}
 */
export function getAllMemos(store) {
  return [...store.memos].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );
}
