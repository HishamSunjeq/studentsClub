export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  appEnv: import.meta.env.VITE_APP_ENV ?? "development",
} as const;
