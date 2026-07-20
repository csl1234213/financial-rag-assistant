import { useState, useCallback, useEffect } from 'react';
import { Header } from '../components/layout/Header';
import { Sidebar } from '../components/Sidebar';
import { ChatWindow } from '../components/chat/ChatWindow';
import { InputBox } from '../components/chat/InputBox';
import { AgentTimeline } from '../components/agent/AgentTimeline';
import { CitationList } from '../components/citation/CitationList';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { sendChatMessage } from '../api/chat';
import { getHealth } from '../api/health';
import type { DemoQuestion } from '../components/chat/ChatWindow';
import type { ChatMessage, ChatResponse, HealthResponse } from '../types/api';
import type { Language } from '../types/language';

const demoQuestions: DemoQuestion[] = [
  { label: 'Tesla revenue growth', question: 'What is Tesla\'s revenue growth trend in 2025?' },
  { label: 'NVIDIA data center', question: 'How is NVIDIA\'s data center business performing?' },
  { label: 'Compare margins', question: 'Compare gross margins between Tesla and NVIDIA in 2025.' },
  { label: 'Apple services', question: 'What is Apple\'s services revenue growth?' },
  { label: 'R&D investments', question: 'How much are Tesla and NVIDIA investing in R&D?' },
];

const copy = {
  en: {
    header: {
      title: 'Financial RAG Assistant',
      subtitle: 'AI Research Agent',
    },
    sidebar: {
      runtime: 'Financial Agent Runtime',
      title: 'AI Copilot',
      demoCompanies: 'Demo Companies',
      language: 'Language',
    },
    chat: {
      title: 'Financial AI Copilot',
      localDemo: 'Local Demo',
      emptyTitle: 'Financial RAG Assistant',
      emptyHint: 'Ask about Tesla, NVIDIA, or Apple financial performance.',
      loadingText: 'Agent Runtime is analyzing...',
      placeholder: 'Ask a financial question...',
    },
    trace: {
      title: 'Agent Trace',
      empty: 'Submit a question to view the agent trace.',
      reasoning: 'Reasoning',
      intent: 'Intent',
      companies: 'Companies',
      researchMode: 'Research mode',
      execution: 'Execution',
      strategy: 'Strategy',
      provider: 'Provider',
      workflow: 'Workflow',
      type: 'Type',
      status: 'Status',
    },
    agent: {
      title: 'Agent Execution',
      empty: 'Submit a question to see the agent execution trace.',
    },
    citation: {
      title: 'Evidence',
      empty: 'Evidence will appear after analysis.',
    },
  },
  'zh-CN': {
    header: {
      title: '金融 RAG 助手',
      subtitle: 'AI 研究代理',
    },
    sidebar: {
      runtime: '金融智能体运行平台',
      title: 'AI Copilot',
      demoCompanies: '演示公司',
      language: '语言',
    },
    chat: {
      title: '金融 AI Copilot',
      localDemo: '本地演示',
      emptyTitle: '金融 RAG 助手',
      emptyHint: '询问特斯拉、英伟达或苹果的财务表现。',
      loadingText: '智能体运行平台正在分析...',
      placeholder: '提出财务问题...',
    },
    trace: {
      title: '智能体轨迹',
      empty: '提交问题后将在此显示智能体轨迹。',
      reasoning: '推理',
      intent: '意图',
      companies: '公司',
      researchMode: '研究模式',
      execution: '执行',
      strategy: '执行策略',
      provider: '服务提供方',
      workflow: '工作流',
      type: '类型',
      status: '状态',
    },
    agent: {
      title: 'Agent 执行',
      empty: '提交问题以查看 Agent 执行轨迹。',
    },
    citation: {
      title: '证据',
      empty: '分析完成后将在此显示证据。',
    },
  },
};

export function Chat() {
  const [language, setLanguage] = useState<Language>('en');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [backendConnected, setBackendConnected] = useState(false);

  const t = copy[language];

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const health = await getHealth();
        if (!cancelled) {
          setBackendConnected(health.status === 'healthy' || health.status === 'degraded');
        }
      } catch {
        if (!cancelled) {
          setBackendConnected(false);
        }
      }
    }

    checkHealth();
    const timer = setInterval(checkHealth, 30000);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const handleSend = useCallback(
    async (question: string) => {
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: question,
      };

      setMessages((prev) => [...prev, userMessage]);
      setLoading(true);
      setError(null);
      setResponse(null);

      try {
        const apiResponse = await sendChatMessage(question);
        setResponse(apiResponse);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: apiResponse.report,
          },
        ]);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Connection Error';
        setError(message);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `Connection Error: ${message}`,
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return (
    <ErrorBoundary>
      <div className="app-layout">
        <Header
          title={t.header.title}
          subtitle={t.header.subtitle}
          connected={backendConnected}
        />

        <div className="copilot-layout">
          <Sidebar
            language={language}
            onLanguageChange={setLanguage}
            labels={t.sidebar}
          />

          <main className="main-chat">
            <div className="main-chat__header">
              <h2>{t.chat.title}</h2>
              <span className="status">{t.chat.localDemo}</span>
            </div>

            <ChatWindow
              messages={messages}
              loading={loading}
              loadingText={t.chat.loadingText}
              emptyTitle={t.chat.emptyTitle}
              emptyHint={t.chat.emptyHint}
              demoQuestions={demoQuestions}
              onDemoQuestion={handleSend}
            />

            <InputBox
              onSubmit={handleSend}
              disabled={loading}
              placeholder={t.chat.placeholder}
            />
          </main>

          <aside className="agent-panel">
            <AgentTimeline
              response={response}
              loading={loading}
              title={t.agent.title}
              emptyMessage={t.agent.empty}
            />

            <CitationList
              citations={response?.citations ?? []}
              title={t.citation.title}
              emptyMessage={t.citation.empty}
            />
          </aside>
        </div>
      </div>
    </ErrorBoundary>
  );
}