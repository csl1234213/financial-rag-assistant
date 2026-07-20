import type { RetrievalMetrics } from '../../types/api';

interface RetrievalMetricsProps {
  metrics: RetrievalMetrics;
}

function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

export function RetrievalMetricsPanel({ metrics }: RetrievalMetricsProps) {
  return (
    <section className="retrieval-metrics" aria-labelledby="retrieval-metrics-title">
      <h2 id="retrieval-metrics-title" className="retrieval-metrics__title">
        Retrieval Metrics
      </h2>

      <div className="retrieval-metrics__grid">
        <div className="retrieval-metrics__card">
          <span className="retrieval-metrics__card-icon" aria-hidden="true">
            &#x23F1;
          </span>
          <div className="retrieval-metrics__card-body">
            <span className="retrieval-metrics__card-value">
              {formatLatency(metrics.latencyMs)}
            </span>
            <span className="retrieval-metrics__card-label">Latency</span>
          </div>
        </div>

        <div className="retrieval-metrics__card">
          <span className="retrieval-metrics__card-icon" aria-hidden="true">
            &#x1F4CB;
          </span>
          <div className="retrieval-metrics__card-body">
            <span className="retrieval-metrics__card-value">{metrics.chunkCount}</span>
            <span className="retrieval-metrics__card-label">Chunks Retrieved</span>
          </div>
        </div>

        <div className="retrieval-metrics__card">
          <span className="retrieval-metrics__card-icon" aria-hidden="true">
            &#x2699;
          </span>
          <div className="retrieval-metrics__card-body">
            <span className="retrieval-metrics__card-value retrieval-metrics__card-value--type">
              {metrics.retrieverType}
            </span>
            <span className="retrieval-metrics__card-label">Retriever Type</span>
          </div>
        </div>
      </div>
    </section>
  );
}