// frontend/src/api.js
const API_BASE = 'http://localhost:8000/api';

export async function apiCall(endpoint, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
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

  getStudyPlan: (username) =>
    apiCall(`/study-plan?username=${username}`),
};
