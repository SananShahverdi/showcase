import type { Locale } from "./types";

/**
 * Soft-hyphenation for display headings.
 *
 * Browsers ship hyphenation dictionaries for English but usually not for
 * Azerbaijani, and not reliably for Russian. Long agglutinative words
 * ("işıqlandırılması") are wider than a heading column at display sizes, so
 * without help they are cut at an arbitrary letter. This inserts U+00AD soft
 * hyphens at syllable boundaries: the browser breaks there only when a word
 * does not fit, and then shows a visible hyphen.
 *
 * Syllable rule shared by Azerbaijani and Russian: a single consonant between
 * vowels starts the next syllable (V-CV); with two or more consonants, the
 * last one starts it (VC-CV, VCC-CV). Russian ь, ъ and й never begin a
 * syllable. At least three letters stay on each side of a break.
 */

const SOFT_HYPHEN = "­";
const VOWELS: Record<Exclude<Locale, "en">, string> = {
  az: "aeəıioöuüAEƏIİOÖUÜ",
  ru: "аеёиоуыэюяАЕЁИОУЫЭЮЯ",
};
const NEVER_STARTS = "ьъйЬЪЙ";
const MIN_WORD = 8;
const MIN_EDGE = 3;

function hyphenateWord(word: string, vowels: string): string {
  const letters = [...word];
  if (letters.length < MIN_WORD) return word;
  const isVowel = (ch: string) => vowels.includes(ch);
  const isLetter = (ch: string) => /\p{L}/u.test(ch);
  const breaks = new Set<number>();
  let previousVowel = -1;
  letters.forEach((ch, index) => {
    if (!isVowel(ch)) return;
    if (previousVowel >= 0) {
      const between = letters.slice(previousVowel + 1, index);
      if (between.length > 0 && between.every(isLetter)) {
        // The last consonant starts the next syllable, unless it is ь/ъ/й,
        // in which case the break moves after it.
        const at = NEVER_STARTS.includes(letters[index - 1]) ? index : index - 1;
        if (at >= MIN_EDGE && letters.length - at >= MIN_EDGE) breaks.add(at);
      }
    }
    previousVowel = index;
  });
  return letters.map((ch, index) => (breaks.has(index) ? SOFT_HYPHEN + ch : ch)).join("");
}

export function hyphenate(text: string, locale: Locale): string {
  if (locale === "en") return text;
  const vowels = VOWELS[locale];
  return text.replace(/\p{L}+/gu, (word) => hyphenateWord(word, vowels));
}
