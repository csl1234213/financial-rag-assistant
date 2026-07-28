import { postJson } from './client';
import {
  createChatRequest,
  parseChatResponse,
} from './chatContract';
import type { ChatResponse } from '../types/chat';

const chatEndpoint = '/v1/chat';

export async function sendChatMessage(
  question: string,
  company?: string,
): Promise<ChatResponse> {
  const payload = await postJson<unknown>(
    chatEndpoint,
    createChatRequest(question, company),
  );
  return parseChatResponse(payload);
}
