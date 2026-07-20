export type ConfidenceLevel = 'high' | 'medium' | 'low';

interface SourceBadgeProps {
  similarity: number;
}

function getConfidenceLevel(similarity: number): ConfidenceLevel {
  if (similarity >= 0.85) return 'high';
  if (similarity >= 0.7) return 'medium';
  return 'low';
}

const confidenceLabels: Record<ConfidenceLevel, string> = {
  high: 'High Confidence',
  medium: 'Med Confidence',
  low: 'Low Confidence',
};

const confidenceIcons: Record<ConfidenceLevel, string> = {
  high: '\u25B2',
  medium: '\u25A0',
  low: '\u25BC',
};

export function SourceBadge({ similarity }: SourceBadgeProps) {
  const level = getConfidenceLevel(similarity);
  const pct = `${(similarity * 100).toFixed(1)}%`;

  return (
    <span className={`source-badge source-badge--${level}`} title={`${confidenceLabels[level]}: ${pct}`}>
      <span className="source-badge__icon" aria-hidden="true">
        {confidenceIcons[level]}
      </span>
      {pct}
    </span>
  );
}