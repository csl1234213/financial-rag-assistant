import { ApiClientError, toApiUrl } from './client';
import { MOCK_DOCUMENTS } from '../types/knowledge';
import type { KnowledgeDocument } from '../types/knowledge';

const knowledgeEndpoint = '/v1/knowledge';
const knowledgeUploadEndpoint = '/v1/knowledge/upload';
const knowledgeRefreshEndpoint = '/v1/knowledge/refresh';

function parseJson(text: string): unknown | undefined {
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function getErrorMessage(payload: unknown, fallback: string): string {
  if (!isRecord(payload)) return fallback;
  const detail = payload.detail;
  if (typeof detail === 'string') return detail;
  const message = payload.message;
  return typeof message === 'string' ? message : fallback;
}

const isMockEnabled = import.meta.env.VITE_ENABLE_MOCK === 'true';

export async function getDocuments(): Promise<KnowledgeDocument[]> {
  try {
    const response = await fetch(toApiUrl(knowledgeEndpoint));
    const payload = parseJson(await response.text());

    if (!response.ok) {
      throw new ApiClientError(
        getErrorMessage(payload, `Failed to fetch documents (${response.status}).`),
        response.status,
        payload,
      );
    }

    if (payload === undefined) {
      throw new ApiClientError('The API returned an invalid JSON response.', response.status);
    }

    const raw = payload as unknown;
    if (isRecord(raw) && Array.isArray(raw.documents)) {
      return raw.documents as KnowledgeDocument[];
    }
    if (Array.isArray(raw)) {
      return raw as KnowledgeDocument[];
    }
    return [];
  } catch (err) {
    if (isMockEnabled) {
      return MOCK_DOCUMENTS;
    }
    throw err;
  }
}

export async function uploadDocument(file: File): Promise<KnowledgeDocument> {
  const formData = new FormData();
  formData.append('file', file);

  let response: Response;
  try {
    response = await fetch(toApiUrl(knowledgeUploadEndpoint), {
      method: 'POST',
      body: formData,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Network request failed.';
    throw new ApiClientError(message);
  }

  const payload = parseJson(await response.text());

  if (!response.ok) {
    throw new ApiClientError(
      getErrorMessage(payload, `Upload failed with status ${response.status}.`),
      response.status,
      payload,
    );
  }

  if (payload === undefined) {
    throw new ApiClientError('The API returned an invalid JSON response.', response.status);
  }

  return payload as KnowledgeDocument;
}

export async function refreshKnowledge(): Promise<KnowledgeDocument[]> {
  let response: Response;
  try {
    response = await fetch(toApiUrl(knowledgeRefreshEndpoint), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Network request failed.';
    throw new ApiClientError(message);
  }

  const payload = parseJson(await response.text());

  if (!response.ok) {
    throw new ApiClientError(
      getErrorMessage(payload, `Refresh failed with status ${response.status}.`),
      response.status,
      payload,
    );
  }

  if (payload === undefined) {
    throw new ApiClientError('The API returned an invalid JSON response.', response.status);
  }

  const raw = payload as unknown;
  if (isRecord(raw) && Array.isArray(raw.documents)) {
    return raw.documents as KnowledgeDocument[];
  }
  if (Array.isArray(raw)) {
    return raw as KnowledgeDocument[];
  }
  return [];
}
