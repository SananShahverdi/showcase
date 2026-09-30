import {
  LOCALE_OPTIONS,
  isLocale,
  useI18n,
} from "../i18n";

export function LanguageSwitcher() {
  const { locale, setLocale, copy } = useI18n();

  return (
    <label className="language-switcher">
      <span className="sr-only">{copy.localeSwitcher.label}</span>
      <select
        value={locale}
        aria-label={copy.localeSwitcher.ariaLabel}
        title={copy.localeSwitcher.label}
        onChange={(event) => {
          if (isLocale(event.target.value)) {
            setLocale(event.target.value);
          }
        }}
      >
        {LOCALE_OPTIONS.map((option) => (
          <option
            value={option.value}
            aria-label={option.label}
            key={option.value}
          >
            {option.shortLabel}
          </option>
        ))}
      </select>
    </label>
  );
}
