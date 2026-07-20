import { DocumentCard } from './DocumentCard';
import type { KnowledgeDocument } from '../../types/knowledge';

interface KnowledgeListProps {
  documents: KnowledgeDocument[];
  onDocumentClick?: (id: string) => void;
}

export function KnowledgeList({ documents, onDocumentClick }: KnowledgeListProps) {
  if (documents.length === 0) {
    return (
      <div className="knowledge-empty">
        <span className="knowledge-empty__icon" aria-hidden="true">📂</span>
        <p className="knowledge-empty__title">No documents yet</p>
        <p className="knowledge-empty__hint">
          Upload a PDF document to add it to the knowledge base.
        </p>
      </div>
    );
  }

  return (
    <div className="knowledge-list">
      {documents.map((doc) => (
        <DocumentCard
          key={doc.id}
          id={doc.id}
          filename={doc.filename}
          company={doc.company}
          pages={doc.pages}
          status={doc.status}
          size={doc.size}
          uploadedAt={doc.uploadedAt}
          onClick={onDocumentClick}
        />
      ))}
    </div>
  );
}