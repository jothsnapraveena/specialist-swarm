const ICONS = { pending: '○', running: '●', passed: '✓', rejected: '✗', hold: '⚑' };
const LABELS = { pending: 'Pending', running: 'Running…', passed: 'Passed', rejected: 'Rejected', hold: 'On Hold' };

export default function StageRow({ name, status, summary, flags, onViewReport }) {
  const icon = ICONS[status] ?? '○';
  const label = LABELS[status] ?? status;

  return (
    <div className={`stage-row stage-${status}`}>
      <span className="stage-icon">{icon}</span>
      <div className="stage-body">
        <div className="stage-header">
          <span className="stage-name">{name}</span>
          <span className="stage-badge">{summary || label}</span>
        </div>
        {flags && flags.length > 0 && (
          <ul className="stage-flags">
            {flags.map((f, i) => (
              <li key={i} className={`flag flag-${f.severity}`}>
                <span className="flag-severity">{f.severity.toUpperCase()}</span> {f.message}
              </li>
            ))}
          </ul>
        )}
        {onViewReport && (
          <button className="link-btn" onClick={onViewReport}>
            View full flag report
          </button>
        )}
      </div>
    </div>
  );
}
