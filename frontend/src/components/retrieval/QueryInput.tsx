import { useState, useCallback, type FormEvent } from 'react';

interface QueryInputProps {
  onSubmit: (query: string) => void;
  loading: boolean;
}

export function QueryInput({ onSubmit, loading }: QueryInputProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      const trimmed = query.trim();
      if (!trimmed || loading) return;
      onSubmit(trimmed);
    },
    [query, loading, onSubmit],
  );

  return (
    <form className="retrieval-query" onSubmit={handleSubmit}>
      <div className="retrieval-query__input-row">
        <span className="retrieval-query__icon" aria-hidden="true">
          &#x1F50D;
        </span>
        <input
          type="text"
          className="retrieval-query__input"
          placeholder='e.g. "Tesla revenue growth in 2025"'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
          aria-label="Retrieval query"
        />
        <button
          type="submit"
          className="retrieval-query__button"
          disabled={!query.trim() || loading}
        >
          {loading ? (
            <>
              <span className="retrieval-query__button-spinner" aria-hidden="true" />
              Searching...
            </>
          ) : (
            <>
              <span className="retrieval-query__button-icon" aria-hidden="true">
                &#x2192;
              </span>
              Search
            </>
          )}
        </button>
      </div>
      <p className="retrieval-query__hint">
        Top 5 most relevant chunks will be retrieved from the knowledge base.
      </p>
    </form>
  );
}