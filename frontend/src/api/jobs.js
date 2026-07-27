import { apiFetch } from './client'

export function fetchJobs({ section = 'main', period, scores, statuses, q }) {
  const params = new URLSearchParams({ section })
  if (q) {
    params.set('q', q)
  } else {
    if (period) params.set('period', period)
    if (scores && scores.length) params.set('score', scores.join(','))
    if (statuses && statuses.length) params.set('status', statuses.join(','))
  }
  return apiFetch(`/api/jobs/?${params.toString()}`)
}

export function fetchJob(id) {
  return apiFetch(`/api/jobs/${id}/`)
}

export function generateCv(id) {
  return apiFetch(`/api/jobs/${id}/generate-cv/`, { method: 'POST', body: {} })
}

export function enrichAndGenerateCv(id, detail) {
  return apiFetch(`/api/jobs/${id}/enrich-and-generate-cv/`, { method: 'POST', body: detail })
}

export function archiveJob(id) {
  return apiFetch(`/api/jobs/${id}/archive/`, { method: 'POST', body: {} })
}

export function unarchiveJob(id) {
  return apiFetch(`/api/jobs/${id}/unarchive/`, { method: 'POST', body: {} })
}

export function markApplicationDone(id) {
  return apiFetch(`/api/jobs/${id}/mark-application-done/`, { method: 'POST', body: {} })
}
