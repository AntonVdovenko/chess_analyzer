export default function PatternList({ patterns, onSelectPattern, showAdvanced }) {
  if (patterns.length === 0) {
    return <div className="no-patterns">No patterns found</div>;
  }

  return (
    <div className="pattern-list">
      <h2>Weakness Patterns ({patterns.length})</h2>
      {patterns.map((pattern) => {
        // Determine priority based on frequency and loss
        let priority = 'medium';
        const frequency = pattern.frequency || 0;
        const avgLoss = pattern.average_eval_loss ?? pattern.avg_loss ?? 0;
        const name = pattern.name ?? pattern.pattern_name ?? `Pattern ${pattern.id}`;

        if (frequency > 10 && avgLoss > 200) {
          priority = 'critical';
        } else if (frequency > 5 || avgLoss > 150) {
          priority = 'high';
        }

        return (
          <div
            key={pattern.id}
            className="pattern-card"
            onClick={() => onSelectPattern(pattern)}
            role="button"
            tabIndex={0}
            onKeyPress={(e) => {
              if (e.key === 'Enter') onSelectPattern(pattern);
            }}
          >
            <div className="pattern-header">
              <h3>{name}</h3>
              <span className={`priority ${priority}`}>
                {priority.charAt(0).toUpperCase() + priority.slice(1)}
              </span>
            </div>
            <div className="pattern-stats">
              <div className="stat">
                <span className="label">Frequency:</span>
                <span className="value">{frequency}</span>
              </div>
              <div className="stat">
                <span className="label">Avg Loss:</span>
                <span className="value">{avgLoss.toFixed(0)} cp</span>
              </div>
            </div>
            {showAdvanced && (
              <div className="advanced-info">
                <span>🔸 Unusual moves tracked</span>
                <span>🔴 Anomalies detected</span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
