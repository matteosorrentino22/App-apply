import { apiFetch } from './client'

export function fetchSearches() {
  return apiFetch('/api/searches/')
}

export function createSearch({ search_type, keywords, city, country }) {
  return apiFetch('/api/searches/', { method: 'POST', body: { search_type, keywords, city, country } })
}

export function updateSearch(id, { search_type, keywords, city, country }) {
  return apiFetch(`/api/searches/${id}/`, {
    method: 'PATCH',
    body: { search_type, keywords, city, country },
  })
}

export function deleteSearch(id) {
  return apiFetch(`/api/searches/${id}/`, { method: 'DELETE' })
}

export function autocompleteCity(query) {
  return apiFetch(`/api/searches-city-autocomplete/?q=${encodeURIComponent(query)}`)
}

export function activateSearch(id) {
  return apiFetch(`/api/searches/${id}/activate/`, { method: 'POST' })
}

export function deactivateSearch(id) {
  return apiFetch(`/api/searches/${id}/deactivate/`, { method: 'POST' })
}
