const LABELS = {
  FUNCTIONAL: 'FUNCIONAL',
  IN_DEVELOPMENT: 'EN DESARROLLO',
  MATURE_CONCEPT: 'CONCEPTO MADURO',
};

export default function StatusBadge({ status }) {
  const label = LABELS[status];
  if (!label) return null;
  return <span className={`status-badge status-badge--${status.toLowerCase()}`}>{label}</span>;
}
