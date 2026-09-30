import { az } from "./locales/az";
import { en } from "./locales/en";
import { ru } from "./locales/ru";
import {
  SUPPORTED_LOCALES,
  type Locale,
  type TranslationDictionary,
} from "./types";

export const translations = {
  en,
  az,
  ru,
} satisfies Record<Locale, TranslationDictionary>;

export const LOCALE_OPTIONS: readonly {
  value: Locale;
  label: string;
  shortLabel: string;
}[] = [
  { value: "en", label: "English", shortLabel: "EN" },
  { value: "az", label: "Azərbaycanca", shortLabel: "AZ" },
  { value: "ru", label: "Русский", shortLabel: "RU" },
];

export function isLocale(value: unknown): value is Locale {
  return (
    typeof value === "string" &&
    (SUPPORTED_LOCALES as readonly string[]).includes(value)
  );
}

export function normalizeLocale(value: string | null | undefined): Locale | null {
  if (!value) return null;
  const language = value.trim().toLowerCase().split(/[-_]/, 1)[0];
  return isLocale(language) ? language : null;
}

