import { apiFetch } from './client'

export function fetchSearches() {
  return apiFetch('/api/searches/')
}

// Sprint 84 (A17, A18): paese + città (lista) e modalità di lavoro (Pro).
function searchBody({ search_type, keywords, country, cities, work_mode }) {
  return { search_type, keywords, country, cities, work_mode: work_mode || '' }
}

export function createSearch(search) {
  return apiFetch('/api/searches/', { method: 'POST', body: searchBody(search) })
}

export function updateSearch(id, search) {
  return apiFetch(`/api/searches/${id}/`, { method: 'PATCH', body: searchBody(search) })
}

export function deleteSearch(id) {
  return apiFetch(`/api/searches/${id}/`, { method: 'DELETE' })
}

// `countryCode` (ISO, facoltativo): solo città di quel paese (Sprint 84).
export function autocompleteCity(query, countryCode = '') {
  const params = new URLSearchParams({ q: query })
  if (countryCode) params.set('country_code', countryCode)
  return apiFetch(`/api/searches-city-autocomplete/?${params.toString()}`)
}

export function activateSearch(id) {
  return apiFetch(`/api/searches/${id}/activate/`, { method: 'POST' })
}

export function deactivateSearch(id) {
  return apiFetch(`/api/searches/${id}/deactivate/`, { method: 'POST' })
}

// Città attive e massimali (Sprint 84): "Città attive n di 50".
export function fetchSearchLimits() {
  return apiFetch('/api/search-limits/')
}

// Lavoro dei desideri (Sprint 84, A19): le keyword ricavate non arrivano mai.
export function fetchJobWish() {
  return apiFetch('/api/job-wish/')
}

export function saveJobWish({ description, country, cities, is_active }) {
  return apiFetch('/api/job-wish/', { method: 'PUT', body: { description, country, cities, is_active } })
}
