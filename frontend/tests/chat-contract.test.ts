import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ChatContractError,
  createChatRequest,
  parseChatResponse,
} from '../src/api/chatContract.ts';
import {
  buildConversationDeletePath,
  buildConversationDetailPath,
  parseConversationDeleteResult,
  parseConversationDetail,
  parseConversationList,
} from '../src/api/agentSessionContract.ts';
import { buildApiUrl } from '../src/api/url.ts';
import {
  buildCitationDomId,
  extractModelIdentity,
  localizeReportHeading,
  parseRestrictedMarkdown,
  splitResearchReport,
} from '../src/components/chat/reportPresentation.ts';

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
      model: 'deepseek-v4-flash',
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
    createChatRequest(
      '  Analyze Tesla revenue growth  ',
      ' Tesla ',
      ' chat-session-123 ',
    ),
    {
      question: 'Analyze Tesla revenue growth',
      company: 'Tesla',
      thread_id: 'chat-session-123',
    },
  );
});

test('keeps thread id optional for non-interactive API callers', () => {
  assert.deepEqual(createChatRequest('What is AI?'), {
    question: 'What is AI?',
  });
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

test('extracts the actual routed provider and model for completion status', () => {
  const response = parseChatResponse(currentBackendResponse());

  assert.deepEqual(extractModelIdentity(response.routing), {
    provider: 'deepseek',
    model: 'deepseek-v4-flash',
  });
  assert.equal(extractModelIdentity(null), null);
  assert.deepEqual(extractModelIdentity({ provider: 'gemini' }), {
    provider: 'gemini',
    model: null,
  });
});

test('separates the current model answer from Agent evidence analysis', () => {
  const report = splitResearchReport(`
# Research Report

## Question
How did Tesla revenue change?

## Answer (LLM Answer)
Summary

The available evidence is insufficient for a growth trend. [Evidence 1]

Key Findings

1. Automotive revenue was 82.4 billion USD.

Evidence Used

[Evidence 1]

## Agent Evidence Analysis

## Key Facts
- Tesla reported automotive revenue of 82.4 billion USD.

## Risk Signals
- Pricing pressure remains a risk.

## AI Conclusion
Collected 1 financial fact.
`);

  assert.ok(report);
  assert.equal(report.question, 'How did Tesla revenue change?');
  assert.match(report.modelAnswer, /available evidence is insufficient/);
  assert.match(report.modelAnswer, /Key Findings/);
  assert.doesNotMatch(report.modelAnswer, /Evidence Used/);
  assert.doesNotMatch(report.modelAnswer, /## Key Facts/);
  assert.equal(report.evidenceUsed, '[Evidence 1]');
  assert.match(report.agentAnalysis, /^## Key Facts/);
  assert.match(report.agentAnalysis, /## AI Conclusion/);
});

test('separates a Chinese research report into the same presentation contract', () => {
  const report = splitResearchReport(`
# 研究报告

## 问题
特斯拉 2025 年的营收增长趋势如何？

## 回答（LLM 模型回答）
摘要

总营收同比下降。[Evidence 1]

使用的证据

[Evidence 1]

## 智能体证据分析

## 关键事实
- Tesla total revenues were 41.831 billion USD.

## 来源覆盖
- Tesla_Q2_2025.pdf: 2 个文本块
`);

  assert.ok(report);
  assert.equal(report.question, '特斯拉 2025 年的营收增长趋势如何？');
  assert.match(report.modelAnswer, /总营收同比下降/);
  assert.doesNotMatch(report.modelAnswer, /智能体证据分析/);
  assert.doesNotMatch(report.modelAnswer, /使用的证据/);
  assert.equal(report.evidenceUsed, '[Evidence 1]');
  assert.match(report.agentAnalysis, /^## 关键事实/);
  assert.match(report.agentAnalysis, /## 来源覆盖/);
});

test('keeps a long model answer intact for continuous scrolling', () => {
  const modelAnswer = '这是需要通过鼠标滚轮完整阅读的模型回答。'.repeat(300);
  const report = splitResearchReport(`
# Research Report

## Question
测试长回答

## Answer
${modelAnswer}

## Agent Evidence Analysis
### Key Facts
- 测试证据
`);

  assert.ok(report);
  assert.equal(report.modelAnswer, modelAnswer);
});

test('restricted Markdown keeps raw HTML as ordinary escaped render data', () => {
  const blocks = parseRestrictedMarkdown(`
## Result

<script>alert("not executable")</script>

- **Evidence:** source.pdf
- \`model=deepseek-v4-flash\`
`);

  assert.deepEqual(blocks[0], {
    type: 'heading',
    level: 2,
    text: 'Result',
  });
  assert.deepEqual(blocks[1], {
    type: 'paragraph',
    text: '<script>alert("not executable")</script>',
  });
  assert.equal(blocks[2].type, 'unordered-list');
  assert.equal(blocks.some((block) => 'html' === block.type), false);
});

test('builds unique, sanitized citation DOM ids for each chat turn', () => {
  assert.equal(
    buildCitationDomId('chat-turn-a1', 1),
    'chat-turn-a1-evidence-1',
  );
  assert.equal(
    buildCitationDomId('chat turn/b2', 1),
    'chat-turn-b2-evidence-1',
  );
  assert.notEqual(
    buildCitationDomId('chat-turn-a1', 1),
    buildCitationDomId('chat-turn-b2', 1),
  );
  assert.equal(
    buildCitationDomId('chat-turn-a1', 2),
    'chat-turn-a1-evidence-2',
  );
});

test('parses authenticated conversation summaries and transcript messages', () => {
  const list = parseConversationList({
    items: [
      {
        thread_id: 'tenant/thread 1',
        message_count: 3,
        created_at: '2026-07-29T08:00:00Z',
        updated_at: '2026-07-29T08:05:00Z',
      },
    ],
    total: 1,
    limit: 50,
    offset: 0,
  });
  const detail = parseConversationDetail({
    session: {
      thread_id: 'tenant/thread 1',
      message_count: 3,
      created_at: '2026-07-29T08:00:00Z',
      updated_at: '2026-07-29T08:05:00Z',
    },
    messages: [
      {
        id: 1,
        role: 'system',
        content: 'internal context',
        metadata: {},
        created_at: '2026-07-29T08:00:00Z',
      },
      {
        id: 2,
        role: 'user',
        content: 'Analyze NVIDIA.',
        metadata: {},
        created_at: '2026-07-29T08:01:00Z',
      },
      {
        id: 3,
        role: 'assistant',
        content: 'NVIDIA analysis.',
        metadata: {},
        created_at: '2026-07-29T08:05:00Z',
      },
    ],
    total_messages: 3,
    limit: 500,
    offset: 0,
  });

  assert.equal(list.items[0].threadId, 'tenant/thread 1');
  assert.deepEqual(detail.messages.map((message) => message.role), [
    'user',
    'assistant',
  ]);
  assert.equal(
    buildConversationDetailPath('tenant/thread 1', 620),
    '/v1/agent/sessions/tenant%2Fthread%201'
      + '?message_limit=500&message_offset=120',
  );
});

test('parses session deletion results and safely encodes delete paths', () => {
  const result = parseConversationDeleteResult({
    deleted: true,
    thread_id: '租户/thread 1',
    messages_deleted: 4,
    checkpoints_archived: 2,
    runtime_checkpoints_deleted: true,
    cache_keys_deleted: 3,
  });

  assert.deepEqual(result, {
    deleted: true,
    threadId: '租户/thread 1',
    messagesDeleted: 4,
    checkpointsArchived: 2,
    runtimeCheckpointsDeleted: true,
    cacheKeysDeleted: 3,
  });
  assert.equal(
    buildConversationDeletePath('租户/thread 1'),
    '/v1/agent/sessions/%E7%A7%9F%E6%88%B7%2Fthread%201',
  );
  assert.throws(
    () => parseConversationDeleteResult({
      deleted: false,
      thread_id: 'thread-1',
      messages_deleted: 0,
      checkpoints_archived: 0,
      runtime_checkpoints_deleted: false,
      cache_keys_deleted: 0,
    }),
    /deleted=true/,
  );
});

test('localizes fixed report headings without changing model prose', () => {
  assert.equal(localizeReportHeading('Summary', 'zh-CN'), '摘要');
  assert.equal(localizeReportHeading('Key Findings', 'zh-CN'), '关键发现');
  assert.equal(localizeReportHeading('Risks', 'zh-CN'), '风险');
  assert.equal(localizeReportHeading('Summary', 'en'), 'Summary');
  assert.equal(
    localizeReportHeading('Tesla automotive revenue', 'zh-CN'),
    'Tesla automotive revenue',
  );
});
