import { apiFetch } from './client'

// Contatori di oggi, massimali del piano e prezzi (Sprint 70).
export function fetchUsage() {
  return apiFetch('/api/accounts/usage/')
}
