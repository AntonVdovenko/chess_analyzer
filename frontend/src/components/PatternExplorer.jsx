import React, { useState, useCallback } from 'react';
import { chessAPI } from '../api';
import { formatPercentage } from '../utils';
import PatternFilter from './PatternFilter';
import PatternList from './PatternList';
import PatternDetail from './PatternDetail';
import '../styles/PatternExplorer.css';

export default function PatternExplorer() {
  const [username, setUsername] = useState('');
  const [stats, setStats] = useState(null);
  const [patterns, setPatterns] = useState([]);
  const [selectedPattern, setSelectedPattern] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState({
    type: 'all',
    sortBy: 'frequency',
    minFrequency: 1,
  });
  const [showAdvanced, setShowAdvanced] = useState(false);

  const loadStatsAndPatterns = useCallback(async () => {
    const statsData = await chessAPI.getStats(username);
    setStats(statsData);
    const patternsData = await chessAPI.getPatterns(username);
    setPatterns(patternsData || []);
  }, [username]);

  const handleLoadAnalysis = async (e) => {
    e.preventDefault();
    if (!username) return;
    setLoading(true);
    setError(null);

    try {
      await loadStatsAndPatterns();
      setShowAdvanced(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRunAdvancedAnalysis = async () => {
    if (!username) return;
    setLoading(true);
    setError(null);

    try {
      const result = await chessAPI.startAdvancedAnalysis(username, 100);
      let completed = false;
      let attempts = 0;

      while (!completed && attempts < 60) {
        await new Promise((resolve) => setTimeout(resolve, 5000));
        const status = await chessAPI.getAdvancedAnalysisStatus(result.job_id);
        if (status.status === 'completed') {
          completed = true;
          await loadStatsAndPatterns();
        }
        attempts++;
      }

      if (!completed) setError('Advanced analysis timed out');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const filteredPatterns = patterns
    .filter((p) => {
      if (filter.type !== 'all' && p.weakness_type !== filter.type) return false;
      if ((p.frequency || 0) < filter.minFrequency) return false;
      return true;
    })
    .sort((a, b) => {
      if (filter.sortBy === 'frequency')
        return (b.frequency || 0) - (a.frequency || 0);
      if (filter.sortBy === 'impact')
        return (b.average_eval_loss || 0) - (a.average_eval_loss || 0);
      return 0;
    });

  return (
    <div className="pattern-explorer-container">
      <h1>Chess Pattern Explorer</h1>
      <form onSubmit={handleLoadAnalysis} className="pattern-explorer-form">
        <div className="form-group">
          <input
            type="text"
            placeholder="Enter chess.com username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <button type="submit" disabled={loading || !username}>
            {loading ? 'Loading...' : 'Load Analysis'}
          </button>
          {showAdvanced && (
            <button
              type="button"
              onClick={handleRunAdvancedAnalysis}
              disabled={loading}
              className="btn-advanced"
            >
              {loading ? 'Analyzing...' : 'Run Advanced Analysis'}
            </button>
          )}
        </div>
      </form>

      {error && <div className="error-message">Error: {error}</div>}

      {stats && (
        <>
          <div className="stats-summary">
            <div className="stat-item">
              <span className="stat-label">Total Games</span>
              <span className="stat-value">{stats.total_games}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Overall Accuracy</span>
              <span className="stat-value">
                {stats.overall_accuracy ? formatPercentage(stats.overall_accuracy, 1) : 'N/A'}
              </span>
            </div>
            {showAdvanced && (
              <>
                <div className="stat-item">
                  <span className="stat-label">Unusual Moves</span>
                  <span className="stat-value">{stats.unusual_moves_total || 0}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Anomalies</span>
                  <span className="stat-value">{stats.anomalies_total || 0}</span>
                </div>
              </>
            )}
          </div>

          <div className="explorer-content">
            <div className="filter-panel">
              <PatternFilter filter={filter} onFilterChange={setFilter} />
            </div>
            <div className="pattern-panel">
              {selectedPattern ? (
                <PatternDetail
                  pattern={selectedPattern}
                  onBack={() => setSelectedPattern(null)}
                />
              ) : (
                <PatternList
                  patterns={filteredPatterns}
                  onSelectPattern={setSelectedPattern}
                  showAdvanced={showAdvanced}
                />
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
