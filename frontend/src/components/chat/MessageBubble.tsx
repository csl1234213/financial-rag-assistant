interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  loading?: boolean;
  loadingText?: string;
}

export function MessageBubble({
  role,
  content,
  loading = false,
  loadingText = 'Analyzing...',
}: MessageBubbleProps) {
  if (loading) {
    return (
      <article className="message message--assistant message--loading" aria-busy="true">
        <div className="message__header">
          <div className="message__avatar" aria-hidden="true">AI</div>
          <span className="message__role">Assistant</span>
        </div>
        <div className="message__body">
          <div className="message__loading-dots" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          {loadingText}
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
          {role === 'user' ? 'You' : 'Assistant'}
        </span>
      </div>
      <div className="message__body">
        <p>{content}</p>
      </div>
    </article>
  );
}