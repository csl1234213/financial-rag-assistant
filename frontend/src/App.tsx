import { useState, useEffect, useCallback } from 'react';
import { Chat } from './pages/Chat';
import { Knowledge } from './pages/Knowledge';
import { DocumentDetail } from './pages/DocumentDetail';
import { Retrieval } from './pages/Retrieval';

type Page = 'chat' | 'knowledge' | 'document-detail' | 'retrieval';

interface AppState {
  page: Page;
  documentId?: string;
}

function getStateFromHash(): AppState {
  const hash = window.location.hash.replace('#', '');
  if (hash.startsWith('knowledge/document/')) {
    const documentId = hash.replace('knowledge/document/', '');
    if (documentId) {
      return { page: 'document-detail', documentId };
    }
  }
  if (hash === 'knowledge') {
    return { page: 'knowledge' };
  }
  if (hash === 'retrieval') {
    return { page: 'retrieval' };
  }
  return { page: 'chat' };
}

function App() {
  const [state, setState] = useState<AppState>(getStateFromHash);

  const handleHashChange = useCallback(() => {
    setState(getStateFromHash());
  }, []);

  useEffect(() => {
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [handleHashChange]);

  const navigateTo = useCallback((target: Page, documentId?: string) => {
    if (target === 'document-detail' && documentId) {
      window.location.hash = `knowledge/document/${documentId}`;
    } else if (target === 'knowledge') {
      window.location.hash = 'knowledge';
    } else if (target === 'retrieval') {
      window.location.hash = 'retrieval';
    } else {
      window.location.hash = '';
    }
  }, []);

  const handleBackToKnowledge = useCallback(() => {
    window.location.hash = 'knowledge';
  }, []);

  return (
    <>
      <nav className="app-nav">
        <button
          type="button"
          className={`app-nav__link ${state.page === 'chat' ? 'app-nav__link--active' : ''}`}
          onClick={() => navigateTo('chat')}
        >
          <span className="app-nav__icon" aria-hidden="true">&#x1F4AC;</span>
          Chat
        </button>
        <button
          type="button"
          className={`app-nav__link ${(state.page === 'knowledge' || state.page === 'document-detail') ? 'app-nav__link--active' : ''}`}
          onClick={() => navigateTo('knowledge')}
        >
          <span className="app-nav__icon" aria-hidden="true">&#x1F4C1;</span>
          Knowledge
        </button>
        <button
          type="button"
          className={`app-nav__link ${state.page === 'retrieval' ? 'app-nav__link--active' : ''}`}
          onClick={() => navigateTo('retrieval')}
        >
          <span className="app-nav__icon" aria-hidden="true">&#x1F50D;</span>
          Retrieval
        </button>
      </nav>
      {state.page === 'chat' && <Chat />}
      {state.page === 'knowledge' && <Knowledge />}
      {state.page === 'document-detail' && state.documentId && (
        <DocumentDetail documentId={state.documentId} onBack={handleBackToKnowledge} />
      )}
      {state.page === 'retrieval' && <Retrieval />}
    </>
  );
}

export default App;