import { AgentStep } from './AgentStep';
import type { AgentStepData } from './AgentStep';
import type { ChatResponse } from '../../types/api';

interface AgentTimelineProps {
  response: ChatResponse | null;
  loading: boolean;
  title?: string;
  emptyMessage?: string;
}

function buildTimeline(response: ChatResponse | null, loading: boolean): AgentStepData[] {
  if (response) {
    const strategy = response.execution?.strategy || 'rag';
    const provider = response.routing?.provider || 'unknown';
    const workflowType = response.workflow?.type || 'rag';
    const intent = response.reasoning?.intent || 'SINGLE_COMPANY';
    const companies = response.reasoning?.companies || [];
    const citationCount = response.citations?.length || 0;
    const executionTime = response.execution_time
      ? `${response.execution_time.toFixed(2)}s`
      : 'N/A';
    const planSteps = response.plan?.steps?.length ?? 0;
    const planDescription = response.plan?.steps?.length
      ? `Executed ${planSteps} research step(s)`
      : 'Built research plan for analysis';

    return [
      {
        id: 'intent',
        name: 'Intent Analyzer',
        description: `Detected intent: ${intent}${companies.length ? ' — ' + companies.join(', ') : ''}`,
        status: 'completed',
      },
      {
        id: 'planner',
        name: 'Query Planner',
        description: `${planDescription} for ${workflowType} workflow`,
        status: 'completed',
      },
      {
        id: 'retriever',
        name: 'Hybrid Retriever',
        description: `Retrieved ${citationCount} evidence chunks from vector store`,
        status: 'completed',
      },
      {
        id: 'ranker',
        name: 'Evidence Ranking',
        description: 'Ranked results by relevance score',
        status: 'completed',
      },
      {
        id: 'generator',
        name: 'LLM Generation',
        description: `Generated report via ${provider} (${strategy}) in ${executionTime}`,
        status: 'completed',
      },
    ];
  }

  if (loading) {
    return [
      { id: 'intent', name: 'Intent Analyzer', description: 'Classifying user intent...', status: 'completed' },
      { id: 'planner', name: 'Query Planner', description: 'Building research plan...', status: 'completed' },
      { id: 'retriever', name: 'Hybrid Retriever', description: 'Searching knowledge base...', status: 'running' },
      { id: 'ranker', name: 'Evidence Ranking', description: 'Waiting for retrieval...', status: 'pending' },
      { id: 'generator', name: 'LLM Generation', description: 'Waiting for evidence...', status: 'pending' },
    ];
  }

  return [
    { id: 'intent', name: 'Intent Analyzer', description: 'Classifies the user query intent', status: 'pending' },
    { id: 'planner', name: 'Query Planner', description: 'Builds a research execution plan', status: 'pending' },
    { id: 'retriever', name: 'Hybrid Retriever', description: 'Searches vector store for evidence', status: 'pending' },
    { id: 'ranker', name: 'Evidence Ranking', description: 'Ranks results by relevance', status: 'pending' },
    { id: 'generator', name: 'LLM Generation', description: 'Generates the final report', status: 'pending' },
  ];
}

export function AgentTimeline({
  response,
  loading,
  title = 'Agent Execution',
  emptyMessage = 'Submit a question to see the agent execution trace.',
}: AgentTimelineProps) {
  const steps = buildTimeline(response, loading);
  const hasResponse = response !== null;

  return (
    <section className="agent-timeline-panel" aria-labelledby="agent-timeline-title">
      <h2 id="agent-timeline-title" className="agent-timeline-panel__title">
        {title}
      </h2>

      {!hasResponse && !loading && (
        <p className="agent-timeline-panel__empty">{emptyMessage}</p>
      )}

      <div className="agent-timeline">
        {steps.map((step, index) => (
          <AgentStep
            key={step.id}
            step={step}
            isLast={index === steps.length - 1}
          />
        ))}
      </div>

      {hasResponse && (
        <div className="agent-timeline-panel__summary">
          <span className="agent-timeline-panel__summary-label">Workflow</span>
          <span className="agent-timeline-panel__summary-value">
            {response.workflow?.type ?? 'rag'}
          </span>
        </div>
      )}
    </section>
  );
}
