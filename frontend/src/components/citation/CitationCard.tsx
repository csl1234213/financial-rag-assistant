import { useState } from 'react';
import { SourceBadge } from './SourceBadge';
import type { Citation } from '../../types/chat';

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  const sourceName = citation.source.replace(/\.pdf$/i, '') || `Source ${index + 1}`;
  const snippet = citation.preview;

  return (
    <article className="citation-card">
      <div className="citation-card__header">
        <div className="citation-card__source-info">
          <span className="citation-card__index">[{index + 1}]</span>
          <span className="citation-card__source-name">{sourceName}</span>
          {citation.chunk_id && (
            <span className="citation-card__page">{citation.chunk_id}</span>
          )}
        </div>
        <SourceBadge similarity={citation.similarity} />
      </div>

      <div className={`citation-card__body ${expanded ? 'citation-card__body--expanded' : ''}`}>
        <p className="citation-card__snippet">{snippet}</p>
      </div>

      <div className="citation-card__footer">
        <span className="citation-card__meta">
          <span className="citation-card__meta-label">Source</span>
          <span className="citation-card__meta-value">{citation.source}</span>
        </span>
        <button
          type="button"
          className="citation-card__expand"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
        >
          {expanded ? 'Collapse' : 'View Context'}
        </button>
      </div>
    </article>
  );
}
