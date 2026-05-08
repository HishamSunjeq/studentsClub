/**
 * Theme registry — adding a new theme is two steps:
 *   1. Append an entry below
 *   2. Add a `.accent-<id> { --primary: …; --ring: …; ... }` block in `src/styles/globals.css`
 *
 * The shell, settings picker, and bootstrap script all read from this registry,
 * so a new accent shows up everywhere automatically.
 */

export type ColorScheme = "light" | "dark" | "system";

export const COLOR_SCHEMES: { id: ColorScheme; label: string }[] = [
  { id: "system", label: "System" },
  { id: "light", label: "Light" },
  { id: "dark", label: "Dark" },
];

/** Accent presets — each id maps to a `.accent-<id>` class in globals.css. */
export const ACCENT_PRESETS = [
  { id: "indigo", label: "Indigo", preview: "#4f46e5" },
  { id: "emerald", label: "Emerald", preview: "#10b981" },
  { id: "amber", label: "Amber", preview: "#f59e0b" },
  { id: "rose", label: "Rose", preview: "#e11d48" },
  { id: "sky", label: "Sky", preview: "#0ea5e9" },
  { id: "violet", label: "Violet", preview: "#8b5cf6" },
] as const;

export type AccentId = (typeof ACCENT_PRESETS)[number]["id"];

export const DEFAULT_ACCENT: AccentId = "indigo";
export const ACCENT_STORAGE_KEY = "sc-accent";
export const THEME_STORAGE_KEY = "sc-theme";

export function isAccentId(value: string | null | undefined): value is AccentId {
  if (!value) return false;
  return ACCENT_PRESETS.some((p) => p.id === value);
}

export const ACCENT_CLASS_PREFIX = "accent-";

export function accentClass(id: AccentId): string {
  return `${ACCENT_CLASS_PREFIX}${id}`;
}
