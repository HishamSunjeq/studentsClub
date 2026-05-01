import axios, { type AxiosError, type AxiosRequestConfig } from "axios";

export const apiInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  timeout: 30_000,
});

// Attach JWT to every request from the persisted Zustand store
apiInstance.interceptors.request.use((config) => {
  // Read directly from localStorage to avoid a circular import with the store
  const raw = localStorage.getItem("auth");
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as { state?: { accessToken?: string } };
      const token = parsed?.state?.accessToken;
      if (token) config.headers.Authorization = `Bearer ${token}`;
    } catch {
      // Ignore parse errors
    }
  }
  return config;
});

// Refresh on 401 — one retry per request
type RetryConfig = AxiosRequestConfig & { _retried?: boolean };

apiInstance.interceptors.response.use(undefined, async (error: AxiosError) => {
  const original = error.config as RetryConfig | undefined;
  if (error.response?.status === 401 && original && !original._retried) {
    original._retried = true;
    try {
      const raw = localStorage.getItem("auth");
      const parsed = raw ? (JSON.parse(raw) as { state?: { refreshToken?: string } }) : null;
      const refreshToken = parsed?.state?.refreshToken;

      if (!refreshToken) return Promise.reject(error);

      const { data } = await apiInstance.post<{
        access_token: string;
        refresh_token: string;
      }>("/api/v1/auth/refresh", { refresh_token: refreshToken });

      // Patch persisted store directly so the next request uses the new token
      const stored = JSON.parse(localStorage.getItem("auth") ?? "{}") as {
        state?: Record<string, unknown>;
      };
      stored.state = {
        ...stored.state,
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
      };
      localStorage.setItem("auth", JSON.stringify(stored));

      if (original.headers) {
        original.headers.Authorization = `Bearer ${data.access_token}`;
      }
      return apiInstance.request(original);
    } catch {
      // Refresh failed — clear auth state so the app redirects to login
      localStorage.removeItem("auth");
    }
  }
  return Promise.reject(error);
});

/**
 * Orval mutator — every generated hook routes through this function
 * so auth, base URL, and error handling are centralised.
 */
export const apiClient = <T>(config: AxiosRequestConfig): Promise<T> =>
  apiInstance.request<T>(config).then((r) => r.data);
