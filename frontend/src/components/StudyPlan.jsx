import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { chessAPI } from '../api';
import StudyFilter from './StudyFilter';
import StudyCard from './StudyCard';
import StudyDetail from './StudyDetail';
import '../styles/StudyPlan.css';

export default function StudyPlan() {
  const [username, setUsername] = useState('');
  const [studyPlans, setStudyPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    status: 'active',
    concept_type: null,
    sort_by: 'created_at',
  });
  const [showDetails, setShowDetails] = useState(false);

  const loadStudyPlans = useCallback(async (user) => {
    setLoading(true);
    setError(null);

    try {
      const plansData = await chessAPI.getStudyPlans(user, filters);
      setStudyPlans(plansData || []);
    } catch (err) {
      setError(`Failed to load study plans: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const loadStudyProgress = useCallback(async (user) => {
    try {
      const progressData = await chessAPI.getStudyProgress(user);
      setProgress(progressData);
    } catch (err) {
      console.error('Failed to load progress:', err.message);
    }
  }, []);

  // Load study plans and progress when username changes
  useEffect(() => {
    if (username) {
      loadStudyPlans(username);
      loadStudyProgress(username);
    }
  }, [username, loadStudyPlans, loadStudyProgress]);

  // Reload study plans when filters change (progress doesn't change with filters)
  useEffect(() => {
    if (username) {
      loadStudyPlans(username);
    }
  }, [username, loadStudyPlans]);

  const handleGeneratePlan = async (e) => {
    e.preventDefault();
    if (!username) return;
    setGenerating(true);
    setError(null);

    try {
      await chessAPI.startStudyPlanGeneration(username, 100);
      // Reload plans after generation
      await loadStudyPlans(username);
      await loadStudyProgress(username);
    } catch (err) {
      setError(`Failed to generate study plan: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
  };

  const handleMarkStudied = async (planId) => {
    try {
      await chessAPI.markWeaknessStudied(planId, 0, 0);
      // Reload plans and progress after marking as studied
      await loadStudyPlans(username);
      await loadStudyProgress(username);
      setSelectedPlan(null);
      setShowDetails(false);
    } catch (err) {
      setError(`Failed to mark as studied: ${err.message}`);
    }
  };

  // Memoize filtered plans to avoid unnecessary recalculations
  const filteredPlans = useMemo(() => {
    // Server already handles status and sort_by filtering, only filter by concept_type
    if (!filters.concept_type || filters.concept_type === 'all') {
      return studyPlans;
    }
    return studyPlans.filter((plan) => plan.concept_type === filters.concept_type);
  }, [studyPlans, filters.concept_type]);

  return (
    <div className="study-plan-container">
      <h1>Study Plan Generator</h1>

      <form onSubmit={handleGeneratePlan} className="study-plan-form">
        <div className="form-group">
          <input
            type="text"
            placeholder="Enter chess.com username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <button type="submit" disabled={generating || !username}>
            {generating ? 'Generating...' : 'Generate Study Plan'}
          </button>
        </div>
      </form>

      {error && <div className="error-message">Error: {error}</div>}

      {progress && (
        <>
          <div className="progress-section">
            <h2>Study Progress</h2>
            <div className="progress-stats">
              <div className="progress-stat">
                <span className="stat-label">Total Plans</span>
                <span className="stat-value">{progress.total_plans}</span>
              </div>
              <div className="progress-stat">
                <span className="stat-label">Active</span>
                <span className="stat-value">{progress.active_plans}</span>
              </div>
              <div className="progress-stat">
                <span className="stat-label">Completed</span>
                <span className="stat-value">{progress.completed_plans}</span>
              </div>
              <div className="progress-stat">
                <span className="stat-label">Completion Rate</span>
                <span className="stat-value">{progress.completion_rate.toFixed(1)}%</span>
              </div>
            </div>

            <div className="progress-bar-container">
              <div className="progress-bar">
                <div
                  className="progress-bar-completed"
                  style={{
                    width: `${progress.completion_rate}%`,
                  }}
                />
              </div>
              <div className="progress-labels">
                <span>{progress.completed_plans} studied</span>
                <span>{progress.active_plans} in progress</span>
                <span>
                  {progress.total_plans - progress.active_plans - progress.completed_plans} remaining
                </span>
              </div>
            </div>
          </div>

          <div className="explorer-content">
            <div className="filter-panel">
              <StudyFilter
                plans={studyPlans}
                filters={filters}
                onFilterChange={handleFilterChange}
              />
            </div>

            <div className="plan-panel">
              {showDetails && selectedPlan ? (
                <StudyDetail
                  plan={selectedPlan}
                  username={username}
                  onBack={() => {
                    setSelectedPlan(null);
                    setShowDetails(false);
                  }}
                  onMarkStudied={handleMarkStudied}
                />
              ) : (
                <div className="study-cards-list">
                  {loading ? (
                    <div className="loading">Loading study plans...</div>
                  ) : filteredPlans.length > 0 ? (
                    filteredPlans.map((plan) => (
                      <StudyCard
                        key={plan.id}
                        plan={plan}
                        onExpand={() => {
                          setSelectedPlan(plan);
                          setShowDetails(true);
                        }}
                      />
                    ))
                  ) : (
                    <div className="empty-state">
                      No study plans found. Generate a new study plan to get started.
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
