export interface Citation {
  filename: string;
  page: number;
  similarity: number;
  snippet: string;
}

export interface Reasoning {
  intent: string;
  companies: string[];
  research_mode: string;
}

export interface Execution {
  strategy: string;
  provider: string;
}

export interface Workflow {
  type: string;
  status: string;
}

/**
 * UI contract for the structured chat response returned by Backend V7.3.3.
 */
export interface ChatResponse {
  report: string;
  reasoning: Reasoning;
  execution: Execution;
  workflow: Workflow;
  citations: Citation[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}
