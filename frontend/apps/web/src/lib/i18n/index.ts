/**
 * i18n bootstrap. EN-only for now; AR + RTL hookup is a future task.
 *
 * Usage anywhere in the app:
 *   import { useTranslation } from "react-i18next";
 *   const { t } = useTranslation();
 *   t("common.signIn"); // → "Sign in"
 *
 * Keep keys nested by feature (see `en.ts`). When adding a new language:
 *   1. Create `ar.ts` matching the shape of `en.ts`
 *   2. Add it to `resources` below
 *   3. Wire `dir="rtl"` on <html> when language is RTL
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import { en } from "./en";

const STORAGE_KEY = "sc-language";

const RTL_LANGUAGES = new Set<string>(["ar", "he", "fa", "ur"]);

function detectInitialLanguage(): string {
  if (typeof window === "undefined") return "en";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored) return stored;
  const browser = window.navigator.language?.split("-")[0];
  return browser ?? "en";
}

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    // ar: { translation: ar }, // wire when ready
  },
  lng: detectInitialLanguage(),
  fallbackLng: "en",
  interpolation: { escapeValue: false }, // React already escapes
  returnNull: false,
});

// Reflect direction on <html dir="..."> when the language switches.
if (typeof window !== "undefined") {
  const applyDir = (lang: string) => {
    const dir = RTL_LANGUAGES.has(lang) ? "rtl" : "ltr";
    document.documentElement.dir = dir;
  };
  applyDir(i18n.language);
  i18n.on("languageChanged", (lang) => {
    applyDir(lang);
    try {
      window.localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // ignore quota errors
    }
  });
}

export { i18n };
