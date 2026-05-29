const BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';

function buildEndpoint(path, params = {}) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, value);
    }
  });

  const queryString = searchParams.toString();
  return queryString ? `${path}?${queryString}` : path;
}

export async function apiCall(endpoint, options = {}) {
  const { headers, ...fetchOptions } = options;
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...fetchOptions,
    headers: { 'Content-Type': 'application/json', ...headers },
  });

  if (!response.ok) {
    let message = `API error ${response.status}`;

    try {
      const errorBody = await response.json();
      if (errorBody.detail) {
        message = typeof errorBody.detail === 'string' ? errorBody.detail : JSON.stringify(errorBody.detail);
      }
    } catch {
      if (response.statusText) {
        message = response.statusText;
      }
    }

    throw new Error(message);
  }

  return response.json();
}

export const chessAPI = {
  analyzeGames: (username, limit = 100) =>
    apiCall('/analyze', {
      method: 'POST',
      body: JSON.stringify({ username, limit }),
    }),

  getAnalysisStatus: (taskId) =>
    apiCall(`/analysis/${taskId}`),

  listGames: (username, limit = 20, offset = 0) =>
    apiCall(buildEndpoint('/games', { username, limit, offset })),

  getStats: (username) =>
    apiCall(buildEndpoint('/stats', { username })),

  getPatterns: (username, weaknessType = null) =>
    apiCall(buildEndpoint('/patterns', { username, weakness_type: weaknessType })),

  getStudyPlan: (userId) =>
    apiCall(buildEndpoint('/study-plan', { user_id: userId })),

  // Phase 2 API methods
  startAdvancedAnalysis: (username, gameLimit = 100) =>
    apiCall('/advanced-analysis', {
      method: 'POST',
      body: JSON.stringify({ username, game_limit: gameLimit }),
    }),

  getAdvancedAnalysisStatus: (jobId) =>
    apiCall(`/advanced-analysis/${jobId}`),

  getMovePredictions: (username, minProbability = 0.0) =>
    apiCall(buildEndpoint('/move-predictions', { username, min_probability: minProbability })),

  getAnomalies: (username, minScore = 0.0) =>
    apiCall(buildEndpoint('/anomalies', { username, min_score: minScore })),

  getSimilarPositions: (positionFen, limit = 10) =>
    apiCall(buildEndpoint('/similar-positions', { position_fen: positionFen, limit })),

  getPatternDetails: (patternId) =>
    apiCall(`/pattern-details/${patternId}`),

  // Phase 3 Study Plan API methods
  startStudyPlanGeneration: (username, gameLimit = 100) =>
    apiCall('/study-plan/generate', {
      method: 'POST',
      body: JSON.stringify({ username, game_limit: gameLimit }),
    }),

  getStudyPlans: (userId, filters = {}) =>
    apiCall(buildEndpoint('/study-plan', {
      user_id: userId,
      status: filters.status !== 'all' ? filters.status : null,
      sort_by: filters.sort_by,
    })),

  markWeaknessStudied: (planId) =>
    apiCall(`/study-plan/${planId}/mark-studied`, {
      method: 'PATCH',
      body: JSON.stringify({}),
    }),

  getStudyProgress: (userId) =>
    apiCall(buildEndpoint('/study-plan/progress', { user_id: userId })),

  getStudyConcepts: (planId, search = null) =>
    apiCall(buildEndpoint(`/study-plan/${planId}/concepts`, { search })),

  getGamesForStudy: (planId, includeAnalysis = true) =>
    apiCall(buildEndpoint(`/study-plan/${planId}/games`, { include_analysis: includeAnalysis })),
};
