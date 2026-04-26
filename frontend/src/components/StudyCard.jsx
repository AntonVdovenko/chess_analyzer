import React from 'react';
import { formatPercentage, formatDate } from '../utils';

export default function StudyCard({ plan, onExpand }) {
  const getPriorityColor = (priority) => {
    if (priority >= 0.8) return '#d32f2f'; // red
    if (priority >= 0.6) return '#f57c00'; // orange
    if (priority >= 0.4) return '#fbc02d'; // yellow
    return '#388e3c'; // green
  };

  const getPriorityLabel = (priority) => {
    if (priority >= 0.8) return 'Critical';
    if (priority >= 0.6) return 'High';
    if (priority >= 0.4) return 'Medium';
    return 'Low';
  };

  const priorityScore = plan.priority_score || 0;
  const priorityColor = getPriorityColor(priorityScore);
  const priorityLabel = getPriorityLabel(priorityScore);

  return (
    <div className="study-card">
      <div className="study-card-header">
        <h3>{plan.weakness_name || plan.weakness_id || 'Weakness Pattern'}</h3>
        <span
          className="priority-badge"
          style={{
            backgroundColor: priorityColor,
            color: 'white',
            padding: '4px 8px',
            borderRadius: '4px',
            fontSize: '12px',
            fontWeight: 'bold',
          }}
        >
          {priorityLabel}
        </span>
      </div>

      <div className="study-card-content">
        <div className="study-card-stat">
          <span className="stat-label">Status</span>
          <span className="stat-value">{plan.status}</span>
        </div>

        {plan.weakness_type && (
          <div className="study-card-stat">
            <span className="stat-label">Type</span>
            <span className="stat-value">{plan.weakness_type}</span>
          </div>
        )}

        <div className="study-card-stat">
          <span className="stat-label">Related Concepts</span>
          <span className="stat-value">{plan.concept_count || 0}</span>
        </div>

        <div className="study-card-stat">
          <span className="stat-label">Priority Score</span>
          <span className="stat-value">{formatPercentage(priorityScore)}</span>
        </div>

        <div className="study-card-stat">
          <span className="stat-label">Created</span>
          <span className="stat-value">
            {formatDate(plan.created_at)}
          </span>
        </div>
      </div>

      <div className="study-card-footer">
        <button
          className="btn-expand"
          onClick={onExpand}
        >
          View Details →
        </button>
      </div>
    </div>
  );
}
