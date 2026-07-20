import type { DocumentStatus } from '../../types/knowledge';

interface DocumentCardProps {
  id: string;
  filename: string;
  company: string;
  pages: number;
  status: DocumentStatus;
  size?: string;
  uploadedAt: string;
  onClick?: (id: string) => void;
}

const statusLabels: Record<DocumentStatus, string> = {
  indexed: 'Indexed',
  processing: 'Processing',
  failed: 'Failed',
};

const statusIcons: Record<DocumentStatus, string> = {
  indexed: '\u2713',
  processing: '\u21BB',
  failed: '\u2717',
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function DocumentCard({
  id,
  filename,
  company,
  pages,
  status,
  size,
  uploadedAt,
  onClick,
}: DocumentCardProps) {
  return (
    <article
      className="doc-card"
      onClick={() => onClick?.(id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.(id);
        }
      }}
    >
      <div className="doc-card__icon">
        <span className="doc-card__icon-text">PDF</span>
      </div>

      <div className="doc-card__info">
        <div className="doc-card__header">
          <span className="doc-card__filename">{filename}</span>
          <span className={`doc-card__status doc-card__status--${status}`}>
            <span className="doc-card__status-icon" aria-hidden="true">
              {statusIcons[status]}
            </span>
            {statusLabels[status]}
          </span>
        </div>

        <div className="doc-card__meta">
          <span className="doc-card__meta-item">
            <span className="doc-card__meta-label">Company</span>
            <span className="doc-card__meta-value">{company}</span>
          </span>
          <span className="doc-card__meta-divider" />
          <span className="doc-card__meta-item">
            <span className="doc-card__meta-label">Pages</span>
            <span className="doc-card__meta-value">{pages}</span>
          </span>
          {size && (
            <>
              <span className="doc-card__meta-divider" />
              <span className="doc-card__meta-item">
                <span className="doc-card__meta-label">Size</span>
                <span className="doc-card__meta-value">{size}</span>
              </span>
            </>
          )}
        </div>

        <div className="doc-card__footer">
          <span className="doc-card__date">Uploaded {formatDate(uploadedAt)}</span>
        </div>
      </div>
    </article>
  );
}