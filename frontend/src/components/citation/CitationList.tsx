import { CitationCard } from './CitationCard';
import type { Citation } from '../../types/chat';

interface CitationListProps {
  citations: Citation[];
  title?: string;
  emptyMessage?: string;
}

export function CitationList({
  citations,
  title = 'Evidence',
  emptyMessage = 'Evidence will appear after analysis.',
}: CitationListProps) {
  const hasCitations = citations.length > 0;

  return (
    <section className="citation-list-panel" aria-labelledby="citation-list-title">
      <div className="citation-list-panel__header">
        <h2 id="citation-list-title" className="citation-list-panel__title">
          {title}
        </h2>
        {hasCitations && (
          <span className="citation-list-panel__count">
            {citations.length} source{citations.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {!hasCitations && (
        <p className="citation-list-panel__empty">{emptyMessage}</p>
      )}

      {hasCitations && (
        <div className="citation-list">
          {citations.map((citation, index) => (
            <CitationCard
              key={`${citation.filename}-${index}`}
              citation={citation}
              index={index}
            />
          ))}
        </div>
      )}
    </section>
  );
}