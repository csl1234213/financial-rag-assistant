import { useLanguage } from '../../i18n/LanguageContext';
import { AssistantReport } from './AssistantReport';
import type { ChatResponse } from '../../types/api';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
  citationNamespace?: string;
  loading?: boolean;
  loadingText?: string;
}

export function MessageBubble({
  role,
  content,
  response,
  citationNamespace,
  loading = false,
  loadingText,
}: MessageBubbleProps) {
  const { t } = useLanguage();
  const roleLabel = role === 'user' ? t.chat.user : t.chat.assistant;

  if (loading) {
    return (
      <article className="message message--assistant message--loading" aria-busy="true">
        <div className="message__header">
          <div className="message__avatar" aria-hidden="true">AI</div>
          <span className="message__role">{t.chat.assistant}</span>
        </div>
        <div className="message__body">
          <div className="message__loading-dots" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          {loadingText ?? t.chat.loading}
        </div>
      </article>
    );
  }

  return (
    <article className={`message message--${role}`}>
      <div className="message__header">
        <div className="message__avatar" aria-hidden="true">
          {role === 'user' ? 'U' : 'AI'}
        </div>
        <span className="message__role">
          {roleLabel}
        </span>
      </div>
      <div className="message__body">
        {role === 'assistant'
          ? (
            <AssistantReport
              content={content}
              response={response}
              citationNamespace={citationNamespace}
            />
          )
          : <p>{content}</p>}
      </div>
    </article>
  );
}
