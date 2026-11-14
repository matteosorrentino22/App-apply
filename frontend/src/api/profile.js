import { apiFetch } from './client'

export function fetchProfile() {
  return apiFetch('/api/profiles/me/')
}

export function updateProfile(payload, { isMultipart = false } = {}) {
  return apiFetch('/api/profiles/me/', { method: 'PATCH', body: payload, isMultipart })
}

// Rimozione della foto (Sprint 70): il file viene cancellato dal server.
export function removeProfilePhoto() {
  return apiFetch('/api/profiles/me/photo/', { method: 'DELETE' })
}

export function importCv(file) {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch('/api/profile/import-cv/', { method: 'POST', body: formData, isMultipart: true })
}

const SECTION_ENDPOINTS = {
  experiences: '/api/experiences/',
  educations: '/api/educations/',
  skills: '/api/skills/',
  certifications: '/api/certifications/',
  languages: '/api/languages/',
}

export function createSectionItem(section, payload) {
  return apiFetch(SECTION_ENDPOINTS[section], { method: 'POST', body: payload })
}

export function updateSectionItem(section, id, payload) {
  return apiFetch(`${SECTION_ENDPOINTS[section]}${id}/`, { method: 'PATCH', body: payload })
}

export function deleteSectionItem(section, id) {
  return apiFetch(`${SECTION_ENDPOINTS[section]}${id}/`, { method: 'DELETE' })
}
