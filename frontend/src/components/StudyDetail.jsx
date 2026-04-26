import React, { useState, useEffect, useCallback } from 'react';
import { chessAPI } from '../api';
import { formatPercentage, formatNumber, formatDate } from '../utils';

export default function StudyDetail({ plan, username, onBack, onMarkStudied }) {
  const [concepts, setConcepts] = useState([]);
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadStudyDetail = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Load concepts for this plan
      const conceptsResponse = await chessAPI.getStudyConcepts(plan.id);
      setConcepts(conceptsResponse.concepts || []);

      // Load games for this plan
      const gamesResponse = await chessAPI.getGamesForStudy(plan.id, true);
      setGames(gamesResponse || []);
    } catch (err) {
      setError(`Failed to load study details: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [plan.id]);

  useEffect(() => {
    loadStudyDetail();
  }, [loadStudyDetail]);

  const handleMarkStudied = async () => {
    try {
      await onMarkStudied(plan.id);
    } catch (err) {
      setError(`Failed to mark as studied: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="study-detail">
        <button className="btn-back" onClick={onBack}>
          ← Back to List
        </button>
        <div className="loading">Loading study details...</div>
      </div>
    );
  }

  return (
    <div className="study-detail">
      <button className="btn-back" onClick={onBack}>
        ← Back to List
      </button>

      <div className="detail-header">
        <h2>{plan.weakness_name || plan.weakness_id || 'Weakness Pattern'}</h2>
        <span className="detail-status">{plan.status}</span>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="detail-content">
        <div className="detail-section">
          <h3>Weakness Information</h3>
          <div className="detail-info">
            <div className="info-row">
              <span className="info-label">Weakness ID</span>
              <span className="info-value">{plan.weakness_id}</span>
            </div>
            {plan.weakness_type && (
              <div className="info-row">
                <span className="info-label">Weakness Type</span>
                <span className="info-value">{plan.weakness_type}</span>
              </div>
            )}
            <div className="info-row">
              <span className="info-label">Priority Score</span>
              <span className="info-value">{formatPercentage(plan.priority_score)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Status</span>
              <span className="info-value">{plan.status}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Created</span>
              <span className="info-value">
                {formatDate(plan.created_at)}
              </span>
            </div>
          </div>
        </div>

        <div className="detail-section">
          <h3>Learning Concepts ({concepts.length})</h3>
          {concepts.length > 0 ? (
            <div className="concepts-grid">
              {concepts.map((concept, idx) => (
                <div key={idx} className="concept-box">
                  <div className="concept-type">{concept.type}</div>
                  <div className="concept-name">{concept.name}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-message">No concepts found for this weakness.</p>
          )}
        </div>

        <div className="detail-section">
          <h3>Games with This Weakness ({games.length})</h3>
          {games.length > 0 ? (
            <div className="games-list">
              {games.map((game) => (
                <div key={game.game_id} className="game-item">
                  <div className="game-result">
                    <span className={`result-badge result-${game.result}`}>
                      {game.result}
                    </span>
                  </div>
                  <div className="game-stats">
                    <div className="game-stat">
                      <span className="stat-label">Accuracy</span>
                      <span className="stat-value">{formatNumber(game.accuracy, 1)}%</span>
                    </div>
                    <div className="game-stat">
                      <span className="stat-label">Eval Loss</span>
                      <span className="stat-value">{formatNumber(game.eval_loss, 1)}</span>
                    </div>
                  </div>
                  <div className="game-fen">
                    <small>{game.position_fen}</small>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-message">No games found for this weakness.</p>
          )}
        </div>
      </div>

      <div className="detail-footer">
        {plan.status !== 'completed' && (
          <button className="btn-mark-studied" onClick={handleMarkStudied}>
            Mark as Studied
          </button>
        )}
        <button className="btn-back-footer" onClick={onBack}>
          Back to List
        </button>
      </div>
    </div>
  );
}
