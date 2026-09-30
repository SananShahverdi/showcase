import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";
import { normalizeLocale, translations } from "./translations";
import type {
  I18nFormatters,
  Locale,
  TranslationDictionary,
} from "./types";
import { hyphenate } from "./hyphenate";

export const LOCALE_STORAGE_KEY = "effekt-locale";

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  copy: TranslationDictionary;
  format: I18nFormatters;
  /** Heading text with soft hyphens where the locale needs them. */
  display: (text: string) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

function storedLocale(): Locale | null {
  if (typeof window === "undefined") return null;

  try {
    return normalizeLocale(window.localStorage.getItem(LOCALE_STORAGE_KEY));
  } catch {
    return null;
  }
}

function browserLocale(): Locale {
  if (typeof navigator === "undefined") return "en";

  const candidates =
    navigator.languages?.length > 0
      ? navigator.languages
      : navigator.language
        ? [navigator.language]
        : [];

  for (const candidate of candidates) {
    const locale = normalizeLocale(candidate);
    if (locale) return locale;
  }

  return "en";
}

export function resolveInitialLocale(): Locale {
  return storedLocale() ?? browserLocale();
}

function interpolate(
  template: string,
  values: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    Object.hasOwn(values, key) ? String(values[key]) : match,
  );
}

function createFormatters(copy: TranslationDictionary): I18nFormatters {
  return {
    openGallery: (title) =>
      interpolate(copy.a11y.openGallery, { title }),
    openImage: (index, title) =>
      interpolate(copy.a11y.openImage, { index, title }),
    offerings: (title) =>
      interpolate(copy.a11y.offerings, { title }),
    interactionDiscipline: (label) =>
      interpolate(copy.water.interactionDiscipline, { label }),
    viewGallery: (count) =>
      interpolate(copy.gallery.viewGallery, { count }),
    copyright: (year) =>
      interpolate(copy.footer.copyright, { year }),
  };
}

export type I18nProviderProps = PropsWithChildren<{
  initialLocale?: Locale;
}>;

export function I18nProvider({
  children,
  initialLocale,
}: I18nProviderProps) {
  const [locale, setLocaleState] = useState<Locale>(
    () => initialLocale ?? resolveInitialLocale(),
  );
  const copy = translations[locale];

  const setLocale = useCallback((nextLocale: Locale) => {
    setLocaleState(nextLocale);
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    } catch {
      // Storage can be blocked or unavailable in privacy-restricted contexts.
    }
  }, [locale]);

  useEffect(() => {
    const root = document.documentElement;
    root.lang = locale;
    root.dir = "ltr";
    root.dataset.locale = locale;
    document.title = copy.meta.title;

    let description = document.querySelector<HTMLMetaElement>(
      'meta[name="description"]',
    );
    if (!description) {
      description = document.createElement("meta");
      description.name = "description";
      document.head.append(description);
    }
    description.content = copy.meta.description;
  }, [copy, locale]);

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      setLocale,
      copy,
      format: createFormatters(copy),
      display: (text: string) => hyphenate(text, locale),
    }),
    [copy, locale, setLocale],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const value = useContext(I18nContext);

  if (!value) {
    throw new Error("useI18n must be used inside an I18nProvider.");
  }

  return value;
}

