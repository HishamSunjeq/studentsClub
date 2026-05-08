/**
 * English translations.
 *
 * Structure note: keys are nested by feature. When AR + RTL ships, add `ar.ts`
 * with the same shape and `i18n.changeLanguage('ar')` flips the active dictionary.
 *
 * This file is intentionally sparse — most existing UI uses literal strings.
 * As we i18n-ify pages, we add keys here and replace the literal in the JSX.
 */
export const en = {
  common: {
    cancel: "Cancel",
    save: "Save",
    delete: "Delete",
    loading: "Loading…",
    retry: "Retry",
    back: "Back",
    close: "Close",
    search: "Search",
    signIn: "Sign in",
    signOut: "Sign out",
    register: "Register",
  },
  nav: {
    dashboard: "Dashboard",
    subjects: "Subjects",
    upload: "Upload",
    drafts: "Drafts",
    quiz: "Quiz",
    history: "History",
    profile: "Profile",
    settings: "Settings",
  },
  auth: {
    welcomeBack: "Welcome back",
    createAccount: "Create your account",
    forgotPassword: "Forgot password?",
  },
  dashboard: {
    welcome: "Welcome back",
  },
  settings: {
    title: "Settings",
    description: "Account, preferences, notifications, and language.",
  },
} as const;

export type Translations = typeof en;
