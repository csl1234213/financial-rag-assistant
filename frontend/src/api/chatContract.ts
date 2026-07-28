import type {
  ChatResponse,
  Citation,
  Execution,
  Planning,
  Reasoning,
  Routing,
  Workflow,
} from '../types/api';

export interface ChatRequest {
  question: string;
  company?: string;
}

export class ChatContractError extends Error {
  constructor(message: string) {
    super(`Invalid chat API contract: ${message}`);
    this.name = 'ChatContractError';
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requireRecord(
  value: unknown,
  path: string,
): Record<string, unknown> {
  if (!isRecord(value)) {
    throw new ChatContractError(`${path} must be an object`);
  }
  return value;
}

function requireString(value: unknown, path: string): string {
  if (typeof value !== 'string') {
    throw new ChatContractError(`${path} must be a string`);
  }
  return value;
}

function requireFiniteNumber(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new ChatContractError(`${path} must be a finite number`);
  }
  return value;
}

function parseCitation(value: unknown, index: number): Citation {
  const path = `citations[${index}]`;
  const citation = requireRecord(value, path);
  const rank = requireFiniteNumber(citation.rank, `${path}.rank`);

  if (!Number.isInteger(rank) || rank < 1) {
    throw new ChatContractError(`${path}.rank must be a positive integer`);
  }

  requireString(citation.source, `${path}.source`);
  requireString(citation.chunk_id, `${path}.chunk_id`);
  requireString(citation.preview, `${path}.preview`);

  const similarity = citation.similarity;
  if (similarity !== null) {
    requireFiniteNumber(similarity, `${path}.similarity`);
  }

  return citation as unknown as Citation;
}

function parseReasoning(value: unknown): Reasoning {
  const reasoning = requireRecord(value, 'reasoning');
  requireString(reasoning.intent, 'reasoning.intent');
  requireString(reasoning.research_mode, 'reasoning.research_mode');
  const evidenceCount = requireFiniteNumber(
    reasoning.evidence_count,
    'reasoning.evidence_count',
  );
  if (!Number.isInteger(evidenceCount) || evidenceCount < 0) {
    throw new ChatContractError(
      'reasoning.evidence_count must be a non-negative integer',
    );
  }

  if (
    !Array.isArray(reasoning.companies)
    || !reasoning.companies.every((company) => typeof company === 'string')
  ) {
    throw new ChatContractError('reasoning.companies must be an array of strings');
  }

  return reasoning as unknown as Reasoning;
}

function parseNullableRecord<T>(
  value: unknown,
  path: string,
  validate: (record: Record<string, unknown>) => void,
): T | null {
  if (value === null) {
    return null;
  }

  const record = requireRecord(value, path);
  validate(record);
  return record as unknown as T;
}

export function createChatRequest(
  question: string,
  company?: string,
): ChatRequest {
  const normalizedQuestion = question.trim();
  if (!normalizedQuestion) {
    throw new ChatContractError('question must not be empty');
  }

  const request: ChatRequest = { question: normalizedQuestion };
  const normalizedCompany = company?.trim();
  if (normalizedCompany) {
    request.company = normalizedCompany;
  }
  return request;
}

export function parseChatResponse(value: unknown): ChatResponse {
  const response = requireRecord(value, 'response');
  requireString(response.report, 'report');
  requireRecord(response.plan, 'plan');
  requireFiniteNumber(response.execution_time, 'execution_time');

  if (!Array.isArray(response.citations)) {
    throw new ChatContractError('citations must be an array');
  }
  const citations = response.citations.map(parseCitation);
  const reasoning = parseReasoning(response.reasoning);

  const routing = parseNullableRecord<Routing>(
    response.routing,
    'routing',
    (record) => requireString(record.provider, 'routing.provider'),
  );
  const planning = parseNullableRecord<Planning>(
    response.planning,
    'planning',
    () => undefined,
  );
  const execution = parseNullableRecord<Execution>(
    response.execution,
    'execution',
    (record) => requireString(record.strategy, 'execution.strategy'),
  );
  const workflow = parseNullableRecord<Workflow>(
    response.workflow,
    'workflow',
    (record) => {
      requireString(record.type, 'workflow.type');
      requireString(record.status, 'workflow.status');
    },
  );

  return {
    ...response,
    citations,
    reasoning,
    routing,
    planning,
    execution,
    workflow,
  } as ChatResponse;
}
