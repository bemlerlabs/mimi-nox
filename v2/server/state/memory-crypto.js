/**
 * ◑ MiMiNox — Memory Encryption
 * server/state/memory-crypto.js
 *
 * AES-256-GCM field-level encryption for personal health data.
 * Uses Node.js built-in `crypto` — zero extra dependencies.
 *
 * Security properties:
 *   - AES-256-GCM: authenticated encryption (integrity + confidentiality)
 *   - Per-value random IV (12 bytes): same value → different ciphertext
 *   - PBKDF2 key derivation (100,000 iterations, SHA-256)
 *   - Auth tag (16 bytes): tamper detection
 *
 * Key source: MIMINOX_MEMORY_KEY env var, falling back to a machine-
 * derived default. For production, always set MIMINOX_MEMORY_KEY.
 *
 * Storage format (compact JSON): {"iv":"<hex>","tag":"<hex>","ct":"<hex>"}
 * System keys (prefixed __) are stored in plaintext — they are non-sensitive
 * metadata (e.g., __country__, __profile__) that the frontend needs to read.
 */

import { createCipheriv, createDecipheriv, pbkdf2Sync, randomBytes } from 'crypto';
import { hostname, platform } from 'os';

// ── Key Derivation ──────────────────────────────────────────────

const ALGORITHM  = 'aes-256-gcm';
const IV_BYTES   = 12;
const TAG_BYTES  = 16;
const ITERATIONS = 100_000;
const DIGEST     = 'sha256';
const SALT       = 'miminox-memory-v1'; // Fixed salt — OK for field-level encryption

/**
 * Derive a 256-bit key from the configured passphrase.
 * Cached after first derivation.
 */
let _cachedKey = null;

function getDerivedKey() {
  if (_cachedKey) return _cachedKey;

  // Priority: explicit env var → machine fingerprint fallback
  const passphrase =
    process.env.MIMINOX_MEMORY_KEY ||
    `miminox-${hostname()}-${platform()}-local-v1`;

  if (!process.env.MIMINOX_MEMORY_KEY) {
    console.warn(
      '⚠️  MIMINOX_MEMORY_KEY nicht gesetzt — Machine-Fingerprint als Fallback.\n' +
      '   Für volle Sicherheit: export MIMINOX_MEMORY_KEY="<starkes-passwort>"'
    );
  }

  _cachedKey = pbkdf2Sync(passphrase, SALT, ITERATIONS, 32, DIGEST);
  return _cachedKey;
}

// ── Encryption ──────────────────────────────────────────────────

/**
 * Encrypt a plaintext string.
 * @param {string} plaintext
 * @returns {string} JSON envelope: {"iv":"...","tag":"...","ct":"..."}
 */
export function encryptField(plaintext) {
  const key    = getDerivedKey();
  const iv     = randomBytes(IV_BYTES);
  const cipher = createCipheriv(ALGORITHM, key, iv);

  const ct = Buffer.concat([
    cipher.update(plaintext, 'utf8'),
    cipher.final(),
  ]);
  const tag = cipher.getAuthTag();

  return JSON.stringify({
    iv:  iv.toString('hex'),
    tag: tag.toString('hex'),
    ct:  ct.toString('hex'),
  });
}

// ── Decryption ──────────────────────────────────────────────────

/**
 * Decrypt a value produced by encryptField().
 * Returns the original plaintext, or throws on corruption/tampering.
 * @param {string} envelope  JSON string from encryptField()
 * @returns {string}
 */
export function decryptField(envelope) {
  const { iv, tag, ct } = JSON.parse(envelope);
  const key             = getDerivedKey();
  const decipher        = createDecipheriv(ALGORITHM, key, Buffer.from(iv, 'hex'));
  decipher.setAuthTag(Buffer.from(tag, 'hex'));

  return decipher.update(Buffer.from(ct, 'hex'), undefined, 'utf8')
    + decipher.final('utf8');
}

// ── Helpers ─────────────────────────────────────────────────────

/**
 * Returns true if the value is an encrypted envelope.
 * Allows safe mixed migration (unencrypted legacy values pass through).
 * @param {string} value
 * @returns {boolean}
 */
export function isEncrypted(value) {
  if (typeof value !== 'string' || !value.startsWith('{')) return false;
  try {
    const parsed = JSON.parse(value);
    return !!(parsed.iv && parsed.tag && parsed.ct);
  } catch {
    return false;
  }
}

/**
 * Safe decrypt: if value is already plaintext (legacy / system key),
 * return as-is. Only decrypt actual encrypted envelopes.
 * @param {string} value
 * @returns {string}
 */
export function safeDecrypt(value) {
  if (!isEncrypted(value)) return value;
  try {
    return decryptField(value);
  } catch {
    // Tampered or wrong key — return placeholder
    return '[verschlüsselt — falscher Schlüssel]';
  }
}

/**
 * System keys (prefixed __) are internal metadata — not encrypted.
 * User-facing personal facts ARE encrypted.
 * @param {string} key
 * @returns {boolean}
 */
export function shouldEncrypt(key) {
  return !key.startsWith('__');
}
