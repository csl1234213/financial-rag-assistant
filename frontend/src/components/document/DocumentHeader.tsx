import type { DocumentDetail } from '../../types/knowledge';

interface DocumentHeaderProps {
  document: DocumentDetail;
  onBack: () => void;
}

const statusLabels: Record<string, string> = {
  indexed: 'Indexed',
  processing: 'Processing',
  failed: 'Failed',
};

const statusIcons: Record<string, string> = {
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

export function DocumentHeader({ document, onBack }: DocumentHeaderProps) {
  return (
    <header className="doc-detail-header">
      <button
        type="button"
        className="doc-detail-header__back"
        onClick={onBack}
        aria-label="Back to Knowledge Workspace"
      >
        <span className="doc-detail-header__back-icon" aria-hidden="true">
          &#8592;
        </span>
        Back to Documents
      </button>

      <div className="doc-detail-header__main">
        <div className="doc-detail-header__icon">
          <span className="doc-detail-header__icon-text">PDF</span>
        </div>

        <div className="doc-detail-header__info">
          <h1 className="doc-detail-header__filename">{document.filename}</h1>

          <div className="doc-detail-header__meta">
            <span className="doc-detail-header__meta-item">
              <span className="doc-detail-header__meta-label">Company</span>
              <span className="doc-detail-header__meta-value">{document.company}</span>
            </span>
            <span className="doc-detail-header__meta-divider" />
            <span className="doc-detail-header__meta-item">
              <span className="doc-detail-header__meta-label">Pages</span>
              <span className="doc-detail-header__meta-value">{document.pages}</span>
            </span>
            <span className="doc-detail-header__meta-divider" />
            <span className="doc-detail-header__meta-item">
              <span className="doc-detail-header__meta-label">Status</span>
              <span className={`doc-detail-header__status doc-detail-header__status--${document.status}`}>
                <span className="doc-detail-header__status-icon" aria-hidden="true">
                  {statusIcons[document.status]}
                </span>
                {statusLabels[document.status]}
              </span>
            </span>
            {document.size && (
              <>
                <span className="doc-detail-header__meta-divider" />
                <span className="doc-detail-header__meta-item">
                  <span className="doc-detail-header__meta-label">Size</span>
                  <span className="doc-detail-header__meta-value">{document.size}</span>
                </span>
              </>
            )}
          </div>

          <div className="doc-detail-header__date">
            Uploaded {formatDate(document.uploadedAt)}
          </div>
        </div>
      </div>
    </header>
  );
}