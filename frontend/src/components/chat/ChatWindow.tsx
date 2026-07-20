import { MessageBubble } from './MessageBubble';
import type { ChatMessage } from '../../types/chat';

export interface DemoQuestion {
  label: string;
  question: string;
}

interface ChatWindowProps {
  messages: ChatMessage[];
  loading: boolean;
  loadingText?: string;
  emptyTitle?: string;
  emptyHint?: string;
  demoQuestions?: DemoQuestion[];
  onDemoQuestion?: (question: string) => void;
}

export function ChatWindow({
  messages,
  loading,
  loadingText = 'Agent Runtime is analyzing...',
  emptyTitle = 'Financial RAG Assistant',
  emptyHint = 'Ask about Tesla, NVIDIA, or Apple financial performance.',
  demoQuestions,
  onDemoQuestion,
}: ChatWindowProps) {
  const isEmpty = messages.length === 0;

  return (
    <section className="chat-window" aria-label="Conversation" aria-live="polite">
      {isEmpty && !loading && (
        <div className="chat-landing">
          <div className="chat-landing__hero">
            <span className="chat-landing__icon" aria-hidden="true">
              &#x1F4CA;
            </span>
            <h1 className="chat-landing__title">{emptyTitle}</h1>
            <p className="chat-landing__subtitle">
              AI-powered financial research agent. Analyze earnings reports, compare
              companies, and extract insights from financial documents.
            </p>
          </div>

          {demoQuestions && demoQuestions.length > 0 && (
            <div className="chat-landing__demo">
              <p className="chat-landing__demo-label">Try a demo question</p>
              <div className="chat-landing__demo-chips">
                {demoQuestions.map((dq) => (
                  <button
                    key={dq.question}
                    type="button"
                    className="chat-landing__demo-chip"
                    onClick={() => onDemoQuestion?.(dq.question)}
                  >
                    {dq.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {messages.map((msg) => (
        <MessageBubble key={msg.id} role={msg.role} content={msg.content} />
      ))}

      {loading && <MessageBubble role="assistant" content="" loading loadingText={loadingText} />}
    </section>
  );
}