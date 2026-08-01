import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import { MessageBubble } from './MessageBubble';
import {
  getChatScrollState,
  getPageScrollDelta,
  type ChatScrollDirection,
  type ChatScrollState,
} from './chatScroll';
import { useLanguage } from '../../i18n/LanguageContext';
import { Icon } from '../ui/Icon';
import type { ChatMessage } from '../../types/chat';

const INITIAL_SCROLL_STATE: ChatScrollState = {
  hasOverflow: false,
  canScrollUp: false,
  canScrollDown: false,
  isNearBottom: true,
};

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
  loadingText,
  emptyTitle,
  emptyHint,
  demoQuestions,
  onDemoQuestion,
}: ChatWindowProps) {
  const { t } = useLanguage();
  const viewportRef = useRef<HTMLElement | null>(null);
  const contentRef = useRef<HTMLDivElement | null>(null);
  const shouldFollowLatestRef = useRef(true);
  const previousRenderRef = useRef({
    initialized: false,
    loading,
    messageCount: messages.length,
    lastMessageId: messages.at(-1)?.id ?? null,
  });
  const [scrollState, setScrollState] = useState<ChatScrollState>(
    INITIAL_SCROLL_STATE,
  );
  const isEmpty = messages.length === 0;
  const resolvedLoadingText = loadingText ?? t.chat.loading;
  const resolvedEmptyTitle = emptyTitle ?? t.chat.emptyTitle;
  const resolvedEmptyHint = emptyHint ?? t.chat.emptyDescription;

  const syncScrollState = useCallback((trackReaderPosition = false) => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return INITIAL_SCROLL_STATE;
    }

    const nextState = getChatScrollState(viewport);
    setScrollState((currentState) => {
      if (
        currentState.hasOverflow === nextState.hasOverflow
        && currentState.canScrollUp === nextState.canScrollUp
        && currentState.canScrollDown === nextState.canScrollDown
        && currentState.isNearBottom === nextState.isNearBottom
      ) {
        return currentState;
      }
      return nextState;
    });

    if (trackReaderPosition) {
      shouldFollowLatestRef.current = nextState.isNearBottom;
    }

    return nextState;
  }, []);

  const handleScroll = useCallback(() => {
    syncScrollState(true);
  }, [syncScrollState]);

  const scrollByPage = useCallback((direction: ChatScrollDirection) => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return;
    }

    const reduceMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches;
    viewport.scrollBy({
      top: getPageScrollDelta(viewport.clientHeight, direction),
      behavior: reduceMotion ? 'auto' : 'smooth',
    });
  }, []);

  useLayoutEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return;
    }

    const previousRender = previousRenderRef.current;
    const isInitialRender = !previousRender.initialized;
    const latestMessage = messages.at(-1);
    const messageCountIncreased =
      messages.length > previousRender.messageCount;
    const latestMessageChanged =
      latestMessage?.id !== previousRender.lastMessageId;
    const userMessageArrived =
      messageCountIncreased
      && latestMessageChanged
      && latestMessage?.role === 'user';
    const assistantMessageArrived =
      messageCountIncreased
      && latestMessageChanged
      && latestMessage?.role === 'assistant';
    const loadingStarted = loading && !previousRender.loading;

    if (
      previousRender.initialized
      && (
        userMessageArrived
        || loadingStarted
        || (assistantMessageArrived && shouldFollowLatestRef.current)
      )
    ) {
      viewport.scrollTop = viewport.scrollHeight;
      shouldFollowLatestRef.current = true;
    }

    previousRenderRef.current = {
      initialized: true,
      loading,
      messageCount: messages.length,
      lastMessageId: latestMessage?.id ?? null,
    };

    if (isInitialRender) {
      shouldFollowLatestRef.current = syncScrollState(false).isNearBottom;
    }

    const frame = window.requestAnimationFrame(() => {
      if (shouldFollowLatestRef.current && !isInitialRender) {
        viewport.scrollTop = viewport.scrollHeight;
      }
      syncScrollState(false);
    });

    return () => window.cancelAnimationFrame(frame);
  }, [loading, messages, syncScrollState]);

  useLayoutEffect(() => {
    const viewport = viewportRef.current;
    const content = contentRef.current;
    if (!viewport || !content) {
      return;
    }

    const observer = new ResizeObserver(() => {
      if (shouldFollowLatestRef.current) {
        viewport.scrollTop = viewport.scrollHeight;
      }
      syncScrollState(false);
    });
    observer.observe(viewport);
    observer.observe(content);

    return () => observer.disconnect();
  }, [syncScrollState]);

  return (
    <div className="chat-window-shell">
      <section
        ref={viewportRef}
        id="chat-message-viewport"
        className="chat-window"
        aria-label={t.app.nav.chat}
        role="log"
        aria-live="polite"
        aria-relevant="additions text"
        onScroll={handleScroll}
        tabIndex={0}
      >
        <div ref={contentRef} className="chat-window__content">
          {isEmpty && !loading && (
            <div className="chat-landing">
              <div className="chat-landing__hero">
                <span className="chat-landing__icon" aria-hidden="true">
                  <Icon name="ledger" />
                </span>
                <h1 className="chat-landing__title">{resolvedEmptyTitle}</h1>
                <p className="chat-landing__subtitle">{resolvedEmptyHint}</p>
              </div>

              {demoQuestions && demoQuestions.length > 0 && (
                <div className="chat-landing__demo">
                  <p className="chat-landing__demo-label">
                    {t.chat.demoPrompt}
                  </p>
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
            <MessageBubble
              key={msg.id}
              role={msg.role}
              content={msg.content}
              response={msg.response}
              citationNamespace={msg.citationNamespace}
            />
          ))}

          {loading && (
            <MessageBubble
              role="assistant"
              content=""
              loading
              loadingText={resolvedLoadingText}
            />
          )}
        </div>
      </section>

      {messages.length > 0 && scrollState.hasOverflow && (
        <nav
          className="chat-scroll-controls"
          aria-label={t.chat.scrollNavigation}
        >
          <button
            type="button"
            className="chat-scroll-controls__button"
            aria-controls="chat-message-viewport"
            aria-label={t.chat.previousPage}
            disabled={!scrollState.canScrollUp}
            onClick={() => scrollByPage('previous')}
          >
            <Icon name="chevron-left" />
            <span>{t.chat.previousPage}</span>
          </button>
          <button
            type="button"
            className="chat-scroll-controls__button"
            aria-controls="chat-message-viewport"
            aria-label={t.chat.nextPage}
            disabled={!scrollState.canScrollDown}
            onClick={() => scrollByPage('next')}
          >
            <span>{t.chat.nextPage}</span>
            <Icon name="chevron-right" />
          </button>
        </nav>
      )}
    </div>
  );
}
