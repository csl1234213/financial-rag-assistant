import { ChunkCard } from './ChunkCard';
import type { DocumentChunk } from '../../types/knowledge';

interface ChunkListProps {
  chunks: DocumentChunk[];
  loading: boolean;
}

export function ChunkList({ chunks, loading }: ChunkListProps) {
  if (loading) {
    return (
      <div className="chunk-list chunk-list--loading">
        <div className="chunk-list__skeleton">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="chunk-skeleton">
              <div className="chunk-skeleton__header" />
              <div className="chunk-skeleton__line chunk-skeleton__line--long" />
              <div className="chunk-skeleton__line chunk-skeleton__line--medium" />
              <div className="chunk-skeleton__line chunk-skeleton__line--short" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (chunks.length === 0) {
    return (
      <div className="chunk-list chunk-list--empty">
        <span className="chunk-list__empty-icon" aria-hidden="true">&#x1F4C4;</span>
        <p className="chunk-list__empty-title">No chunks available</p>
        <p className="chunk-list__empty-hint">
          This document has not been chunked yet or the chunks are unavailable.
        </p>
      </div>
    );
  }

  return (
    <div className="chunk-list">
      {chunks.map((chunk) => (
        <ChunkCard key={chunk.index} chunk={chunk} />
      ))}
    </div>
  );
}