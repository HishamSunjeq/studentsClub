import { apiInstance } from "@/api/client";
import type { AuthUser } from "@/features/auth/auth.store";

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  college: string;
  academic_year: number;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export async function register(payload: RegisterPayload): Promise<AuthTokens> {
  const { data } = await apiInstance.post<AuthTokens>(
    "/api/v1/auth/register",
    payload,
  );
  return data;
}

export async function login(payload: LoginPayload): Promise<AuthTokens> {
  const { data } = await apiInstance.post<AuthTokens>(
    "/api/v1/auth/login",
    payload,
  );
  return data;
}

export async function fetchMe(): Promise<AuthUser> {
  const { data } = await apiInstance.get<AuthUser>("/api/v1/users/me");
  return data;
}

export async function logout(refreshToken: string): Promise<void> {
  await apiInstance.post("/api/v1/auth/logout", { refresh_token: refreshToken });
}
