import { apiFetch } from './client'

export function fetchSearches() {
  return apiFetch('/api/searches/')
}

export function createSearch({ name, keywords, location }) {
  return apiFetch('/api/searches/', { method: 'POST', body: { name, keywords, location } })
}

export function updateSearch(id, { name, keywords, location }) {
  return apiFetch(`/api/searches/${id}/`, { method: 'PATCH', body: { name, keywords, location } })
}

export function deleteSearch(id) {
  return apiFetch(`/api/searches/${id}/`, { method: 'DELETE' })
}

export function activateSearch(id) {
  return apiFetch(`/api/searches/${id}/activate/`, { method: 'POST' })
}

export function deactivateSearch(id) {
  return apiFetch(`/api/searches/${id}/deactivate/`, { method: 'POST' })
}
