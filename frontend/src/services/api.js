const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export const api = {
  health: () => request('/health'),
  dashboardSummary: () => request('/api/dashboard/summary'),
  listTransactions: () => request('/api/transactions'),
  getTransaction: (id) => request(`/api/transactions/${id}`),
  listAlerts: () => request('/api/alerts'),
  getAlert: (id) => request(`/api/alerts/${id}`),
  startInvestigation: (alertId) =>
    request('/api/investigations', { method: 'POST', body: JSON.stringify({ alert_id: alertId }) }),
  getInvestigation: (id) => request(`/api/investigations/${id}`),
  reviewInvestigation: (id, reviewer_decision, notes) =>
    request(`/api/investigations/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({ reviewer_decision, notes }),
    }),
  submitFeedback: (id, was_correct, comment) =>
    request(`/api/investigations/${id}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ was_correct, comment }),
    }),
  getAudit: (id) => request(`/api/investigations/${id}/audit`),
  getEvaluation: () => request('/api/evaluation'),
  demoReset: () => request('/api/demo/reset', { method: 'POST' }),
}
