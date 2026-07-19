import type { Citation } from '../types/chat';

interface EvidenceCardProps {
  citation: Citation;
  labels: {
    page: string;
    snippet: string;
    similarity: (score: number) => string;
  };
}

export function EvidenceCard({ citation, labels }: EvidenceCardProps) {
  return (
    <article className="evidence-card">
      <div className="evidence-card__header">
        <strong>{citation.filename}</strong>
        <span>{labels.similarity(citation.similarity)}</span>
      </div>
      <dl className="evidence-card__metadata">
        <div>
          <dt>{labels.page}</dt>
          <dd>{citation.page}</dd>
        </div>
      </dl>
      <p>
        <span className="evidence-card__snippet-label">{labels.snippet}</span>
        {citation.snippet}
      </p>
    </article>
  );
}
