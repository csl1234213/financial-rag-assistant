import { useState, useMemo, useEffect, useCallback } from 'react';
import { Header } from '../components/layout/Header';
import { KnowledgeHeader } from '../components/knowledge/KnowledgeHeader';
import { KnowledgeList } from '../components/knowledge/KnowledgeList';
import { UploadPanel } from '../components/knowledge/UploadPanel';
import {
  deleteDocument,
  getDocuments,
  refreshKnowledge,
  uploadDocument,
} from '../api/knowledge';
import { ApiClientError } from '../api/client';
import { useLanguage } from '../i18n/LanguageContext';
import { Icon } from '../components/ui/Icon';
import type { KnowledgeDocument } from '../types/knowledge';

export function Knowledge() {
  const { t } = useLanguage();
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [deletingDocumentId, setDeletingDocumentId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : t.knowledge.connectionError;
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [t.knowledge.connectionError]);

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
      const message = err instanceof Error ? err.message : t.knowledge.connectionError;
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [t.knowledge.connectionError]);

  const handleUpload = useCallback(async (file: File) => {
    setNotice(null);
    try {
      await uploadDocument(file);
      await loadDocuments();
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        if (err.status === 400) {
          throw new Error(t.upload.invalidDocument);
        }
        if (err.status === 409) {
          throw new Error(t.upload.duplicateDocument);
        }
        if (err.status === 413) {
          throw new Error(t.upload.fileTooLarge);
        }
        if (err.status === 429) {
          throw new Error(t.upload.uploadLimitExceeded);
        }
      }
      throw err;
    }
  }, [
    loadDocuments,
    t.upload.duplicateDocument,
    t.upload.fileTooLarge,
    t.upload.invalidDocument,
    t.upload.uploadLimitExceeded,
  ]);

  const handleDelete = useCallback(async (document: KnowledgeDocument) => {
    if (!window.confirm(t.knowledge.deleteConfirm(document.filename))) {
      return;
    }

    setDeletingDocumentId(document.id);
    setError(null);
    setNotice(null);
    try {
      await deleteDocument(document.id);
      setDocuments((current) => current.filter((item) => item.id !== document.id));
      setNotice(t.knowledge.deleteSuccess(document.filename));
    } catch (err: unknown) {
      const message = err instanceof Error
        ? err.message
        : t.knowledge.deleteFailed;
      setError(message);
    } finally {
      setDeletingDocumentId(null);
    }
  }, [
    t.knowledge.deleteConfirm,
    t.knowledge.deleteFailed,
    t.knowledge.deleteSuccess,
  ]);

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
        title={t.header.title}
        subtitle={t.header.knowledgeSubtitle}
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
              <Icon name="search" />
            </span>
            <input
              type="text"
              className="knowledge-search__input"
              placeholder={t.knowledge.searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label={t.knowledge.searchLabel}
            />
          </div>
        </div>

        <div className="knowledge-layout__body">
          <main className="knowledge-main">
            <section className="knowledge-section" aria-labelledby="documents-title">
              <h2 id="documents-title" className="knowledge-section__title">
                {t.knowledge.documents}
              </h2>
              {error && (
                <div className="knowledge-error" role="alert">
                  <span className="knowledge-error__icon" aria-hidden="true">&#x26A0;</span>
                  {error}
                </div>
              )}
              {notice && (
                <div className="knowledge-success" role="status">
                  <span aria-hidden="true">&#x2713;</span>
                  {notice}
                </div>
              )}
              <KnowledgeList
                documents={filteredDocs}
                onDocumentDelete={handleDelete}
                deletingDocumentId={deletingDocumentId}
              />
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
