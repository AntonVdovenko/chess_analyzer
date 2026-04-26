import React, { useState } from 'react';
import { chessAPI } from '../api';
import '../styles/Dashboard.css';

export default function Dashboard() {
  const [username, setUsername] = useState('');
  const [stats, setStats] = useState(null);
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyze = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await chessAPI.analyzeGames(username, 100);
      console.log('Analysis started:', result);

      const statsData = await chessAPI.getStats(username);
      setStats(statsData);

      const patternsData = await chessAPI.getPatterns(username);
      setPatterns(patternsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-container">
      <h1>Chess Analyzer</h1>

      <form onSubmit={handleAnalyze} className="analysis-form">
        <input
          type="text"
          placeholder="Enter chess.com username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <button type="submit" disabled={loading || !username}>
          {loading ? 'Analyzing...' : 'Analyze Games'}
        </button>
      </form>

      {error && <div className="error-message">Error: {error}</div>}

      {stats && (
        <div className="stats-section">
          <h2>Statistics</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <h3>Total Games</h3>
              <p>{stats.total_games}</p>
            </div>
            <div className="stat-card">
              <h3>Overall Accuracy</h3>
              <p>{stats.overall_accuracy.toFixed(1)}%</p>
            </div>
          </div>

          <h3>Accuracy by Phase</h3>
          <ul>
            {Object.entries(stats.accuracy_by_phase || {}).map(([phase, acc]) => (
              <li key={phase}>{phase}: {acc.toFixed(1)}%</li>
            ))}
          </ul>

          {stats.weakness_summary && stats.weakness_summary.length > 0 && (
            <>
              <h3>Top Weaknesses</h3>
              <ul>
                {stats.weakness_summary.map((w, idx) => (
                  <li key={idx}>{w.weakness}: {w.frequency} occurrences</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {patterns.length > 0 && (
        <div className="patterns-section">
          <h2>Patterns Found</h2>
          {patterns.map((p) => {
            const name = p.name ?? p.pattern_name ?? `Pattern ${p.id}`;
            const weaknessType = p.weakness_type ?? p.type ?? 'Unknown';
            const averageEvalLoss = p.average_eval_loss ?? p.avg_loss ?? 0;

            return (
              <div key={p.id} className="pattern-card">
                <h3>{name}</h3>
                <p>Type: {weaknessType}</p>
                <p>Frequency: {p.frequency ?? 0}</p>
                <p>Avg Loss: {Number(averageEvalLoss).toFixed(1)}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
