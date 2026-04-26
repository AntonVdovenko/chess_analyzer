export default function PatternDetail({ pattern, onBack }) {
  const frequency = pattern.frequency || 0;
  const avgLoss = pattern.average_eval_loss ?? pattern.avg_loss ?? 0;
  const name = pattern.name ?? pattern.pattern_name ?? `Pattern ${pattern.id}`;
  const weaknessType = pattern.weakness_type ?? pattern.type ?? 'Unknown';

  let priority = 'medium';
  if (frequency > 10 && avgLoss > 200) {
    priority = 'critical';
  } else if (frequency > 5 || avgLoss > 150) {
    priority = 'high';
  }

  return (
    <div className="pattern-detail">
      <button className="btn-back" onClick={onBack}>
        ← Back to Patterns
      </button>
      <h2>{name}</h2>
      <div className="detail-grid">
        <div className="detail-card">
          <h3>Overview</h3>
          <div className="detail-row">
            <span className="label">Type:</span>
            <span className="value">{weaknessType}</span>
          </div>
          <div className="detail-row">
            <span className="label">Priority:</span>
            <span className="value" style={{ textTransform: 'capitalize' }}>
              {priority}
            </span>
          </div>
          <div className="detail-row">
            <span className="label">Frequency:</span>
            <span className="value">{frequency} times</span>
          </div>
          <div className="detail-row">
            <span className="label">Avg Loss:</span>
            <span className="value">{avgLoss.toFixed(0)} centipawns</span>
          </div>
        </div>

        <div className="detail-card">
          <h3>Impact Analysis</h3>
          <div className="detail-row">
            <span className="label">Total Loss:</span>
            <span className="value">
              {(frequency * avgLoss).toFixed(0)} cp
            </span>
          </div>
          <div className="detail-row">
            <span className="label">Games Affected:</span>
            <span className="value">
              {pattern.game_ids ? pattern.game_ids.length : 0}
            </span>
          </div>
          <div className="detail-row">
            <span className="label">Study Priority:</span>
            <span
              className="value"
              style={{
                padding: '0.25rem 0.75rem',
                borderRadius: '4px',
                backgroundColor:
                  priority === 'critical'
                    ? '#ffcdd2'
                    : priority === 'high'
                      ? '#ffe0b2'
                      : '#c8e6c9',
                color:
                  priority === 'critical'
                    ? '#c62828'
                    : priority === 'high'
                      ? '#e65100'
                      : '#1b5e20',
              }}
            >
              {priority.charAt(0).toUpperCase() + priority.slice(1)}
            </span>
          </div>
        </div>

        <div className="detail-card">
          <h3>Recommendations</h3>
          <div className="detail-row">
            <span className="label">Study Focus:</span>
            <span className="value">
              {priority === 'critical'
                ? 'Immediate attention required'
                : priority === 'high'
                  ? 'High priority study'
                  : 'Regular practice'}
            </span>
          </div>
          <div className="detail-row">
            <span className="label">Progress:</span>
            <span className="value">
              {frequency > 20
                ? 'Frequently recurring'
                : frequency > 10
                  ? 'Moderate occurrence'
                  : 'Occasional issue'}
            </span>
          </div>
          <div className="detail-row">
            <span className="label">Next Steps:</span>
            <span className="value">
              {avgLoss > 200
                ? 'Review tactical themes'
                : avgLoss > 100
                  ? 'Practice position evaluation'
                  : 'Study typical positions'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
