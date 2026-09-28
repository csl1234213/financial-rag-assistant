import { postJson } from './client';
import {
  createChatRequest,
  parseChatResponse,
} from './chatContract';
import type { ChatResponse } from '../types/chat';
import type { Language } from '../types/language';

const chatEndpoint = '/v1/chat';

export async function sendChatMessage(
  question: string,
  company?: string,
  threadId?: string,
  answerLanguage?: Language,
): Promise<ChatResponse> {
  const payload = await postJson(
    chatEndpoint,
    createChatRequest(question, company, threadId, answerLanguage),
  );
  return parseChatResponse(payload);
}
