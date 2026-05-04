/**
 * ◑ MiMiNox Field-Tools — Test: LAN-Chat
 * Feature 2: Lokaler Chat über Socket.io im selben WLAN (ohne Internet)
 *
 * TDD: Tests FIRST.
 *
 * Architektur:
 *  - MiMiNox-Server (läuft schon) = Signaling-Server via Socket.io
 *  - Clients verbinden sich über QR-Code zur selben LAN-IP
 *  - Nachrichten: Text + GPS-Koordinaten teilen
 *  - Kein Internet nötig: alles läuft lokal
 *
 * Hier testen wir: Message-Store + Chat-Room-State (keine Browser-APIs)
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  createChatRoom,
  addMessage,
  addParticipant,
  removeParticipant,
  getMessages,
  clearMessages,
  buildMessage,
  MSG_TYPE,
} from '../../server/field-tools/lan-chat.js';

const NOW = new Date('2026-04-21T16:00:00Z');

describe('Feature 2: LAN-Chat — Message Store + Room State', () => {

  let room;
  beforeEach(() => {
    room = createChatRoom({ name: 'Bergtour 2026', hostId: 'host-1' });
  });

  // GIVEN neuer Room
  // WHEN createChatRoom aufgerufen
  // THEN leer, kein Teilnehmer, kein Nachrichten
  it('[D] GIVEN new room WHEN created THEN empty', () => {
    expect(room.messages).toHaveLength(0);
    expect(room.participants).toHaveLength(0);
    expect(room.name).toBe('Bergtour 2026');
    expect(room.hostId).toBe('host-1');
  });

  // GIVEN leerer Room + Teilnehmer
  // WHEN addParticipant aufgerufen
  // THEN Room hat 1 Teilnehmer
  it('[D] GIVEN empty room WHEN addParticipant THEN 1 participant', () => {
    const p = { id: 'peer-1', name: 'Alice', joinedAt: NOW };
    const next = addParticipant(room, p);
    expect(next.participants).toHaveLength(1);
    expect(next.participants[0].name).toBe('Alice');
  });

  // GIVEN Room mit 2 Teilnehmern
  // WHEN removeParticipant aufgerufen
  // THEN 1 Teilnehmer übrig
  it('[D] GIVEN 2 participants WHEN removeParticipant THEN 1 remains', () => {
    const r = addParticipant(
      addParticipant(room, { id: 'p1', name: 'Alice', joinedAt: NOW }),
                           { id: 'p2', name: 'Bob',   joinedAt: NOW }
    );
    const after = removeParticipant(r, 'p1');
    expect(after.participants).toHaveLength(1);
    expect(after.participants[0].name).toBe('Bob');
  });

  // GIVEN Room + Nachricht
  // WHEN addMessage aufgerufen
  // THEN Room hat 1 Nachricht
  it('[D] GIVEN room WHEN addMessage THEN 1 message', () => {
    const msg = buildMessage({ senderId: 'p1', senderName: 'Alice', text: 'Hallo!', type: MSG_TYPE.TEXT, timestamp: NOW });
    const next = addMessage(room, msg);
    expect(next.messages).toHaveLength(1);
    expect(next.messages[0].text).toBe('Hallo!');
  });

  // GIVEN Room mit Nachrichten
  // WHEN getMessages aufgerufen
  // THEN sortiert nach timestamp (älteste zuerst)
  it('[D] GIVEN messages WHEN getMessages THEN sorted oldest first', () => {
    const m1 = buildMessage({ senderId: 'p1', senderName: 'A', text: 'Erste',  type: MSG_TYPE.TEXT, timestamp: new Date('2026-04-21T10:00:00Z') });
    const m2 = buildMessage({ senderId: 'p1', senderName: 'A', text: 'Zweite', type: MSG_TYPE.TEXT, timestamp: new Date('2026-04-21T11:00:00Z') });
    const r = addMessage(addMessage(room, m2), m1); // falsche Reihenfolge absichtlich
    const msgs = getMessages(r);
    expect(msgs[0].text).toBe('Erste');
    expect(msgs[1].text).toBe('Zweite');
  });

  // GIVEN Room mit Nachrichten
  // WHEN clearMessages aufgerufen
  // THEN keine Nachrichten mehr
  it('[D] GIVEN messages WHEN clearMessages THEN empty', () => {
    const msg = buildMessage({ senderId: 'p1', senderName: 'A', text: 'Test', type: MSG_TYPE.TEXT, timestamp: NOW });
    const r = clearMessages(addMessage(room, msg));
    expect(r.messages).toHaveLength(0);
  });

  // GIVEN buildMessage mit GPS-Koordinaten
  // WHEN aufgerufen mit type = GPS
  // THEN Nachricht hat coords und type GPS
  it('[D] GIVEN GPS coords WHEN buildMessage GPS THEN has coords', () => {
    const msg = buildMessage({
      senderId: 'p1', senderName: 'Alice',
      text: 'Mein Standort',
      type: MSG_TYPE.GPS,
      coords: { lat: 48.137, lng: 11.576 },
      timestamp: NOW,
    });
    expect(msg.type).toBe(MSG_TYPE.GPS);
    expect(msg.coords.lat).toBe(48.137);
  });

  // GIVEN MSG_TYPE enum
  // THEN enthält TEXT, GPS, SYSTEM
  it('[D] GIVEN MSG_TYPE THEN has TEXT, GPS, SYSTEM', () => {
    expect(MSG_TYPE.TEXT).toBeDefined();
    expect(MSG_TYPE.GPS).toBeDefined();
    expect(MSG_TYPE.SYSTEM).toBeDefined();
  });

  // GIVEN buildMessage
  // WHEN aufgerufen
  // THEN Nachricht hat id (UUID-ähnlich) und timestamp
  it('[D] GIVEN buildMessage WHEN called THEN has id and timestamp', () => {
    const msg = buildMessage({ senderId: 'p1', senderName: 'A', text: 'Test', type: MSG_TYPE.TEXT, timestamp: NOW });
    expect(msg.id).toBeDefined();
    expect(msg.id.length).toBeGreaterThan(0);
    expect(msg.timestamp).toBeInstanceOf(Date);
  });

  // GIVEN Room mit 200 Nachrichten (Limit)
  // WHEN addMessage aufgerufen
  // THEN älteste Nachricht wird entfernt (FIFO, max 200)
  it('[D] GIVEN 200 messages WHEN addMessage THEN oldest removed', () => {
    let r = room;
    for (let i = 0; i < 200; i++) {
      const msg = buildMessage({ senderId: 'p1', senderName: 'A', text: `Msg ${i}`, type: MSG_TYPE.TEXT, timestamp: new Date(NOW.getTime() + i * 1000) });
      r = addMessage(r, msg);
    }
    expect(r.messages).toHaveLength(200);
    const newMsg = buildMessage({ senderId: 'p1', senderName: 'A', text: 'Neue', type: MSG_TYPE.TEXT, timestamp: new Date(NOW.getTime() + 200000) });
    const after = addMessage(r, newMsg);
    expect(after.messages).toHaveLength(200);
    expect(after.messages[0].text).toBe('Msg 1'); // Msg 0 wurde entfernt
  });
});
