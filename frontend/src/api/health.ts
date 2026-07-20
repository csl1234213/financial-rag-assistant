import { apiBaseUrl, ApiClientError } from './client';
import type { HealthResponse } from '../types/api';

const healthEndpoint = '/api/v1/health';

function parseJson(text: string): unknown | undefined {
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined;
  }
}

export async function getHealth(): Promise<HealthResponse> {
  let response: Response;

  try {
    response = await fetch(`${apiBaseUrl}${healthEndpoint}`);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Network request failed.';
    throw new ApiClientError(message);
  }

  const payload = parseJson(await response.text());

  if (!response.ok) {
    const fallback = `Health check failed with status ${response.status}.`;
    const detail = (payload as Record<string, unknown> | undefined)?.detail;
    const message = typeof detail === 'string' ? detail : fallback;
    throw new ApiClientError(message, response.status, payload);
  }

  if (payload === undefined) {
    throw new ApiClientError('The API returned an invalid JSON response.', response.status);
  }

  return payload as HealthResponse;
}