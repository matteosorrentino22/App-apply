import { apiFetch, getToken } from './client'

export function fetchJobs({
  section = 'main',
  dateFrom,
  dateTo,
  scores,
  statuses,
  q,
  searchIds,
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
    if (searchIds && searchIds.length) params.set('search', searchIds.join(','))
    if (location) params.set('location', location)
    if (applicantsRanges && applicantsRanges.length) params.set('applicants', applicantsRanges.join(','))
    if (hasRecruiter) params.set('recruiter', hasRecruiter)
  }
  return apiFetch(`/api/jobs/?${params.toString()}`)
}

export function fetchJob(id) {
  return apiFetch(`/api/jobs/${id}/`)
}

export function fetchFilterPresets() {
  return apiFetch('/api/job-filter-presets/')
}

export function createFilterPreset(payload) {
  return apiFetch('/api/job-filter-presets/', { method: 'POST', body: payload })
}

export function deleteFilterPreset(id) {
  return apiFetch(`/api/job-filter-presets/${id}/`, { method: 'DELETE' })
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

export function openCvDraft(id) {
  return apiFetch(`/api/jobs/${id}/cv-draft/`, { method: 'POST', body: {} })
}

export function fetchCvDraft(id) {
  return apiFetch(`/api/jobs/${id}/cv-draft/`)
}

export function updateCvDraft(id, content) {
  return apiFetch(`/api/jobs/${id}/cv-draft/`, { method: 'PATCH', body: content })
}

export function finalizeCvDraft(id) {
  return apiFetch(`/api/jobs/${id}/cv-draft/finalize/`, { method: 'POST', body: {} })
}

export function fetchCvDraftChat(id) {
  return apiFetch(`/api/jobs/${id}/cv-draft/chat/`)
}

export function sendCvDraftChatMessage(id, message, focusedBullets = []) {
  return apiFetch(`/api/jobs/${id}/cv-draft/chat/`, {
    method: 'POST',
    body: {
      message,
      focus_bullets: focusedBullets.map(({ profileExperienceId, bulletIndex }) => ({
        profile_experience_id: profileExperienceId,
        bullet_index: bulletIndex,
      })),
    },
  })
}

export function recordCvDraftChatDecision(id, messageIndex, actionIndex, decision) {
  return apiFetch(`/api/jobs/${id}/cv-draft/chat/`, {
    method: 'PATCH',
    body: { message_index: messageIndex, action_index: actionIndex, decision },
  })
}

// Non passa da `apiFetch`: la risposta è un PDF binario, non JSON (serve
// leggerla come blob), e il conteggio pagine arriva in un header custom,
// non nel body — un fetch diretto resta più semplice che adattare il
// wrapper generico per questo unico caso.
export async function previewCvDraft(id, content) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Token ${token}`

  const response = await fetch(`/api/jobs/${id}/cv-draft/preview/`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify(content),
  })
  if (!response.ok) {
    throw new Error('Preview non disponibile')
  }
  const pageCount = Number(response.headers.get('X-Page-Count')) || 1
  const blob = await response.blob()
  return { blob, pageCount }
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

export function openCoverLetterDraft(id) {
  return apiFetch(`/api/jobs/${id}/cover-letter-draft/`, { method: 'POST', body: {} })
}

export function fetchCoverLetterDraft(id) {
  return apiFetch(`/api/jobs/${id}/cover-letter-draft/`)
}

export function updateCoverLetterDraft(id, content) {
  return apiFetch(`/api/jobs/${id}/cover-letter-draft/`, { method: 'PATCH', body: content })
}

export function finalizeCoverLetterDraft(id) {
  return apiFetch(`/api/jobs/${id}/cover-letter-draft/finalize/`, { method: 'POST', body: {} })
}

// Stesso motivo di `previewCvDraft`: risposta PDF binaria con il
// conteggio pagine in un header custom.
export async function previewCoverLetterDraft(id, content) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Token ${token}`

  const response = await fetch(`/api/jobs/${id}/cover-letter-draft/preview/`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify(content),
  })
  if (!response.ok) {
    throw new Error('Preview non disponibile')
  }
  const pageCount = Number(response.headers.get('X-Page-Count')) || 1
  const blob = await response.blob()
  return { blob, pageCount }
}

export function fetchCoverLetterDraftChat(id) {
  return apiFetch(`/api/jobs/${id}/cover-letter-draft/chat/`)
}

export function sendCoverLetterDraftChatMessage(id, message) {
  return apiFetch(`/api/jobs/${id}/cover-letter-draft/chat/`, { method: 'POST', body: { message } })
}

export function recordCoverLetterChatDecision(id, messageIndex, actionIndex, decision) {
  return apiFetch(`/api/jobs/${id}/cover-letter-draft/chat/`, {
    method: 'PATCH',
    body: { message_index: messageIndex, action_index: actionIndex, decision },
  })
}

export function generateReferralMessage(id, payload) {
  return apiFetch(`/api/jobs/${id}/generate-referral-message/`, {
    method: 'POST',
    body: payload,
  })
}

export function fetchReferralMessages(id) {
  return apiFetch(`/api/jobs/${id}/referral-messages/`)
}

export function fetchReferralMessageInstructions() {
  return apiFetch('/api/referral-message-instructions/')
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
