import { useState, useMemo, useEffect, useCallback } from 'react';
import { Header } from '../components/layout/Header';
import { KnowledgeHeader } from '../components/knowledge/KnowledgeHeader';
import { KnowledgeList } from '../components/knowledge/KnowledgeList';
import { UploadPanel } from '../components/knowledge/UploadPanel';
import { getDocuments, refreshKnowledge, uploadDocument } from '../api/knowledge';
import type { KnowledgeDocument } from '../types/knowledge';

export function Knowledge() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Connection Error';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const docs = await refreshKnowledge();
      setDocuments(docs);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Connection Error';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleUpload = useCallback(async (file: File) => {
    await uploadDocument(file);
    await loadDocuments();
  }, [loadDocuments]);

  const filteredDocs = useMemo(() => {
    if (!searchQuery.trim()) return documents;
    const q = searchQuery.toLowerCase();
    return documents.filter(
      (doc) =>
        doc.filename.toLowerCase().includes(q) ||
        (doc.company ?? '').toLowerCase().includes(q),
    );
  }, [documents, searchQuery]);

  const indexedCount = documents.filter((d) => d.status === 'indexed').length;
  const processingCount = documents.filter((d) => d.status === 'processing').length;
  const failedCount = documents.filter((d) => d.status === 'failed').length;

  return (
    <div className="app-layout">
      <Header
        title="Financial RAG Assistant"
        subtitle="Knowledge Workspace"
        connected
      />

      <div className="knowledge-layout">
        <div className="knowledge-layout__header">
          <KnowledgeHeader
            documentCount={documents.length}
            indexedCount={indexedCount}
            processingCount={processingCount}
            failedCount={failedCount}
            onRefresh={handleRefresh}
            refreshing={loading}
          />

          <div className="knowledge-search">
            <span className="knowledge-search__icon" aria-hidden="true">
              &#x1F50D;
            </span>
            <input
              type="text"
              className="knowledge-search__input"
              placeholder="Search documents by name or company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search documents"
            />
          </div>
        </div>

        <div className="knowledge-layout__body">
          <main className="knowledge-main">
            <section className="knowledge-section" aria-labelledby="documents-title">
              <h2 id="documents-title" className="knowledge-section__title">
                Documents
              </h2>
              {error && (
                <div className="knowledge-error" role="alert">
                  <span className="knowledge-error__icon" aria-hidden="true">&#x26A0;</span>
                  {error}
                </div>
              )}
              <KnowledgeList documents={filteredDocs} onDocumentClick={(id) => {
                window.location.hash = `knowledge/document/${id}`;
              }} />
            </section>
          </main>

          <aside className="knowledge-sidebar">
            <UploadPanel onUploadSuccess={handleUpload} />
          </aside>
        </div>
      </div>
    </div>
  );
}