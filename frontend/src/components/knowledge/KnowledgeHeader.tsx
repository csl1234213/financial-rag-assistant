interface KnowledgeHeaderProps {
  documentCount: number;
  indexedCount: number;
  processingCount: number;
  failedCount: number;
  onRefresh?: () => void;
  refreshing?: boolean;
}

export function KnowledgeHeader({
  documentCount,
  indexedCount,
  processingCount,
  failedCount,
  onRefresh,
  refreshing = false,
}: KnowledgeHeaderProps) {
  return (
    <div className="knowledge-header">
      <div className="knowledge-header__titles">
        <div className="knowledge-header__title-row">
          <h1 className="knowledge-header__title">Knowledge Workspace</h1>
          {onRefresh && (
            <button
              type="button"
              className={`knowledge-header__refresh ${refreshing ? 'knowledge-header__refresh--spinning' : ''}`}
              onClick={onRefresh}
              disabled={refreshing}
              title="Refresh knowledge base"
              aria-label="Refresh knowledge base"
            >
              <span className="knowledge-header__refresh-icon" aria-hidden="true">
                &#x21BB;
              </span>
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
          )}
        </div>
        <p className="knowledge-header__subtitle">Financial Document Center</p>
      </div>

      <div className="knowledge-header__stats">
        <div className="knowledge-header__stat">
          <span className="knowledge-header__stat-value">{documentCount}</span>
          <span className="knowledge-header__stat-label">Total</span>
        </div>
        <div className="knowledge-header__stat knowledge-header__stat--indexed">
          <span className="knowledge-header__stat-value">{indexedCount}</span>
          <span className="knowledge-header__stat-label">Indexed</span>
        </div>
        {processingCount > 0 && (
          <div className="knowledge-header__stat knowledge-header__stat--processing">
            <span className="knowledge-header__stat-value">{processingCount}</span>
            <span className="knowledge-header__stat-label">Processing</span>
          </div>
        )}
        {failedCount > 0 && (
          <div className="knowledge-header__stat knowledge-header__stat--failed">
            <span className="knowledge-header__stat-value">{failedCount}</span>
            <span className="knowledge-header__stat-label">Failed</span>
          </div>
        )}
      </div>
    </div>
  );
}