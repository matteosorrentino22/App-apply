import { apiFetch } from './client'

export function fetchJobs({
  section = 'main',
  dateFrom,
  dateTo,
  scores,
  statuses,
  q,
  searchId,
  location,
  applicantsRanges,
  hasRecruiter,
}) {
  const params = new URLSearchParams({ section })
  if (q) {
    params.set('q', q)
  } else {
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    if (scores && scores.length) params.set('score', scores.join(','))
    if (statuses && statuses.length) params.set('status', statuses.join(','))
    if (searchId) params.set('search', searchId)
    if (location) params.set('location', location)
    if (applicantsRanges && applicantsRanges.length) params.set('applicants', applicantsRanges.join(','))
    if (hasRecruiter) params.set('recruiter', hasRecruiter)
  }
  return apiFetch(`/api/jobs/?${params.toString()}`)
}

export function fetchJob(id) {
  return apiFetch(`/api/jobs/${id}/`)
}

export function collectJobs() {
  return apiFetch('/api/jobs/collect/', { method: 'POST', body: {} })
}

export function fetchHomeStats() {
  return apiFetch('/api/jobs/stats/')
}

export function generateCv(id, gaps = [], gapInstructions = '') {
  return apiFetch(`/api/jobs/${id}/generate-cv/`, {
    method: 'POST',
    body: { gaps, gap_instructions: gapInstructions },
  })
}

export function generateCoverLetter(id, instructions) {
  return apiFetch(`/api/jobs/${id}/generate-cover-letter/`, {
    method: 'POST',
    body: { instructions },
  })
}

export function fetchCoverLetterInstructions() {
  return apiFetch('/api/cover-letter-instructions/')
}

export function archiveJob(id) {
  return apiFetch(`/api/jobs/${id}/archive/`, { method: 'POST', body: {} })
}

export function unarchiveJob(id) {
  return apiFetch(`/api/jobs/${id}/unarchive/`, { method: 'POST', body: {} })
}

export function favoriteJob(id) {
  return apiFetch(`/api/jobs/${id}/favorite/`, { method: 'POST', body: {} })
}

export function unfavoriteJob(id) {
  return apiFetch(`/api/jobs/${id}/unfavorite/`, { method: 'POST', body: {} })
}

export function markApplicationDone(id) {
  return apiFetch(`/api/jobs/${id}/mark-application-done/`, { method: 'POST', body: {} })
}

export function importJob(url) {
  return apiFetch('/api/jobs/import/', { method: 'POST', body: { url } })
}

export function createManualJob(payload) {
  return apiFetch('/api/jobs/manual/', { method: 'POST', body: payload })
}
