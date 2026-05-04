/**
 * ◑ MiMiNox Field-Tools — Test: Sprach-Notiz (Voice Memo)
 * Feature 4: Offline Sprachnotizen aufnehmen und speichern
 *
 * TDD: Tests FIRST.
 *
 * MediaRecorder API — funktioniert offline.
 * Notizen werden in IndexedDB gespeichert (lokal, persistiert).
 *
 * Hier testen wir: State Machine + Memo-Verwaltung (keine Browser-APIs)
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  createVoiceMemoStore,
  addMemo,
  deleteMemo,
  getMemo,
  getAllMemos,
  RECORDER_STATE,
} from '../../server/field-tools/voice-memo.js';

const NOW = new Date('2026-04-21T15:00:00Z');

describe('Feature 4: Sprach-Notiz Store', () => {

  let store;
  beforeEach(() => {
    store = createVoiceMemoStore();
  });

  // GIVEN neuer Store
  // WHEN createVoiceMemoStore aufgerufen
  // THEN leer, status IDLE
  it('[D] GIVEN new store WHEN created THEN empty and IDLE', () => {
    expect(store.memos).toHaveLength(0);
    expect(store.recorderState).toBe(RECORDER_STATE.IDLE);
  });

  // GIVEN leerer Store + neue Memo
  // WHEN addMemo aufgerufen
  // THEN Store hat 1 Memo
  it('[D] GIVEN empty store WHEN addMemo THEN 1 memo', () => {
    const memo = { id: 'memo-1', title: 'Verletzungsprotokoll', durationSec: 30, blob: null, createdAt: NOW };
    const next = addMemo(store, memo);
    expect(next.memos).toHaveLength(1);
    expect(next.memos[0].title).toBe('Verletzungsprotokoll');
  });

  // GIVEN Store mit 2 Memos
  // WHEN getMemo mit ID aufgerufen
  // THEN gibt korrekte Memo zurück
  it('[D] GIVEN 2 memos WHEN getMemo by id THEN returns correct memo', () => {
    const m1 = { id: 'memo-1', title: 'A', durationSec: 10, blob: null, createdAt: NOW };
    const m2 = { id: 'memo-2', title: 'B', durationSec: 20, blob: null, createdAt: NOW };
    const s = addMemo(addMemo(store, m1), m2);
    const found = getMemo(s, 'memo-2');
    expect(found.title).toBe('B');
  });

  // GIVEN Store mit Memo
  // WHEN getMemo mit unbekannter ID
  // THEN gibt undefined zurück
  it('[D] GIVEN memo store WHEN getMemo unknown id THEN undefined', () => {
    const m = { id: 'memo-1', title: 'A', durationSec: 10, blob: null, createdAt: NOW };
    const s = addMemo(store, m);
    expect(getMemo(s, 'nonexistent')).toBeUndefined();
  });

  // GIVEN Store mit 3 Memos
  // WHEN deleteMemo aufgerufen
  // THEN Store hat 2 Memos
  it('[D] GIVEN 3 memos WHEN deleteMemo THEN 2 memos remain', () => {
    const memos = [
      { id: 'a', title: 'A', durationSec: 5,  blob: null, createdAt: NOW },
      { id: 'b', title: 'B', durationSec: 10, blob: null, createdAt: NOW },
      { id: 'c', title: 'C', durationSec: 15, blob: null, createdAt: NOW },
    ];
    const s = memos.reduce(addMemo, store);
    const after = deleteMemo(s, 'b');
    expect(after.memos).toHaveLength(2);
    expect(after.memos.find(m => m.id === 'b')).toBeUndefined();
  });

  // GIVEN Store mit Memos
  // WHEN getAllMemos aufgerufen
  // THEN gibt alle Memos sortiert nach createdAt (neueste zuerst)
  it('[D] GIVEN memos WHEN getAllMemos THEN sorted newest first', () => {
    const m1 = { id: 'a', title: 'Alt',  durationSec: 5,  blob: null, createdAt: new Date('2026-04-21T10:00:00Z') };
    const m2 = { id: 'b', title: 'Neu',  durationSec: 10, blob: null, createdAt: new Date('2026-04-21T12:00:00Z') };
    const s = addMemo(addMemo(store, m1), m2);
    const all = getAllMemos(s);
    expect(all[0].title).toBe('Neu');  // neueste zuerst
    expect(all[1].title).toBe('Alt');
  });

  // GIVEN RECORDER_STATE enum
  // THEN enthält IDLE, RECORDING, STOPPED
  it('[D] GIVEN RECORDER_STATE THEN has IDLE, RECORDING, STOPPED', () => {
    expect(RECORDER_STATE.IDLE).toBeDefined();
    expect(RECORDER_STATE.RECORDING).toBeDefined();
    expect(RECORDER_STATE.STOPPED).toBeDefined();
  });

  // GIVEN Store mit Memo ID 'memo-1'
  // WHEN nochmal addMemo mit gleicher ID
  // THEN Memo wird überschrieben (Upsert)
  it('[D] GIVEN existing id WHEN addMemo again THEN upsert replaces memo', () => {
    const m1 = { id: 'memo-1', title: 'Alt',  durationSec: 5,  blob: null, createdAt: NOW };
    const m2 = { id: 'memo-1', title: 'Neu', durationSec: 10, blob: null, createdAt: NOW };
    const s = addMemo(addMemo(store, m1), m2);
    expect(s.memos).toHaveLength(1);
    expect(s.memos[0].title).toBe('Neu');
  });
});
