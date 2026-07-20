export type StepStatus = 'completed' | 'running' | 'pending';

interface StatusBadgeProps {
  status: StepStatus;
}

const statusLabels: Record<StepStatus, string> = {
  completed: 'Completed',
  running: 'Running',
  pending: 'Pending',
};

const statusIcons: Record<StepStatus, string> = {
  completed: '\u2713',
  running: '\u25CF',
  pending: '\u25CB',
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-badge--${status}`} aria-label={statusLabels[status]}>
      <span className="status-badge__icon" aria-hidden="true">
        {statusIcons[status]}
      </span>
      {statusLabels[status]}
    </span>
  );
}