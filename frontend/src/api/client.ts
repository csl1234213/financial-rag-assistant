import { buildApiUrl, normalizeApiBaseUrl } from './url';

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL;

/**
 * API base includes the reverse-proxy prefix. Endpoint modules own only the
 * versioned path below it (for example, `/v1/chat`).
 */
export const apiBaseUrl = normalizeApiBaseUrl(configuredBaseUrl || '/api');

export interface ApiErrorDetail {
  detail?: string;
  message?: string;
  errors?: unknown[];
  code?: string;
}

export class ApiClientError extends Error {
  readonly status?: number;
  readonly payload?: unknown;
  readonly detail: ApiErrorDetail | null;

  constructor(message: string, status?: number, payload?: unknown) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.payload = payload;
    this.detail = extractErrorDetail(payload);
  }

  get errorCode(): string | undefined {
    return this.detail?.code;
  }

  get errorMessages(): string[] {
    if (Array.isArray(this.detail?.errors)) {
      return this.detail.errors
        .filter((e): e is string | { message: string } => typeof e === 'string' || (typeof e === 'object' && e !== null))
        .map((e) => (typeof e === 'string' ? e : (e as { message: string }).message));
    }
    return [];
  }
}

function extractErrorDetail(payload: unknown): ApiErrorDetail | null {
  if (typeof payload !== 'object' || payload === null) return null;

  const p = payload as Record<string, unknown>;
  const detail: ApiErrorDetail = {};

  if (typeof p.detail === 'string') detail.detail = p.detail;
  if (typeof p.message === 'string') detail.message = p.message;
  if (Array.isArray(p.errors)) detail.errors = p.errors;
  if (typeof p.code === 'string') detail.code = p.code;

  return Object.keys(detail).length > 0 ? detail : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function getErrorMessage(payload: unknown, fallback: string): string {
  if (!isRecord(payload)) {
    return fallback;
  }

  const detail = payload.detail;
  if (typeof detail === 'string') {
    return detail;
  }

  const message = payload.message;
  return typeof message === 'string' ? message : fallback;
}

function parseJson(text: string): unknown | undefined {
  if (!text) {
    return undefined;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined;
  }
}

export function toApiUrl(path: string): string {
  return buildApiUrl(apiBaseUrl, path);
}

export async function postJson<TResponse>(path: string, body: unknown): Promise<TResponse> {
  let response: Response;

  try {
    response = await fetch(toApiUrl(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Network request failed.';
    throw new ApiClientError(message);
  }

  const payload = parseJson(await response.text());

  if (!response.ok) {
    throw new ApiClientError(
      getErrorMessage(payload, `Request failed with status ${response.status}.`),
      response.status,
      payload,
    );
  }

  if (payload === undefined) {
    throw new ApiClientError('The API returned an invalid JSON response.', response.status);
  }

  return payload as TResponse;
}
