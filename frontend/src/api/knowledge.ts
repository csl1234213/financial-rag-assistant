import {
  ApiClientError,
  deleteJson,
  getAuthorizationHeaders,
  getJson,
  toApiUrl,
} from './client';
import {
  isKnowledgeRecord,
  mapKnowledgeDocument,
} from './knowledgeContract';
import { MOCK_DOCUMENTS } from '../types/knowledge';
import type { KnowledgeDocument } from '../types/knowledge';

const knowledgeEndpoint = '/v1/knowledge';
const TASK_POLL_INTERVAL_MS = 4_000;
const TASK_RATE_LIMIT_RETRY_MS = 6_000;
const READ_RATE_LIMIT_RETRY_MS = 2_000;
export interface DocumentQuota {
  used: number;
  limit: number;
  remaining: number;
  bypassed?: boolean;
}

async function getKnowledgeJson<TResponse>(path: string): Promise<TResponse> {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      return await getJson<TResponse>(path);
    } catch (error: unknown) {
      if (!(error instanceof ApiClientError) || error.status !== 429 || attempt === 2) {
        throw error;
      }
      await wait(READ_RATE_LIMIT_RETRY_MS * (attempt + 1));
    }
  }
  throw new ApiClientError('Knowledge request retry budget exhausted.');
}

export function getDocumentQuota(): Promise<DocumentQuota> {
  return getKnowledgeJson<DocumentQuota>(`${knowledgeEndpoint}/quota`);
}
const knowledgeUploadEndpoint = '/v1/upload';
const taskEndpoint = (taskId: string) => `/v1/tasks/${taskId}`;

function parseJson(text: string): unknown | undefined {
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return isKnowledgeRecord(value);
}

function getErrorMessage(payload: unknown, fallback: string): string {
  if (!isRecord(payload)) return fallback;
  const detail = payload.detail;
  if (typeof detail === 'string') return detail;
  const message = payload.message;
  return typeof message === 'string' ? message : fallback;
}

const isMockEnabled = import.meta.env.VITE_ENABLE_MOCK === 'true';

interface UploadResponse {
  message: string;
  file: string;
  document_id: number;
  task_id: string;
  status: string;
}

interface TaskResponse {
  id: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  progress: number;
  error: string | null;
}

interface DeleteDocumentResponse {
  deleted: boolean;
  document_id: number;
}

export async function getDocuments(): Promise<KnowledgeDocument[]> {
  try {
    const raw = await getKnowledgeJson<unknown>(knowledgeEndpoint);
    if (isRecord(raw) && Array.isArray(raw.items)) {
      return raw.items
        .map(mapKnowledgeDocument)
        .filter((document): document is KnowledgeDocument => document !== null);
    }
    if (isRecord(raw) && Array.isArray(raw.documents)) {
      return raw.documents
        .map(mapKnowledgeDocument)
        .filter((document): document is KnowledgeDocument => document !== null);
    }
    if (Array.isArray(raw)) {
      return raw
        .map(mapKnowledgeDocument)
        .filter((document): document is KnowledgeDocument => document !== null);
    }
    return [];
  } catch (err) {
    if (isMockEnabled && (!(err instanceof ApiClientError) || err.status !== 401)) {
      return MOCK_DOCUMENTS;
    }
    throw err;
  }
}

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function waitForTask(taskId: string): Promise<void> {
  const deadline = Date.now() + 120_000;

  while (Date.now() < deadline) {
    let task: TaskResponse;
    try {
      task = await getJson<TaskResponse>(taskEndpoint(taskId));
    } catch (error: unknown) {
      // Upload already succeeded at this point. A reverse-proxy 429 while
      // checking task progress is transient and must not be reported as a
      // failed document upload.
      if (error instanceof ApiClientError && error.status === 429) {
        await wait(TASK_RATE_LIMIT_RETRY_MS);
        continue;
      }
      throw error;
    }
    if (task.status === 'success') {
      return;
    }
    if (task.status === 'failed') {
      throw new ApiClientError(task.error || 'Document processing failed.');
    }
    await wait(TASK_POLL_INTERVAL_MS);
  }

  throw new ApiClientError('Document processing timed out after 120 seconds.');
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  let response: Response;
  try {
    response = await fetch(toApiUrl(knowledgeUploadEndpoint), {
      method: 'POST',
      headers: getAuthorizationHeaders(),
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

  if (!isRecord(payload) || typeof payload.task_id !== 'string') {
    throw new ApiClientError('The upload response did not include a task id.', response.status, payload);
  }

  const uploadResponse = payload as unknown as UploadResponse;
  await waitForTask(uploadResponse.task_id);
  return uploadResponse;
}

export async function refreshKnowledge(): Promise<KnowledgeDocument[]> {
  return getDocuments();
}

export async function deleteDocument(documentId: string): Promise<void> {
  const response = await deleteJson<DeleteDocumentResponse>(
    `${knowledgeEndpoint}/${encodeURIComponent(documentId)}`,
  );
  if (!response.deleted) {
    throw new ApiClientError('The API did not confirm document deletion.');
  }
}
