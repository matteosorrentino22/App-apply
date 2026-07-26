import { apiFetch } from './client'

export function createSearch({ name, keywords, location }) {
  return apiFetch('/api/searches/', { method: 'POST', body: { name, keywords, location } })
}

export function activateSearch(id) {
  return apiFetch(`/api/searches/${id}/activate/`, { method: 'POST' })
}
