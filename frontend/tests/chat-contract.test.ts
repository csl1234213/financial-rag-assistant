import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ChatContractError,
  createChatRequest,
  parseChatResponse,
} from '../src/api/chatContract.ts';
import { buildApiUrl } from '../src/api/url.ts';

function currentBackendResponse(): Record<string, unknown> {
  return {
    report: 'Tesla revenue increased.',
    citations: [
      {
        rank: 1,
        source: 'Tesla_Q2_2025.pdf',
        chunk_id: 'tesla-q2-14',
        similarity: 0.93,
        preview: 'Revenue increased during the quarter.',
      },
    ],
    reasoning: {
      intent: 'SINGLE_COMPANY',
      companies: ['Tesla'],
      research_mode: 'default',
      evidence_count: 1,
    },
    plan: {
      intent: 'single_company',
      task_count: 1,
      tasks: [],
    },
    execution_time: 0.42,
    routing: {
      provider: 'deepseek',
      model: 'deepseek-chat',
    },
    planning: {
      task_type: 'document_qa',
    },
    execution: {
      strategy: 'rag',
      use_retrieval: true,
    },
    workflow: {
      type: 'rag',
      status: 'completed',
    },
  };
}

test('creates the backend request with question, never message', () => {
  assert.deepEqual(
    createChatRequest('  Analyze Tesla revenue growth  ', ' Tesla '),
    {
      question: 'Analyze Tesla revenue growth',
      company: 'Tesla',
    },
  );
});

test('builds the canonical Docker and Vite proxy chat URL', () => {
  assert.equal(buildApiUrl('/api', '/v1/chat'), '/api/v1/chat');
  assert.equal(
    buildApiUrl('http://localhost:8000/api/', 'v1/chat'),
    'http://localhost:8000/api/v1/chat',
  );
});

test('accepts the current backend citation and routing provider contract', () => {
  const response = parseChatResponse(currentBackendResponse());

  assert.equal(response.citations[0].source, 'Tesla_Q2_2025.pdf');
  assert.equal(response.citations[0].preview, 'Revenue increased during the quarter.');
  assert.equal(response.routing?.provider, 'deepseek');
  assert.equal(response.execution?.strategy, 'rag');
});

test('rejects the obsolete frontend-only citation shape', () => {
  const payload = currentBackendResponse();
  payload.citations = [
    {
      filename: 'Tesla_Q2_2025.pdf',
      page: 14,
      similarity: 0.93,
      snippet: 'Legacy UI shape.',
    },
  ];

  assert.throws(
    () => parseChatResponse(payload),
    (error: unknown) => (
      error instanceof ChatContractError
      && error.message.includes('citations[0].rank')
    ),
  );
});
