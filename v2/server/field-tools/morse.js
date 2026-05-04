/**
 * ◑ MiMiNox Field-Tools — SOS Morse Encoder + Timeline Builder
 * server/field-tools/morse.js
 *
 * Internationaler Morsecode (ITU-R M.1677-1).
 * Timing:
 *   dit  = 1 unit (100ms)
 *   dah  = 3 units (300ms)
 *   Pause zwischen Symbolen = 1 unit (100ms)
 *   Pause zwischen Buchstaben = 3 units (300ms)
 *   Pause zwischen Wörtern = 7 units (700ms)
 */

export const MORSE_DIT_MS  = 100;
export const MORSE_DAH_MS  = 300;
const SYMBOL_GAP_MS   = 100;  // Pause zwischen dit/dah
const LETTER_GAP_MS   = 300;  // Pause zwischen Buchstaben
const WORD_GAP_MS     = 700;  // Pause zwischen Wörtern

export const MORSE_MAP = {
  'A': '.-',    'B': '-...',  'C': '-.-.',  'D': '-..',
  'E': '.',     'F': '..-.',  'G': '--.',   'H': '....',
  'I': '..',    'J': '.---',  'K': '-.-',   'L': '.-..',
  'M': '--',    'N': '-.',    'O': '---',   'P': '.--.',
  'Q': '--.-',  'R': '.-.',   'S': '...',   'T': '-',
  'U': '..-',   'V': '...-',  'W': '.--',   'X': '-..-',
  'Y': '-.--',  'Z': '--..',
  '0': '-----', '1': '.----', '2': '..---', '3': '...--',
  '4': '....-', '5': '.....', '6': '-....', '7': '--...',
  '8': '---..', '9': '----.',
  '.': '.-.-.-',',' : '--..--','?': '..--..','!': '-.-.--',
  '/': '-..-.',  '-': '-....-','(': '-.--.',  ')': '-.--.-',
  '&': '.-...',  ':': '---...','=': '-...-',  '+': '.-.-.',
  '@': '.--.-.',
};

/**
 * Encodiert einen Text als Morse-String.
 * Ungültige Zeichen werden übersprungen.
 *
 * @param {string} text
 * @returns {string} z.B. "... --- ..."
 */
export function encodeMorse(text) {
  return text
    .toUpperCase()
    .split('')
    .reduce((parts, char) => {
      if (char === ' ') {
        parts.push('');          // Leerzeichen → Wort-Trenner
      } else if (MORSE_MAP[char]) {
        parts.push(MORSE_MAP[char]);
      }
      // Ungültige Zeichen → ignorieren
      return parts;
    }, [])
    .filter(Boolean)
    .join(' ');
}

/**
 * Baut eine Timeline für Audio/Screen-Flasher.
 * Jeder Eintrag: { type: 'ON'|'OFF', durationMs: number }
 *
 * @param {string} text
 * @returns {Array<{ type: 'ON'|'OFF', durationMs: number }>}
 */
export function buildMorseTimeline(text) {
  const timeline = [];
  const words = text.toUpperCase().trim().split(/\s+/);

  words.forEach((word, wordIdx) => {
    const chars = word.split('');

    chars.forEach((char, charIdx) => {
      const code = MORSE_MAP[char];
      if (!code) return;

      const symbols = code.split('');
      symbols.forEach((sym, symIdx) => {
        // Symbol ON
        timeline.push({
          type:       'ON',
          durationMs: sym === '.' ? MORSE_DIT_MS : MORSE_DAH_MS,
        });
        // Pause nach Symbol (außer letztem in Buchstabe)
        if (symIdx < symbols.length - 1) {
          timeline.push({ type: 'OFF', durationMs: SYMBOL_GAP_MS });
        }
      });

      // Pause nach Buchstabe (außer letztem im Wort)
      if (charIdx < chars.filter(c => MORSE_MAP[c]).length - 1) {
        timeline.push({ type: 'OFF', durationMs: LETTER_GAP_MS });
      }
    });

    // Pause nach Wort (außer letztem)
    if (wordIdx < words.length - 1) {
      timeline.push({ type: 'OFF', durationMs: WORD_GAP_MS });
    }
  });

  return timeline;
}
