import type { DocumentDetail } from '../../types/knowledge';

interface DocumentStatsProps {
  document: DocumentDetail;
}

const embeddingStatusLabels: Record<string, string> = {
  completed: 'Completed',
  pending: 'Pending',
  failed: 'Failed',
};

const vectorStatusLabels: Record<string, string> = {
  stored: 'Stored',
  pending: 'Pending',
  failed: 'Failed',
};

const embeddingStatusIcons: Record<string, string> = {
  completed: '\u2713',
  pending: '\u23F3',
  failed: '\u2717',
};

const vectorStatusIcons: Record<string, string> = {
  stored: '\u2713',
  pending: '\u23F3',
  failed: '\u2717',
};

export function DocumentStats({ document }: DocumentStatsProps) {
  return (
    <section className="doc-stats" aria-labelledby="doc-stats-title">
      <h2 id="doc-stats-title" className="doc-stats__title">
        Document Statistics
      </h2>

      <div className="doc-stats__grid">
        <div className="doc-stats__card">
          <span className="doc-stats__card-icon" aria-hidden="true">
            &#x1F4CB;
          </span>
          <div className="doc-stats__card-body">
            <span className="doc-stats__card-value">{document.chunkCount}</span>
            <span className="doc-stats__card-label">Chunks</span>
          </div>
        </div>

        <div className={`doc-stats__card doc-stats__card--${document.embeddingStatus}`}>
          <span className="doc-stats__card-icon" aria-hidden="true">
            {embeddingStatusIcons[document.embeddingStatus]}
          </span>
          <div className="doc-stats__card-body">
            <span className="doc-stats__card-value doc-stats__card-value--status">
              {embeddingStatusLabels[document.embeddingStatus]}
            </span>
            <span className="doc-stats__card-label">Embedding Status</span>
          </div>
        </div>

        <div className={`doc-stats__card doc-stats__card--${document.vectorStatus}`}>
          <span className="doc-stats__card-icon" aria-hidden="true">
            {vectorStatusIcons[document.vectorStatus]}
          </span>
          <div className="doc-stats__card-body">
            <span className="doc-stats__card-value doc-stats__card-value--status">
              {vectorStatusLabels[document.vectorStatus]}
            </span>
            <span className="doc-stats__card-label">Vector Status</span>
          </div>
        </div>
      </div>
    </section>
  );
}