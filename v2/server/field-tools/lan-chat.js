/**
 * ◑ MiMiNox Field-Tools — LAN-Chat
 * server/field-tools/lan-chat.js
 *
 * Immutable State Machine für lokalen Chat (ohne Internet).
 * Signaling-Server: MiMiNox-Server (Socket.io, läuft schon).
 * Clients: Alle Geräte im selben WLAN via QR-Code verbunden.
 *
 * Features:
 *  - Text-Nachrichten
 *  - GPS-Koordinaten teilen (MSG_TYPE.GPS)
 *  - System-Meldungen (join/leave)
 *  - FIFO bei 200 Nachrichten (Speicherschutz)
 *
 * Kein DOM, kein Socket.io — reine Logik, testbar mit Vitest.
 */

export const MSG_TYPE = {
  TEXT:   'text',
  GPS:    'gps',
  SYSTEM: 'system',
};

const MSG_MAX = 200;

/**
 * Erstellt einen neuen Chat-Room.
 * @param {{ name: string, hostId: string }} opts
 * @returns {ChatRoom}
 */
export function createChatRoom(opts = {}) {
  return {
    name:         opts.name   ?? 'MiMiNox Chat',
    hostId:       opts.hostId ?? null,
    participants: [],
    messages:     [],
    createdAt:    new Date(),
  };
}

/**
 * Baut eine neue Nachricht (immutable, mit automatischer ID).
 *
 * @param {{ senderId, senderName, text, type, coords?, timestamp }} opts
 * @returns {ChatMessage}
 */
export function buildMessage(opts) {
  return {
    id:         generateId(),
    senderId:   opts.senderId,
    senderName: opts.senderName,
    text:       opts.text ?? '',
    type:       opts.type ?? MSG_TYPE.TEXT,
    coords:     opts.coords ?? null,
    timestamp:  opts.timestamp instanceof Date ? opts.timestamp : new Date(opts.timestamp),
  };
}

/**
 * Fügt eine Nachricht hinzu. Bei 200+ Nachrichten wird die älteste entfernt.
 *
 * @param {ChatRoom} room
 * @param {ChatMessage} msg
 * @returns {ChatRoom}
 */
export function addMessage(room, msg) {
  let messages = [...room.messages, msg];
  if (messages.length > MSG_MAX) {
    // Älteste entfernen (FIFO)
    messages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    messages = messages.slice(1);
  }
  return { ...room, messages };
}

/**
 * Gibt alle Nachrichten sortiert nach timestamp (älteste zuerst) zurück.
 * @param {ChatRoom} room
 * @returns {ChatMessage[]}
 */
export function getMessages(room) {
  return [...room.messages].sort(
    (a, b) => new Date(a.timestamp) - new Date(b.timestamp)
  );
}

/**
 * Löscht alle Nachrichten (immutable).
 * @param {ChatRoom} room
 * @returns {ChatRoom}
 */
export function clearMessages(room) {
  return { ...room, messages: [] };
}

/**
 * Fügt einen Teilnehmer hinzu (immutable). Upsert nach id.
 * @param {ChatRoom} room
 * @param {{ id, name, joinedAt }} participant
 * @returns {ChatRoom}
 */
export function addParticipant(room, participant) {
  const existing = room.participants.findIndex(p => p.id === participant.id);
  const participants = existing >= 0
    ? room.participants.map(p => p.id === participant.id ? { ...participant } : p)
    : [...room.participants, { ...participant }];
  return { ...room, participants };
}

/**
 * Entfernt einen Teilnehmer nach ID (immutable).
 * @param {ChatRoom} room
 * @param {string} id
 * @returns {ChatRoom}
 */
export function removeParticipant(room, id) {
  return {
    ...room,
    participants: room.participants.filter(p => p.id !== id),
  };
}

/** Erzeugt eine kurze pseudozufällige ID. */
function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}
