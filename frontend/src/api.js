// frontend/src/api.js
const BASE_URL = 'http://localhost:8000/api';

export async function apiCall(endpoint, options = {}) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
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
    apiCall(`/games?username=${username}&limit=${limit}&offset=${offset}`),

  getStats: (username) =>
    apiCall(`/stats?username=${username}`),

  getPatterns: (username, weaknessType = null) =>
    apiCall(`/patterns?username=${username}${weaknessType ? `&weakness_type=${weaknessType}` : ''}`),

  getStudyPlan: (userId) =>
    apiCall(`/study-plan?user_id=${userId}`),

  // Phase 2 API methods
  startAdvancedAnalysis: async (username, gameLimit = 100) => {
    const response = await fetch(`${BASE_URL}/advanced-analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, game_limit: gameLimit }),
    });
    if (!response.ok) throw new Error(`Failed to start analysis: ${response.statusText}`);
    return response.json();
  },

  getAdvancedAnalysisStatus: async (jobId) => {
    const response = await fetch(`${BASE_URL}/advanced-analysis/${jobId}`);
    if (!response.ok) throw new Error(`Failed to get status: ${response.statusText}`);
    return response.json();
  },

  getMovePredictions: async (username, minProbability = 0.0) => {
    const params = new URLSearchParams({ username, min_probability: minProbability });
    const response = await fetch(`${BASE_URL}/move-predictions?${params}`);
    if (!response.ok) throw new Error(`Failed to get predictions: ${response.statusText}`);
    return response.json();
  },

  getAnomalies: async (username, minScore = 0.0) => {
    const params = new URLSearchParams({ username, min_score: minScore });
    const response = await fetch(`${BASE_URL}/anomalies?${params}`);
    if (!response.ok) throw new Error(`Failed to get anomalies: ${response.statusText}`);
    return response.json();
  },

  getSimilarPositions: async (positionFen, limit = 10) => {
    const params = new URLSearchParams({ position_fen: positionFen, limit });
    const response = await fetch(`${BASE_URL}/similar-positions?${params}`);
    if (!response.ok) throw new Error(`Failed to get similar positions: ${response.statusText}`);
    return response.json();
  },

  getPatternDetails: async (patternId) => {
    const response = await fetch(`${BASE_URL}/pattern-details/${patternId}`);
    if (!response.ok) throw new Error(`Failed to get pattern details: ${response.statusText}`);
    return response.json();
  },

  // Phase 3 Study Plan API methods
  startStudyPlanGeneration: async (username, gameLimit = 100) => {
    const response = await fetch(`${BASE_URL}/study-plan/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, game_limit: gameLimit }),
    });
    if (!response.ok) throw new Error(`Failed to start study plan generation: ${response.statusText}`);
    return response.json();
  },

  getStudyPlans: async (userId, filters = {}) => {
    const params = new URLSearchParams({ user_id: userId });
    if (filters.status && filters.status !== 'all') params.append('status', filters.status);
    if (filters.sort_by) params.append('sort_by', filters.sort_by);

    const response = await fetch(`${BASE_URL}/study-plan?${params}`);
    if (!response.ok) throw new Error(`Failed to get study plans: ${response.statusText}`);
    return response.json();
  },

  markWeaknessStudied: async (planId) => {
    const response = await fetch(`${BASE_URL}/study-plan/${planId}/mark-studied`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!response.ok) throw new Error(`Failed to mark weakness as studied: ${response.statusText}`);
    return response.json();
  },

  getStudyProgress: async (userId) => {
    const params = new URLSearchParams({ user_id: userId });
    const response = await fetch(`${BASE_URL}/study-plan/progress?${params}`);
    if (!response.ok) throw new Error(`Failed to get study progress: ${response.statusText}`);
    return response.json();
  },

  getStudyConcepts: async (planId, search = null) => {
    const response = await fetch(`${BASE_URL}/study-plan/${planId}/concepts`);
    if (!response.ok) throw new Error(`Failed to get study concepts: ${response.statusText}`);
    return response.json();
  },

  getGamesForStudy: async (planId, includeAnalysis = true) => {
    const response = await fetch(`${BASE_URL}/study-plan/${planId}/games`);
    if (!response.ok) throw new Error(`Failed to get games for study: ${response.statusText}`);
    return response.json();
  },
};
