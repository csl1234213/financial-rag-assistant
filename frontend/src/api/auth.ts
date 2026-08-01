import { getJson, postJson } from './client';
import { clearAccessToken, setAccessToken } from './session';
import type {
  AuthUser,
  LoginResponse,
  RegisterResponse,
} from '../types/auth';

export async function getCurrentUser(): Promise<AuthUser> {
  return getJson<AuthUser>('/v1/auth/me');
}

export async function registerUser(
  email: string,
  password: string,
): Promise<AuthUser> {
  const response = await postJson<RegisterResponse>('/v1/auth/register', {
    email,
    password,
  });
  setAccessToken(response.token);

  try {
    return await getCurrentUser();
  } catch (error) {
    clearAccessToken();
    throw error;
  }
}

export async function loginUser(
  email: string,
  password: string,
): Promise<AuthUser> {
  const response = await postJson<LoginResponse>('/v1/auth/login', {
    email,
    password,
  });
  setAccessToken(response.access_token);

  try {
    return await getCurrentUser();
  } catch (error) {
    clearAccessToken();
    throw error;
  }
}

export function logoutUser(): void {
  clearAccessToken();
}
