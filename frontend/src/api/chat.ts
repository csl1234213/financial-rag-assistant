import { postJson } from './client';
import type { ChatResponse } from '../types/chat';

const chatEndpoint = '/api/v1/chat';

export interface ChatRequest {
  question: string;
  company?: string;
}

export async function sendChatMessage(
  question: string,
  company?: string,
): Promise<ChatResponse> {
  const body: ChatRequest = { question };
  if (company) {
    body.company = company;
  }

  return postJson<ChatResponse>(chatEndpoint, body);
}