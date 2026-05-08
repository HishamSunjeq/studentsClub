import { useCallback, useEffect, useState } from "react";
import {
  ACCENT_CLASS_PREFIX,
  ACCENT_STORAGE_KEY,
  DEFAULT_ACCENT,
  accentClass,
  isAccentId,
  type AccentId,
} from "./themes";

/**
 * Sibling to next-themes' `useTheme`, but for the *accent* dimension.
 * Persists to localStorage and writes a `.accent-<id>` class on <html>.
 *
 * The bootstrap script in `index.html` handles the first paint so this hook
 * never causes a flash of wrong-accent content.
 */
export function useAccent() {
  const [accent, setAccentState] = useState<AccentId>(() => {
    if (typeof window === "undefined") return DEFAULT_ACCENT;
    const stored = window.localStorage.getItem(ACCENT_STORAGE_KEY);
    return isAccentId(stored) ? stored : DEFAULT_ACCENT;
  });

  // Keep <html> class in sync with state
  useEffect(() => {
    const root = document.documentElement;
    // Strip any existing accent class
    root.classList.forEach((cls) => {
      if (cls.startsWith(ACCENT_CLASS_PREFIX)) root.classList.remove(cls);
    });
    root.classList.add(accentClass(accent));
  }, [accent]);

  const setAccent = useCallback((next: AccentId) => {
    setAccentState(next);
    try {
      window.localStorage.setItem(ACCENT_STORAGE_KEY, next);
    } catch {
      // ignore quota errors
    }
  }, []);

  return { accent, setAccent };
}
