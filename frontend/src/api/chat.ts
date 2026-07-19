import { postJson } from './client';
import teslaResponse from '../mock/tesla_response.json';
import type { ChatResponse } from '../types/chat';

const chatEndpoint = '/api/v1/chat';

/**
 * Sends a chat request to FastAPI. Any network, HTTP, or JSON failure falls
 * back to the local Tesla response so the demo remains usable offline.
 */
export async function sendChatMessage(message: string): Promise<ChatResponse> {
  try {
    return await postJson<ChatResponse>(chatEndpoint, { question: message });
  } catch {
    return teslaResponse;
  }
}
